import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy import ndimage as ndi
from rasterio.transform import from_origin
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe41.structural import (  # noqa: E402
    StructuralConfig,
    TerrainField,
    _family_masks,
    _local_strike_and_coherence,
    build_structural_fields,
    distance_weighted_tversky,
    emit_probabilities,
    make_terrain_field,
    spatial_quadrant_masks,
    write_submission,
)


def test_local_strike_convention_for_cardinal_lines():
    vertical = np.zeros((81, 81), dtype=bool)
    vertical[:, 40] = True
    strike_v, coherence_v = _local_strike_and_coherence(vertical, 1.0, 2.5)
    assert abs(float(strike_v[40, 40]) - 0.0) < 3.0
    assert float(coherence_v[40, 40]) > 0.8

    horizontal = np.zeros((81, 81), dtype=bool)
    horizontal[40, :] = True
    strike_h, coherence_h = _local_strike_and_coherence(horizontal, 1.0, 2.5)
    assert abs(float(strike_h[40, 40]) - 90.0) < 3.0
    assert float(coherence_h[40, 40]) > 0.8


def test_family_strike_bins_are_disjoint_and_leave_other_strikes_unclassified():
    skeleton = np.ones((1, 4), dtype=bool)
    strikes = np.array([[135.0, 20.0, 80.0, 160.0]], dtype=np.float32)
    coherence = np.ones_like(strikes)
    nw, normal, other = _family_masks(skeleton, strikes, coherence, StructuralConfig())
    assert nw.tolist() == [[True, False, False, False]]
    assert normal.tolist() == [[False, True, False, False]]
    assert other.tolist() == [[False, False, True, True]]
    assert not np.any(nw & normal)


def test_terrain_gradient_reference_uses_exact_registered_quantile():
    rows, cols = np.mgrid[:17, :19]
    elevation = (0.03 * rows**2 + np.sin(cols / 2.3) + 0.02 * rows * cols).astype(np.float32)
    valid = np.ones(elevation.shape, dtype=bool)
    config = StructuralConfig()
    field = make_terrain_field(elevation, valid, None, config)
    smoothed = ndi.gaussian_filter(elevation, config.terrain_smoothing_sigma_px)
    grad_row, grad_col = np.gradient(smoothed)
    gradient = np.hypot(grad_col, grad_row)
    expected = float(np.quantile(gradient[valid], config.terrain_gradient_quantile))
    assert abs(field.gradient_reference - expected) < 1.0e-7


def test_terrain_baseline_remains_available_when_a_fold_has_no_fault_families():
    shape = (30, 30)
    known_faults = np.zeros(shape, dtype=bool)
    footprint = np.ones(shape, dtype=bool)
    terrain = TerrainField(
        strike_deg=np.zeros(shape, dtype=np.float32),
        coherence=np.full(shape, 0.7, dtype=np.float32),
        gradient_strength=np.full(shape, 0.8, dtype=np.float32),
        valid=footprint.copy(),
        gradient_reference=1.0,
    )
    fields = build_structural_fields(known_faults, terrain, footprint)
    assert np.count_nonzero(fields.score) == 0
    assert np.count_nonzero(fields.corridor_only) == 0
    assert np.count_nonzero(fields.terrain_only) > 0
    assert float(fields.terrain_only.max()) == 1.0


def test_probability_emitter_is_range_safe_and_matches_expected_mass():
    score = np.linspace(0.01, 1.0, 1000, dtype=np.float32).reshape(20, 50)
    allowed = np.ones(score.shape, dtype=bool)
    prediction, receipt = emit_probabilities(score, allowed, expected_mass=100.0, support_factor=3)
    assert np.isfinite(prediction).all()
    assert float(prediction.min()) >= 0.0
    assert float(prediction.max()) <= 1.0
    assert abs(float(prediction.sum(dtype=np.float64)) - 100.0) < 1.0e-3
    assert receipt["nonzero_pixels"] == 300
    assert receipt["support_pixels"] == 300


def test_probability_emitter_resolves_tied_scores_by_flat_index():
    score = np.ones((1, 10), dtype=np.float32)
    allowed = np.ones(score.shape, dtype=bool)
    prediction, receipt = emit_probabilities(score, allowed, expected_mass=1.0, support_factor=3)
    assert np.flatnonzero(prediction).tolist() == [0, 1, 2]
    assert receipt["support_factor_met"] is True
    assert abs(float(prediction.sum()) - 1.0) < 1.0e-6


def test_distance_weighted_tversky_basics_and_range_check():
    truth = np.zeros((15, 15), dtype=bool)
    truth[7, 7] = True
    perfect = np.zeros(truth.shape, dtype=np.float32)
    perfect[7, 7] = 1.0
    score = distance_weighted_tversky(perfect, truth)
    assert score["tp"] == 1.0
    assert score["fp"] == 0.0
    assert score["fn"] == 0.0
    assert score["dti"] > 0.999999

    distant = np.zeros(truth.shape, dtype=np.float32)
    distant[7, 11] = 1.0  # exactly 400 m away: outside the 300 m kernel
    miss = distance_weighted_tversky(distant, truth)
    assert miss["tp"] == 0.0
    assert miss["fn"] == 1.0
    assert miss["fp"] == 1.0
    assert miss["dti"] == 0.0

    invalid = perfect.copy()
    invalid[0, 0] = np.nan
    try:
        distance_weighted_tversky(invalid, truth)
    except ValueError as exc:
        assert "finite" in str(exc)
    else:
        raise AssertionError("non-finite predictions must be rejected")


def test_four_spatial_masks_are_disjoint_and_collar_is_applied():
    masks = spatial_quadrant_masks((40, 50), collar_px=3)
    stacked = np.stack(list(masks.values()))
    assert np.all(stacked.sum(axis=0) <= 1)
    assert masks["NW"][0, 0]
    assert not masks["NW"][19, 19]
    assert masks["SE"][39, 49]


def test_writer_reopens_exact_grid_and_all_finite_values(tmp_path):
    template_path = tmp_path / "template.tif"
    output_path = tmp_path / "candidate.tif"
    transform = from_origin(243350, 4508550, 100, 100)
    template = np.zeros((12, 10), dtype=np.float32)
    template[:2, :] = np.nan
    with rasterio.open(
        template_path,
        "w",
        driver="GTiff",
        height=template.shape[0],
        width=template.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(template, 1)
    probabilities = np.zeros(template.shape, dtype=np.float32)
    probabilities[3, 4] = 0.6
    receipt = write_submission(output_path, template_path, probabilities)
    assert receipt["crs"] == "EPSG:32611"
    assert receipt["shape"] == [12, 10]
    assert receipt["dtype"] == "float32"
    assert receipt["count"] == 1
    assert receipt["nodata"] == "NaN"
    assert receipt["all_finite"] is False
    assert receipt["inside_footprint_finite"] is True
    assert receipt["outside_footprint_all_nan"] is True
    assert receipt["min"] == 0.0
    assert abs(receipt["max"] - 0.6) < 1.0e-6
    with rasterio.open(output_path) as ds:
        data = ds.read(1)
        assert ds.transform == transform
        assert ds.crs.to_epsg() == 32611
        assert np.isnan(ds.nodata)
        assert np.isnan(data[:2, :]).all()
        assert np.isfinite(data[2:, :]).all()
        assert np.all((data[2:, :] >= 0) & (data[2:, :] <= 1))
