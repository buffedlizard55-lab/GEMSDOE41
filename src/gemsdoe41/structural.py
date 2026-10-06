"""H41-A-R: raster-derived transfer corridors with terrain orientation support.

The model is intentionally geometric. It derives local strike from the supplied binary
fault raster, pairs NW-family terminal pixels with a nearby N-to-NNE-family trace, and
scores only narrow corridor neighborhoods where a terrain-gradient orientation agrees
with the nearer population. Slip sense is not observed in the raster; the family names
are regional structural interpretations, not per-feature kinematic measurements.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import rasterio
from scipy import ndimage as ndi
from skimage.draw import line as raster_line
from skimage.morphology import skeletonize


@dataclass(frozen=True)
class StructuralConfig:
    """H41-A-PRE-1 thresholds (all distances use the 100 m grid)."""

    fault_smooth_sigma_px: float = 1.0
    fault_tensor_sigma_px: float = 2.5
    min_fault_coherence: float = 0.25
    nw_strike_min_deg: float = 120.0  # axial 0..180; equivalent bearings 300..330
    nw_strike_max_deg: float = 150.0
    normal_strike_min_deg: float = 0.0
    normal_strike_max_deg: float = 30.0  # N through NNE; ambiguous strikes are not forced
    endpoint_to_nw_max_px: float = 4.0
    max_tip_to_normal_px: float = 30.0  # 3 km pairing search radius
    corridor_sigma_px: float = 3.0
    corridor_support_max_px: float = 5.0
    family_max_distance_px: float = 20.0  # both families must be within 2 km
    family_distance_balance_px: float = 12.0  # within 1.2 km of the medial region
    known_fault_exclusion_px: float = 3.0  # no output within 300 m of any known line
    terrain_smoothing_sigma_px: float = 1.2
    terrain_tensor_sigma_px: float = 2.0
    orientation_tolerance_deg: float = 20.0
    terrain_gradient_quantile: float = 0.70


@dataclass
class TerrainField:
    strike_deg: np.ndarray
    coherence: np.ndarray
    gradient_strength: np.ndarray
    valid: np.ndarray
    gradient_reference: float


@dataclass
class StructuralFields:
    score: np.ndarray
    corridor_only: np.ndarray
    terrain_only: np.ndarray
    corridor_distance_px: np.ndarray
    distance_nw_px: np.ndarray
    distance_normal_px: np.ndarray
    distance_catalogue_px: np.ndarray
    nw_trace: np.ndarray
    normal_trace: np.ndarray
    pair_seeds: np.ndarray
    lineament_support: np.ndarray
    stats: dict[str, Any]


def _local_strike_and_coherence(
    binary_line: np.ndarray,
    smooth_sigma_px: float,
    tensor_sigma_px: float,
) -> tuple[np.ndarray, np.ndarray]:
    """Return axial strike (0..180 degrees from north) and structure-tensor coherence.

    In array coordinates, rows increase southward and columns increase eastward. The
    major structure-tensor eigenvector is normal to a narrow line; rotating it by 90°
    gives the line tangent. The formula below converts that tangent to an axial strike.
    """
    image = ndi.gaussian_filter(binary_line.astype(np.float32), smooth_sigma_px)
    grad_row, grad_col = np.gradient(image)
    j_xx = ndi.gaussian_filter(grad_col * grad_col, tensor_sigma_px)
    j_yy = ndi.gaussian_filter(grad_row * grad_row, tensor_sigma_px)
    j_xy = ndi.gaussian_filter(grad_col * grad_row, tensor_sigma_px)
    trace = j_xx + j_yy
    discriminant = np.sqrt(np.maximum((j_xx - j_yy) ** 2 + 4.0 * j_xy**2, 0.0))
    coherence = discriminant / (trace + 1.0e-12)
    normal_angle_from_east = 0.5 * np.arctan2(2.0 * j_xy, j_xx - j_yy)
    strike_deg = np.mod(-np.rad2deg(normal_angle_from_east), 180.0)
    return strike_deg.astype(np.float32), coherence.astype(np.float32)


def _family_masks(
    skeleton: np.ndarray,
    strike_deg: np.ndarray,
    coherence: np.ndarray,
    config: StructuralConfig,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Classify oriented skeleton cells into two non-overlapping strike families.

    The binary labels do not contain per-trace slip sense. The word ``dextral`` for the
    NW family and ``normal`` for the N/NNE family therefore comes from the cited regional
    framework, not from a direct measurement on this raster. Other strikes remain
    unclassified rather than being forced into one of the two populations.
    """
    confident = skeleton & (coherence >= config.min_fault_coherence)
    nw = confident & (strike_deg >= config.nw_strike_min_deg) & (
        strike_deg <= config.nw_strike_max_deg
    )
    normal = confident & (strike_deg >= config.normal_strike_min_deg) & (
        strike_deg <= config.normal_strike_max_deg
    )
    other = skeleton & ~(nw | normal)
    return nw, normal, other


def build_fault_families(
    known_faults: np.ndarray,
    config: StructuralConfig = StructuralConfig(),
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Skeletonize a raster catalogue and infer local strike-family masks."""
    if known_faults.ndim != 2:
        raise ValueError("known_faults must be a two-dimensional raster")
    skeleton = skeletonize(np.asarray(known_faults, dtype=bool))
    strike, coherence = _local_strike_and_coherence(
        skeleton, config.fault_smooth_sigma_px, config.fault_tensor_sigma_px
    )
    nw, normal, other = _family_masks(skeleton, strike, coherence, config)
    counts = {
        "catalogue_positive_pixels": int(np.count_nonzero(known_faults)),
        "skeleton_pixels": int(np.count_nonzero(skeleton)),
        "nw_family_skeleton_pixels": int(np.count_nonzero(nw)),
        "normal_family_skeleton_pixels": int(np.count_nonzero(normal)),
        "other_or_low_coherence_skeleton_pixels": int(np.count_nonzero(other)),
    }
    return skeleton, strike, coherence, nw, normal, counts


def make_terrain_field(
    elevation: np.ndarray,
    valid_footprint: np.ndarray,
    nodata: float | int | None,
    config: StructuralConfig = StructuralConfig(),
) -> TerrainField:
    """Estimate a terrain-gradient lineament-orientation proxy from ``det_elev`` only.

    This is an unsupervised, local orientation/coherence transform of the competition's
    detrended elevation band. It is not a geophysical transform and is not a validated
    geological lineament inventory.
    """
    if elevation.shape != valid_footprint.shape:
        raise ValueError("elevation and valid_footprint shapes differ")
    valid = np.asarray(valid_footprint, dtype=bool) & np.isfinite(elevation)
    if nodata is not None and np.isfinite(nodata):
        # GeoDAWN's float32 nodata is the minimum finite value, not NaN.
        valid &= ~np.isclose(elevation, nodata, rtol=0.0, atol=0.0)
    if not np.any(valid):
        raise ValueError("no valid detrended-elevation pixels within the template footprint")

    weights = ndi.gaussian_filter(
        valid.astype(np.float32), config.terrain_smoothing_sigma_px
    )
    numerator = ndi.gaussian_filter(
        np.where(valid, elevation, 0.0).astype(np.float32),
        config.terrain_smoothing_sigma_px,
    )
    surface = numerator / np.maximum(weights, 1.0e-6)
    grad_row, grad_col = np.gradient(surface)
    j_xx = ndi.gaussian_filter(
        grad_col * grad_col, config.terrain_tensor_sigma_px
    )
    j_yy = ndi.gaussian_filter(
        grad_row * grad_row, config.terrain_tensor_sigma_px
    )
    j_xy = ndi.gaussian_filter(
        grad_col * grad_row, config.terrain_tensor_sigma_px
    )
    trace = j_xx + j_yy
    discriminant = np.sqrt(np.maximum((j_xx - j_yy) ** 2 + 4.0 * j_xy**2, 0.0))
    coherence = discriminant / (trace + 1.0e-12)
    normal_angle_from_east = 0.5 * np.arctan2(2.0 * j_xy, j_xx - j_yy)
    strike_deg = np.mod(-np.rad2deg(normal_angle_from_east), 180.0)

    gradient = np.hypot(grad_col, grad_row)
    # Use the exact registered quantile over all valid cells; a former every-50th
    # systematic subsample was removed in review because it could alias spatial patterns.
    reference = float(
        np.quantile(gradient[valid], config.terrain_gradient_quantile)
    )
    strength = np.clip(gradient / max(reference, 1.0e-9), 0.0, 1.0)
    # Require the smoothed window to be well-supported by valid source values.
    valid &= weights >= 0.90
    return TerrainField(
        strike_deg=strike_deg.astype(np.float32),
        coherence=coherence.astype(np.float32),
        gradient_strength=strength.astype(np.float32),
        valid=valid,
        gradient_reference=reference,
    )


def _corridor_seeds(
    skeleton: np.ndarray,
    nw: np.ndarray,
    normal: np.ndarray,
    distance_nw: np.ndarray,
    distance_normal: np.ndarray,
    nearest_normal: np.ndarray,
    config: StructuralConfig,
) -> tuple[np.ndarray, dict[str, int]]:
    """Connect eligible NW trace tips to their nearest N/NNE trace pixels."""
    empty = np.zeros(skeleton.shape, dtype=bool)
    empty_stats = {
        "nw_tip_candidates": 0,
        "paired_tips": 0,
        "corridor_centerline_pixels": 0,
    }
    if not np.any(nw) or not np.any(normal):
        return empty, empty_stats

    neighbors = ndi.convolve(
        skeleton.astype(np.uint8), np.ones((3, 3), dtype=np.uint8), mode="constant"
    ) - skeleton.astype(np.uint8)
    endpoints = skeleton & (neighbors == 1)
    endpoint_rows, endpoint_cols = np.nonzero(endpoints)
    if endpoint_rows.size == 0:
        return empty, empty_stats

    near_nw = distance_nw[endpoint_rows, endpoint_cols] <= config.endpoint_to_nw_max_px
    endpoint_rows = endpoint_rows[near_nw]
    endpoint_cols = endpoint_cols[near_nw]
    tip_count = int(endpoint_rows.size)
    nearest_rows = nearest_normal[0, endpoint_rows, endpoint_cols]
    nearest_cols = nearest_normal[1, endpoint_rows, endpoint_cols]
    separation = distance_normal[endpoint_rows, endpoint_cols]
    pair_mask = separation <= config.max_tip_to_normal_px
    endpoint_rows = endpoint_rows[pair_mask]
    endpoint_cols = endpoint_cols[pair_mask]
    nearest_rows = nearest_rows[pair_mask]
    nearest_cols = nearest_cols[pair_mask]

    seeds = np.zeros(skeleton.shape, dtype=bool)
    for r0, c0, r1, c1 in zip(
        endpoint_rows, endpoint_cols, nearest_rows, nearest_cols
    ):
        rr, cc = raster_line(int(r0), int(c0), int(r1), int(c1))
        seeds[rr, cc] = True
    return seeds, {
        "nw_tip_candidates": tip_count,
        "paired_tips": int(endpoint_rows.size),
        "corridor_centerline_pixels": int(np.count_nonzero(seeds)),
    }


def build_structural_fields(
    known_faults: np.ndarray,
    terrain: TerrainField,
    valid_footprint: np.ndarray,
    config: StructuralConfig = StructuralConfig(),
) -> StructuralFields:
    """Build H41-A and its two registered, ablatable comparison fields."""
    if known_faults.shape != valid_footprint.shape:
        raise ValueError("known_faults and valid_footprint shapes differ")
    if terrain.valid.shape != valid_footprint.shape:
        raise ValueError("terrain and valid_footprint shapes differ")
    known_faults = np.asarray(known_faults, dtype=bool) & np.asarray(
        valid_footprint, dtype=bool
    )
    skeleton, strike, coherence, nw, normal, family_counts = build_fault_families(
        known_faults, config
    )

    if not np.any(nw) or not np.any(normal):
        zeros = np.zeros(known_faults.shape, dtype=np.float32)
        inf = np.full(known_faults.shape, np.inf, dtype=np.float32)
        distance_catalogue = ndi.distance_transform_edt(~known_faults).astype(np.float32)
        terrain_only = (terrain.coherence * terrain.gradient_strength).astype(np.float32)
        terrain_domain = (
            np.asarray(valid_footprint, dtype=bool)
            & terrain.valid
            & (distance_catalogue > config.known_fault_exclusion_px)
        )
        terrain_only[~terrain_domain] = 0.0
        terrain_max = float(terrain_only.max(initial=0.0))
        if terrain_max > 0:
            terrain_only /= terrain_max
        return StructuralFields(
            score=zeros.copy(),
            corridor_only=zeros.copy(),
            terrain_only=terrain_only,
            corridor_distance_px=inf,
            distance_nw_px=inf.copy(),
            distance_normal_px=inf.copy(),
            distance_catalogue_px=distance_catalogue,
            nw_trace=nw,
            normal_trace=normal,
            pair_seeds=np.zeros_like(known_faults),
            lineament_support=zeros.copy(),
            stats={
                **family_counts,
                "nw_tip_candidates": 0,
                "paired_tips": 0,
                "candidate_domain_pixels": 0,
                "emission_pixels_within_300m_of_catalogue": 0,
                "candidate_pixels_closer_to_nw_family": 0,
                "candidate_pixels_closer_to_normal_family": 0,
                "terrain_gradient_reference": terrain.gradient_reference,
                "max_normalized_score": 0.0,
            },
        )

    distance_nw, indices_nw = ndi.distance_transform_edt(~nw, return_indices=True)
    distance_normal, indices_normal = ndi.distance_transform_edt(
        ~normal, return_indices=True
    )
    distance_catalogue = ndi.distance_transform_edt(~known_faults)
    seeds, pair_stats = _corridor_seeds(
        skeleton,
        nw,
        normal,
        distance_nw,
        distance_normal,
        indices_normal,
        config,
    )
    if np.any(seeds):
        corridor_distance = ndi.distance_transform_edt(~seeds).astype(np.float32)
        corridor_proximity = np.exp(
            -0.5 * (corridor_distance / config.corridor_sigma_px) ** 2
        ).astype(np.float32)
    else:
        corridor_distance = np.full(known_faults.shape, np.inf, dtype=np.float32)
        corridor_proximity = np.zeros(known_faults.shape, dtype=np.float32)

    # In each cell, use the orientation of the nearer of the two mapped populations.
    nearer_nw = distance_nw <= distance_normal
    nw_strike = strike[indices_nw[0], indices_nw[1]]
    normal_strike = strike[indices_normal[0], indices_normal[1]]
    expected_strike = np.where(nearer_nw, nw_strike, normal_strike)
    axial_difference = np.abs(
        (terrain.strike_deg - expected_strike + 90.0) % 180.0 - 90.0
    )
    lineament_support = (
        terrain.coherence
        * terrain.gradient_strength
        * np.exp(-0.5 * (axial_difference / config.orientation_tolerance_deg) ** 2)
    ).astype(np.float32)
    lineament_support = np.clip(lineament_support, 0.0, 1.0)

    farther_family_distance = np.maximum(distance_nw, distance_normal)
    family_imbalance = np.abs(distance_nw - distance_normal)
    junction_proximity = (
        np.exp(-0.5 * (farther_family_distance / (0.75 * config.family_max_distance_px)) ** 2)
        * np.exp(-0.5 * (family_imbalance / config.family_distance_balance_px) ** 2)
    ).astype(np.float32)
    valid_domain = (
        np.asarray(valid_footprint, dtype=bool)
        & terrain.valid
        & (distance_catalogue > config.known_fault_exclusion_px)
        & (corridor_distance <= config.corridor_support_max_px)
        & (farther_family_distance <= config.family_max_distance_px)
        & (family_imbalance <= config.family_distance_balance_px)
    )
    corridor_only = corridor_proximity * junction_proximity
    score = corridor_only * lineament_support
    # The ablation is genuinely terrain-only: do not leak fault-family orientation into
    # this baseline. The same 300 m exclusion is retained so all arms target off-catalogue
    # cells under the same novelty policy.
    terrain_only = (terrain.coherence * terrain.gradient_strength).astype(np.float32)
    terrain_domain = (
        np.asarray(valid_footprint, dtype=bool)
        & terrain.valid
        & (distance_catalogue > config.known_fault_exclusion_px)
    )
    terrain_only[~terrain_domain] = 0.0
    corridor_only[~valid_domain] = 0.0
    score[~valid_domain] = 0.0

    max_score = float(score.max(initial=0.0))
    max_corridor = float(corridor_only.max(initial=0.0))
    max_terrain = float(terrain_only.max(initial=0.0))
    if max_score > 0:
        score /= max_score
    if max_corridor > 0:
        corridor_only /= max_corridor
    if max_terrain > 0:
        terrain_only /= max_terrain

    stats = {
        **family_counts,
        **pair_stats,
        "candidate_domain_pixels": int(np.count_nonzero(valid_domain)),
        "emission_pixels_within_300m_of_catalogue": int(
            np.count_nonzero((distance_catalogue <= 3.0) & (score > 0))
        ),
        "candidate_pixels_closer_to_nw_family": int(
            np.count_nonzero((score > 0) & nearer_nw)
        ),
        "candidate_pixels_closer_to_normal_family": int(
            np.count_nonzero((score > 0) & ~nearer_nw)
        ),
        "terrain_gradient_reference": terrain.gradient_reference,
        "max_normalized_score": float(score.max(initial=0.0)),
    }
    return StructuralFields(
        score=score,
        corridor_only=corridor_only,
        terrain_only=terrain_only,
        corridor_distance_px=corridor_distance,
        distance_nw_px=distance_nw.astype(np.float32),
        distance_normal_px=distance_normal.astype(np.float32),
        distance_catalogue_px=distance_catalogue.astype(np.float32),
        nw_trace=nw,
        normal_trace=normal,
        pair_seeds=seeds,
        lineament_support=lineament_support,
        stats=stats,
    )


def emit_probabilities(
    score: np.ndarray,
    allowed: np.ndarray,
    expected_mass: float,
    support_factor: int = 3,
) -> tuple[np.ndarray, dict[str, float | int]]:
    """Select the highest scores and scale soft predictions to a fixed expected mass.

    The support contains ``support_factor * expected_mass`` cells when possible. A
    deterministic water-filling scale is applied so the sum of output probabilities
    equals ``expected_mass`` (unless the eligible support is too small). This makes
    spatial-fold comparisons matched in probability mass rather than positive-pixel
    count. Returned probabilities are finite and clipped to [0, 1].
    """
    if score.shape != allowed.shape:
        raise ValueError("score and allowed shapes differ")
    if expected_mass < 0:
        raise ValueError("expected_mass must be nonnegative")
    if support_factor < 1:
        raise ValueError("support_factor must be at least 1")
    output = np.zeros(score.shape, dtype=np.float32)
    candidate = np.asarray(allowed, dtype=bool) & np.isfinite(score) & (score > 0)
    flat_ids = np.flatnonzero(candidate)
    requested_support = max(
        int(np.ceil(expected_mass * support_factor)), int(np.ceil(expected_mass))
    )
    if expected_mass == 0 or flat_ids.size == 0:
        return output, {
            "probability_mass": 0.0,
            "nonzero_pixels": 0,
            "eligible_pixels": int(flat_ids.size),
            "requested_mass": float(expected_mass),
            "requested_support_pixels": requested_support,
            "support_pixels": 0,
            "support_factor_met": flat_ids.size >= requested_support,
            "support_shortfall_pixels": max(0, requested_support - int(flat_ids.size)),
        }
    target_support = min(flat_ids.size, requested_support)
    if expected_mass >= target_support:
        # Too few cells for a soft support: use a hard 0/1 map at the available mass.
        target_support = min(flat_ids.size, int(np.ceil(expected_mass)))
    flat_score = score.ravel()
    candidate_scores = flat_score[flat_ids]
    # Select above a partition threshold, then resolve cutoff ties by ascending flat
    # index so the exact support is deterministic across runs and array layouts.
    partition_index = candidate_scores.size - target_support
    cutoff = np.partition(candidate_scores, partition_index)[partition_index]
    above_cutoff = flat_ids[candidate_scores > cutoff]
    tied_at_cutoff = flat_ids[candidate_scores == cutoff]
    remaining = target_support - above_cutoff.size
    selected = np.concatenate((above_cutoff, tied_at_cutoff[:remaining]))
    selected = selected[np.lexsort((selected, -flat_score[selected]))]
    weights = np.maximum(flat_score[selected].astype(np.float64), 1.0e-12)
    target_mass = min(float(expected_mass), float(target_support))
    low, high = 0.0, max(1.0 / float(np.min(weights)), 1.0)
    for _ in range(64):
        mid = 0.5 * (low + high)
        mass = float(np.minimum(1.0, mid * weights).sum())
        if mass < target_mass:
            low = mid
        else:
            high = mid
    probabilities = np.minimum(1.0, high * weights).astype(np.float32)
    # Correct sub-ulp scaling drift on one unsaturated pixel, without breaking [0, 1].
    residual = target_mass - float(probabilities.sum(dtype=np.float64))
    if abs(residual) > 1.0e-5:
        free = np.flatnonzero((probabilities > 0) & (probabilities < 1))
        if free.size:
            j = int(free[-1])
            probabilities[j] = np.float32(np.clip(float(probabilities[j]) + residual, 0.0, 1.0))
    output.ravel()[selected] = probabilities
    return output, {
        "probability_mass": float(output.sum(dtype=np.float64)),
        "nonzero_pixels": int(np.count_nonzero(output)),
        "eligible_pixels": int(flat_ids.size),
        "requested_mass": float(expected_mass),
        "requested_support_pixels": requested_support,
        "support_pixels": int(target_support),
        "support_factor_met": bool(target_support >= requested_support),
        "support_shortfall_pixels": max(0, requested_support - int(target_support)),
        "min_nonzero_probability": float(output[output > 0].min()),
        "max_probability": float(output.max(initial=0.0)),
    }


def distance_weighted_tversky(
    prediction: np.ndarray,
    truth: np.ndarray,
    pixel_size_m: float = 100.0,
    radius_m: float = 300.0,
    alpha: float = 0.2,
    beta: float = 0.8,
    epsilon: float = 1.0e-8,
) -> dict[str, float]:
    """Compute the competition's distance-weighted Tversky index on a 2-D window."""
    if prediction.shape != truth.shape or prediction.ndim != 2:
        raise ValueError("prediction and truth must be matching 2-D arrays")
    p = np.asarray(prediction, dtype=np.float64)
    g = np.asarray(truth, dtype=bool)
    if not np.isfinite(p).all() or np.any((p < 0) | (p > 1)):
        raise ValueError("prediction values must be finite and in [0, 1]")
    truth_count = int(np.count_nonzero(g))
    if truth_count == 0:
        return {"tp": 0.0, "fp": float(p.sum()), "fn": 0.0, "truth_pixels": 0, "dti": 0.0}

    radius_px = radius_m / pixel_size_m
    max_offset = int(np.floor(radius_px))
    best_credit = np.zeros(g.shape, dtype=np.float64)
    height, width = g.shape
    for dr in range(-max_offset, max_offset + 1):
        for dc in range(-max_offset, max_offset + 1):
            distance_px = float(np.hypot(dr, dc))
            if distance_px > radius_px:
                continue
            kernel = max(1.0 - distance_px / radius_px, 0.0)
            # At each ground-truth coordinate, examine prediction at (g_row+dr,g_col+dc).
            gr0, gr1 = max(0, -dr), min(height, height - dr)
            gc0, gc1 = max(0, -dc), min(width, width - dc)
            if gr0 >= gr1 or gc0 >= gc1:
                continue
            pred_window = p[gr0 + dr : gr1 + dr, gc0 + dc : gc1 + dc]
            truth_window = best_credit[gr0:gr1, gc0:gc1]
            np.maximum(truth_window, pred_window * kernel, out=truth_window)

    tp = float(best_credit[g].sum())
    fn = float((1.0 - best_credit[g]).sum())
    distance_to_truth_px = ndi.distance_transform_edt(~g)
    nearest_truth_kernel = np.maximum(
        1.0 - (distance_to_truth_px * pixel_size_m) / radius_m, 0.0
    )
    fp = float((p * (1.0 - nearest_truth_kernel)).sum())
    dti = tp / (tp + alpha * fp + beta * fn + epsilon)
    return {"tp": tp, "fp": fp, "fn": fn, "truth_pixels": truth_count, "dti": float(dti)}


def write_submission(
    output_path: str | Path,
    template_path: str | Path,
    probabilities: np.ndarray,
    tags: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Write a single-band float32 GeoTIFF on the exact template grid.

    Predictions must be finite and in [0, 1] within the template footprint. Cells outside
    that footprint are NaN and the output nodata tag is NaN, matching the competition's
    published format guidance and the local example raster.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with rasterio.open(template_path) as template:
        profile = template.profile.copy()
        expected_shape = (template.height, template.width)
        expected_transform = template.transform
        expected_crs = template.crs
        template_values = template.read(1)
        footprint = np.isfinite(template_values)
        if template.nodata is not None and np.isfinite(template.nodata):
            footprint &= ~np.isclose(
                template_values, template.nodata, rtol=0.0, atol=0.0
            )
    if probabilities.shape != expected_shape:
        raise ValueError(f"output shape {probabilities.shape} != template {expected_shape}")
    probabilities = np.asarray(probabilities, dtype=np.float32)
    if not np.isfinite(probabilities[footprint]).all():
        raise ValueError("predictions contain NaN or infinity within the template footprint")
    if np.any((probabilities[footprint] < 0.0) | (probabilities[footprint] > 1.0)):
        raise ValueError("predictions within the template footprint are outside [0, 1]")
    array = np.full(expected_shape, np.nan, dtype=np.float32)
    array[footprint] = probabilities[footprint]
    profile.update(
        driver="GTiff",
        count=1,
        dtype="float32",
        crs=expected_crs,
        transform=expected_transform,
        height=expected_shape[0],
        width=expected_shape[1],
        nodata=np.nan,
        compress="deflate",
        predictor=3,
        tiled=True,
        blockxsize=256,
        blockysize=256,
    )
    with rasterio.open(output_path, "w", **profile) as dst:
        dst.write(array, 1)
        if tags:
            dst.update_tags(**tags)
    # Reopen the bytes from disk; do not rely on the in-memory profile alone.
    with rasterio.open(output_path) as written:
        if written.count != 1 or written.dtypes != ("float32",):
            raise RuntimeError("written raster is not single-band float32")
        if (
            written.crs != expected_crs
            or written.transform != expected_transform
            or written.shape != expected_shape
        ):
            raise RuntimeError("written raster grid does not match the template")
        if written.nodata is None or not np.isnan(written.nodata):
            raise RuntimeError("written raster lost the template's NaN nodata convention")
        data = written.read(1)
        inside = data[footprint]
        outside = data[~footprint]
        if not np.isfinite(inside).all():
            raise RuntimeError("written raster contains NaN or infinity in its valid footprint")
        if outside.size and not np.isnan(outside).all():
            raise RuntimeError("written raster does not preserve NaN outside the template footprint")
        minimum = float(inside.min())
        maximum = float(inside.max())
        if minimum < 0.0 or maximum > 1.0:
            raise RuntimeError("written in-footprint values are outside [0, 1]")
        receipt = {
            "path": str(output_path),
            "crs": written.crs.to_string() if written.crs else None,
            "shape": [written.height, written.width],
            "dtype": written.dtypes[0],
            "count": written.count,
            "transform": list(written.transform)[:6],
            "bounds": [written.bounds.left, written.bounds.bottom, written.bounds.right, written.bounds.top],
            "nodata": "NaN",
            "all_finite": bool(np.isfinite(data).all()),
            "inside_footprint_finite": True,
            "outside_footprint_all_nan": bool(outside.size == 0 or np.isnan(outside).all()),
            "valid_footprint_pixels": int(footprint.sum()),
            "outside_footprint_pixels": int((~footprint).sum()),
            "min": minimum,
            "max": maximum,
            "positive_pixels": int(np.count_nonzero(inside > 0)),
            "probability_mass": float(inside.sum(dtype=np.float64)),
            "outside_footprint_encoding": "NaN_with_NaN_nodata_tag",
        }
    return receipt


def load_competition_inputs(
    template_path: str | Path,
    fault_path: str | Path,
    feature_path: str | Path,
    config: StructuralConfig = StructuralConfig(),
) -> tuple[np.ndarray, np.ndarray, TerrainField, dict[str, Any]]:
    """Cross-check the example template, labels, and named `det_elev` band."""
    with rasterio.open(template_path) as template:
        template_values = template.read(1)
        footprint = np.isfinite(template_values)
        template_meta = {
            "crs": template.crs.to_string() if template.crs else None,
            "shape": [template.height, template.width],
            "transform": list(template.transform)[:6],
            "footprint_pixels": int(footprint.sum()),
            "template_nodata": (
                "NaN"
                if template.nodata is not None and np.isnan(template.nodata)
                else template.nodata
            ),
        }
        grid_crs = template.crs
        grid_transform = template.transform
        grid_shape = template.shape
    with rasterio.open(fault_path) as faults_ds:
        if faults_ds.crs != grid_crs or faults_ds.transform != grid_transform or faults_ds.shape != grid_shape:
            raise ValueError("fault raster grid does not match the submission template")
        fault_values = faults_ds.read(1)
        known_faults = (fault_values > 0) & footprint
        template_meta["known_fault_positive_pixels"] = int(known_faults.sum())
        template_meta["fault_raster_nodata"] = faults_ds.nodata
    with rasterio.open(feature_path) as features_ds:
        if features_ds.crs != grid_crs or features_ds.transform != grid_transform or features_ds.shape != grid_shape:
            raise ValueError("feature raster grid does not match the submission template")
        band_index = None
        for i, description in enumerate(features_ds.descriptions, start=1):
            if description and description.split(" - ")[0].strip() == "det_elev":
                band_index = i
                break
            tag_name = features_ds.tags(i).get("band_name")
            if tag_name == "det_elev":
                band_index = i
                break
        if band_index is None:
            raise ValueError("no named det_elev band in training_features.tif")
        elevation = features_ds.read(band_index)
        band_nodata = features_ds.nodatavals[band_index - 1]
        terrain = make_terrain_field(elevation, footprint, band_nodata, config)
        template_meta.update(
            {
                "feature_band_count": features_ds.count,
                "det_elev_band_index": band_index,
                "det_elev_description": features_ds.descriptions[band_index - 1],
                "det_elev_nodata": band_nodata,
                "valid_det_elev_pixels": int(terrain.valid.sum()),
                "terrain_gradient_reference": terrain.gradient_reference,
            }
        )
    return footprint, known_faults, terrain, template_meta


def spatial_quadrant_masks(shape: tuple[int, int], collar_px: int) -> dict[str, np.ndarray]:
    """Return four disjoint interior quadrant masks after an inward spatial collar."""
    height, width = shape
    mid_r, mid_c = height // 2, width // 2
    masks: dict[str, np.ndarray] = {}
    bounds = {
        "NW": (0, mid_r, 0, mid_c),
        "NE": (0, mid_r, mid_c, width),
        "SW": (mid_r, height, 0, mid_c),
        "SE": (mid_r, height, mid_c, width),
    }
    for name, (r0, r1, c0, c1) in bounds.items():
        # Only internal fold boundaries need a collar; the outer raster edge is not a
        # boundary between training and test labels.
        rr0 = r0 + (collar_px if r0 > 0 else 0)
        rr1 = r1 - (collar_px if r1 < height else 0)
        cc0 = c0 + (collar_px if c0 > 0 else 0)
        cc1 = c1 - (collar_px if c1 < width else 0)
        m = np.zeros(shape, dtype=bool)
        if rr0 < rr1 and cc0 < cc1:
            m[rr0:rr1, cc0:cc1] = True
        masks[name] = m
    return masks


def buffered_holdout_training_faults(
    all_faults: np.ndarray,
    fold_name: str,
    collar_px: int,
) -> np.ndarray:
    """Hide the held-out quadrant and its collar before constructing predictors."""
    h, w = all_faults.shape
    mr, mc = h // 2, w // 2
    bounds = {
        "NW": (0, mr, 0, mc),
        "NE": (0, mr, mc, w),
        "SW": (mr, h, 0, mc),
        "SE": (mr, h, mc, w),
    }
    if fold_name not in bounds:
        raise ValueError(f"unknown fold {fold_name}")
    r0, r1, c0, c1 = bounds[fold_name]
    r0 = max(0, r0 - collar_px)
    r1 = min(h, r1 + collar_px)
    c0 = max(0, c0 - collar_px)
    c1 = min(w, c1 + collar_px)
    training = np.asarray(all_faults, dtype=bool).copy()
    training[r0:r1, c0:c1] = False
    return training


def sha256_file(path: str | Path, chunk_size: int = 1 << 20) -> str:
    import hashlib

    digest = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def jsonable_config(config: StructuralConfig) -> dict[str, Any]:
    return asdict(config)
