#!/usr/bin/env python3
"""Validate H41-A on spatial blocks, then build an auditable candidate GeoTIFF.

Example:
  python scripts/build_submission.py --data-dir data/raw
  python scripts/build_submission.py --data-dir data --output docs/downloads/candidate.tif

A local holdout is only a proxy against known catalogued faults. The script never uploads
anything to DrivenData and always labels its output as unscored unless an organizer score
is independently observed.
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gemsdoe41.structural import (  # noqa: E402
    StructuralConfig,
    buffered_holdout_training_faults,
    build_structural_fields,
    distance_weighted_tversky,
    emit_probabilities,
    jsonable_config,
    load_competition_inputs,
    sha256_file,
    spatial_quadrant_masks,
    write_submission,
)


FOLDS = ("NW", "NE", "SW", "SE")
ARMS = ("h41a_full", "corridor_only", "terrain_only")


def _display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def _fold_window(name: str, shape: tuple[int, int], collar_px: int) -> tuple[slice, slice]:
    height, width = shape
    mid_r, mid_c = height // 2, width // 2
    bounds = {
        "NW": (0, mid_r, 0, mid_c),
        "NE": (0, mid_r, mid_c, width),
        "SW": (mid_r, height, 0, mid_c),
        "SE": (mid_r, height, mid_c, width),
    }
    if name not in bounds:
        raise ValueError(f"unknown fold: {name}")
    r0, r1, c0, c1 = bounds[name]
    r0 += collar_px if r0 > 0 else 0
    r1 -= collar_px if r1 < height else 0
    c0 += collar_px if c0 > 0 else 0
    c1 -= collar_px if c1 < width else 0
    if r0 >= r1 or c0 >= c1:
        raise ValueError(f"collar removes the {name} fold")
    return slice(r0, r1), slice(c0, c1)


def _sha_or_none(path: Path) -> str | None:
    return sha256_file(path) if path.exists() else None


def run_spatial_holdout(
    known_faults: np.ndarray,
    footprint: np.ndarray,
    terrain: Any,
    config: StructuralConfig,
    total_expected_mass: float,
    collar_px: int,
    support_factor: int,
) -> dict[str, Any]:
    """Run a four-quadrant, equal-probability-mass proxy holdout."""
    eval_masks = spatial_quadrant_masks(known_faults.shape, collar_px)
    fold_results: list[dict[str, Any]] = []
    pooled: dict[str, dict[str, float]] = {
        arm: {"tp": 0.0, "fp": 0.0, "fn": 0.0, "truth_pixels": 0.0}
        for arm in ARMS
    }
    fold_expected_mass = total_expected_mass / len(FOLDS)

    for fold in FOLDS:
        train_faults = buffered_holdout_training_faults(
            known_faults, fold, collar_px=collar_px
        )
        fields = build_structural_fields(train_faults, terrain, footprint, config)
        eval_domain = eval_masks[fold] & footprint & terrain.valid
        window_rows, window_cols = _fold_window(fold, known_faults.shape, collar_px)
        truth = known_faults[window_rows, window_cols] & eval_domain[window_rows, window_cols]
        truth_count = int(np.count_nonzero(truth))
        if truth_count == 0:
            fold_results.append(
                {
                    "fold": fold,
                    "status": "no_truth_after_collar",
                    "truth_pixels": 0,
                    "candidate_stats": fields.stats,
                }
            )
            del fields
            continue

        fold_record: dict[str, Any] = {
            "fold": fold,
            "truth_pixels": truth_count,
            "training_catalogue_pixels": int(train_faults.sum()),
            "evaluation_cells": int(eval_domain.sum()),
            "per_arm": {},
            "candidate_stats": fields.stats,
        }
        arm_scores = {
            "h41a_full": fields.score,
            "corridor_only": fields.corridor_only,
            "terrain_only": fields.terrain_only,
        }
        insufficient: list[str] = []
        for arm, arm_score in arm_scores.items():
            available = int(np.count_nonzero((arm_score > 0) & eval_domain))
            arm_record: dict[str, Any] = {"eligible_pixels": available}
            if available < fold_expected_mass:
                arm_record.update(
                    {
                        "status": "insufficient_support_for_matched_mass",
                        "dti": None,
                    }
                )
                insufficient.append(arm)
                fold_record["per_arm"][arm] = arm_record
                continue
            prediction, emission = emit_probabilities(
                arm_score,
                eval_domain,
                expected_mass=fold_expected_mass,
                support_factor=support_factor,
            )
            if emission["probability_mass"] + 1.0e-3 < fold_expected_mass:
                arm_record.update(
                    {
                        "status": "insufficient_probability_mass",
                        "dti": None,
                        "emission": emission,
                    }
                )
                insufficient.append(arm)
                fold_record["per_arm"][arm] = arm_record
                del prediction
                continue
            metric = distance_weighted_tversky(
                prediction[window_rows, window_cols],
                truth,
            )
            arm_record.update({"status": "scored", **metric, "emission": emission})
            fold_record["per_arm"][arm] = arm_record
            for key in ("tp", "fp", "fn", "truth_pixels"):
                pooled[arm][key] += float(metric[key])
            del prediction
        fold_record["status"] = (
            "matched_candidate_unavailable" if "h41a_full" in insufficient else "scored"
        )
        fold_record["unmatched_arms"] = insufficient
        fold_results.append(fold_record)
        del fields

    pooled_dti: dict[str, float | None] = {}
    for arm in ARMS:
        counts = pooled[arm]
        if counts["truth_pixels"] == 0:
            pooled_dti[arm] = None
            continue
        denom = counts["tp"] + 0.2 * counts["fp"] + 0.8 * counts["fn"] + 1.0e-8
        pooled_dti[arm] = counts["tp"] / denom if denom > 0 else 0.0

    scored_folds = [
        f for f in fold_results
        if f.get("status") == "scored"
        and all(f["per_arm"][arm].get("status") == "scored" for arm in ARMS)
    ]
    wins = 0
    paired: list[dict[str, Any]] = []
    for fold in scored_folds:
        scores = fold["per_arm"]
        best_control = max(
            scores["corridor_only"]["dti"], scores["terrain_only"]["dti"]
        )
        won = scores["h41a_full"]["dti"] > best_control
        wins += int(won)
        paired.append(
            {
                "fold": fold["fold"],
                "candidate": scores["h41a_full"]["dti"],
                "best_control": best_control,
                "candidate_wins": won,
            }
        )
    controls = [pooled_dti["corridor_only"], pooled_dti["terrain_only"]]
    finite_controls = [value for value in controls if value is not None]
    pooled_best_control = max(finite_controls) if finite_controls else None
    primary_passed = (
        len(scored_folds) == 4
        and wins >= 3
        and pooled_dti["h41a_full"] is not None
        and pooled_best_control is not None
        and pooled_dti["h41a_full"] > pooled_best_control
    )
    sensitivity_gate = {
        "required": "gain survives collar and orientation-window sensitivity checks",
        "performed": False,
        "passed": False,
        "status": "not_run_primary_candidate_unavailable" if not primary_passed else "not_implemented_in_H41A_PRE_1",
        "note": "No sensitivity result is inferred. Freeze numeric sensitivity variants in a new dated preregistration before any future scoring.",
    }
    passed = primary_passed and sensitivity_gate["passed"]
    failure_reason = None
    if not primary_passed:
        unavailable = [
            f["fold"] for f in fold_results
            if f.get("per_arm", {}).get("h41a_full", {}).get("status")
            != "scored"
        ]
        if unavailable:
            failure_reason = (
                "H41-A had insufficient/nonexistent support in leak-resistant spatial fold(s): "
                + ", ".join(unavailable)
                + ". No registered H41-A pair-corridor cells reached the 3.3 km-collared test interiors; the registered local corridor method therefore could not provide a matched-mass prediction there."
            )
        else:
            failure_reason = "H41-A did not beat the best matched control on the registered >=3/4-fold rule."
    elif not sensitivity_gate["passed"]:
        failure_reason = "The primary matched-holdout gate passed, but the required collar/orientation sensitivity gate was not performed; no slot may be recommended."
    return {
        "protocol": "H41-A-PRE-1",
        "proxy_only": True,
        "proxy_truth": "known public catalogue faults hidden in four spatial quadrants",
        "fold_order": list(FOLDS),
        "collar_px": collar_px,
        "collar_m": collar_px * 100,
        "total_expected_probability_mass": total_expected_mass,
        "per_fold_expected_probability_mass": fold_expected_mass,
        "support_factor": support_factor,
        "alpha": 0.2,
        "beta": 0.8,
        "radius_m": 300,
        "fold_results": fold_results,
        "pooled_counts": pooled,
        "pooled_dti": pooled_dti,
        "pooled_best_control": pooled_best_control,
        "paired_fold_comparisons": paired,
        "candidate_wins": wins,
        "primary_promotion_gate_passed": primary_passed,
        "sensitivity_gate": sensitivity_gate,
        "promotion_gate_passed": passed,
        "failure_reason": failure_reason,
        "promotion_gate": "primary: full candidate beats both matched controls on >=3/4 folds and pooled DTI; slot eligibility additionally requires the preregistered collar/orientation sensitivity gate",
        "limitations": [
            "The hidden competition labels are not available; this proxy rewards recovery of withheld known faults, not discovery of genuinely new faults.",
            "A missing candidate field in a block is an inability to generalize, not a DTI of zero; that fold is marked unevaluable rather than assigned a fabricated score.",
            "The 33 px collar exceeds the 30 px pairing radius but is 2 px smaller than the maximum 35 px centerline-plus-support reach; no H41-A support entered any scored quadrant, but this geometric margin is a protocol limitation for any future nonzero fold.",
            "The exact hidden evaluation may include corrections within 300 m of known faults; H41-A deliberately excludes that zone and may miss such corrections.",
            "The supplied raster is not the original vector catalogue, so strike estimates are 100 m raster approximations and slip sense is not observed.",
        ],
    }


def compare_prior_rasters(
    candidate: np.ndarray,
    footprint: np.ndarray,
    prior_paths: list[Path],
    template_path: Path,
) -> list[dict[str, Any]]:
    """Report support overlap only when each prior matches the actual template grid."""
    candidate_support = (candidate > 0) & footprint
    with rasterio.open(template_path) as template_ds:
        expected_shape = template_ds.shape
        expected_crs = template_ds.crs
        expected_transform = template_ds.transform
    results: list[dict[str, Any]] = []
    for path in prior_paths:
        with rasterio.open(path) as prior_ds:
            if prior_ds.shape != expected_shape or prior_ds.shape != candidate.shape:
                results.append({"path": str(path), "comparable": False, "reason": "shape mismatch"})
                continue
            if prior_ds.crs != expected_crs or prior_ds.crs is None:
                results.append({"path": str(path), "comparable": False, "reason": "CRS mismatch"})
                continue
            if prior_ds.transform != expected_transform:
                results.append({"path": str(path), "comparable": False, "reason": "transform mismatch to template"})
                continue
            prior = prior_ds.read(1)
        prior_support = (np.isfinite(prior) & (prior > 0)) & footprint
        intersection = int(np.count_nonzero(candidate_support & prior_support))
        union = int(np.count_nonzero(candidate_support | prior_support))
        candidate_count = int(candidate_support.sum())
        prior_count = int(prior_support.sum())
        results.append(
            {
                "path": str(path),
                "sha256": sha256_file(path),
                "comparable": True,
                "candidate_nonzero": candidate_count,
                "prior_nonzero": prior_count,
                "intersection": intersection,
                "jaccard": intersection / union if union else 1.0,
                "candidate_contained_in_prior": intersection / candidate_count if candidate_count else 0.0,
            }
        )
    return results


def _candidate_record(
    fields: Any,
    output: np.ndarray,
    emission: dict[str, Any],
    footprint: np.ndarray,
    known_faults: np.ndarray,
    train_faults: np.ndarray,
) -> dict[str, Any]:
    support = output > 0
    dcat = fields.distance_catalogue_px
    dn = fields.distance_nw_px
    dnormal = fields.distance_normal_px

    def distance_summary(distance_px: np.ndarray) -> dict[str, float | None]:
        values = distance_px[support]
        if values.size == 0:
            return {"min_m": None, "median_m": None, "p90_m": None}
        return {
            "min_m": float(np.min(values) * 100.0),
            "median_m": float(np.median(values) * 100.0),
            "p90_m": float(np.quantile(values, 0.90) * 100.0),
        }

    def probability_weighted_mean(distance_px: np.ndarray) -> float | None:
        values = distance_px[support]
        weights = output[support].astype(np.float64)
        if values.size == 0 or float(weights.sum()) == 0:
            return None
        return float(np.average(values * 100.0, weights=weights))

    closer_nw = support & (dn <= dnormal)
    closer_normal = support & (dnormal < dn)
    family_distance_counts = {
        f"within_{radius_m}m_{family_name}_family": int(
            np.count_nonzero(support & (distance <= radius_m / 100.0))
        )
        for family_name, distance in (("NW", dn), ("normal", dnormal))
        for radius_m in (100, 200, 300)
    }
    return {
        **family_distance_counts,
        "probability_mass": float(output.sum(dtype=np.float64)),
        "nonzero_pixels": int(support.sum()),
        "emission": emission,
        "within_100m_known_fault": int(np.count_nonzero(support & (dcat <= 1.0))),
        "within_200m_known_fault": int(np.count_nonzero(support & (dcat <= 2.0))),
        "within_300m_known_fault": int(np.count_nonzero(support & (dcat <= 3.0))),
        "within_300m_NW_family": int(np.count_nonzero(support & (dn <= 3.0))),
        "within_300m_normal_family": int(np.count_nonzero(support & (dnormal <= 3.0))),
        "outside_300m_all_known_traces": int(np.count_nonzero(support & (dcat > 3.0))),
        "within_500m_of_pair_centerline": int(
            np.count_nonzero(support & (fields.corridor_distance_px <= 5.0))
        ),
        "both_families_within_2km": int(
            np.count_nonzero(support & (np.maximum(dn, dnormal) <= 20.0))
        ),
        "closer_to_NW_family_pixels": int(np.count_nonzero(closer_nw)),
        "closer_to_normal_family_pixels": int(np.count_nonzero(closer_normal)),
        "nearest_catalogue_distance": distance_summary(dcat),
        "nearest_NW_family_distance": distance_summary(dn),
        "nearest_normal_family_distance": distance_summary(dnormal),
        "probability_weighted_mean_catalogue_distance_m": probability_weighted_mean(dcat),
        "probability_weighted_mean_NW_distance_m": probability_weighted_mean(dn),
        "probability_weighted_mean_normal_distance_m": probability_weighted_mean(dnormal),
        "catalogue_train_pixels": int(train_faults.sum()),
        "known_catalogue_pixels": int(known_faults.sum()),
        "valid_footprint_pixels": int(footprint.sum()),
        "maximum_probability": float(output.max(initial=0.0)),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/raw", help="directory containing example_submission.tif, existing_faults.tif, and training_features.tif")
    parser.add_argument("--template", type=Path, help="override example_submission.tif template path")
    parser.add_argument("--faults", type=Path, help="override existing_faults.tif path")
    parser.add_argument("--features", type=Path, help="override training_features.tif path")
    parser.add_argument("--output", type=Path, default=ROOT / "docs/downloads/gemsdoe41-h41a-bimodal-transfer-20261005.tif")
    parser.add_argument("--receipt", type=Path, default=ROOT / "docs/evidence/h41a_build_receipt.json")
    parser.add_argument("--total-mass", type=float, default=30000.0, help="total expected probability mass for the final full-region raster")
    parser.add_argument("--holdout-mass", type=float, default=30000.0, help="total expected probability mass across four holdout folds")
    parser.add_argument("--support-factor", type=int, default=3, help="nonzero support cells per unit expected mass")
    parser.add_argument("--collar-px", type=int, default=33, help="inward spatial collar; exceeds the 30 px pairing radius")
    parser.add_argument("--compare-raster", type=Path, action="append", default=[], help="same-grid prior raster to use only for uniqueness diagnostics; repeatable")
    parser.add_argument("--skip-holdout", action="store_true", help="not recommended; only use for format-development fixtures")
    args = parser.parse_args()

    template = args.template or args.data_dir / "example_submission.tif"
    faults = args.faults or args.data_dir / "existing_faults.tif"
    features = args.features or args.data_dir / "training_features.tif"
    for path in (template, faults, features):
        if not path.exists():
            raise FileNotFoundError(f"required input is absent: {path}")

    config = StructuralConfig()
    footprint, known_faults, terrain, grid = load_competition_inputs(
        template, faults, features, config
    )
    holdout = None
    if not args.skip_holdout:
        holdout = run_spatial_holdout(
            known_faults,
            footprint,
            terrain,
            config,
            total_expected_mass=args.holdout_mass,
            collar_px=args.collar_px,
            support_factor=args.support_factor,
        )
        evidence_path = ROOT / "docs/evidence/h41a_holdout_20261005.json"
        evidence_path.parent.mkdir(parents=True, exist_ok=True)
        evidence_path.write_text(json.dumps(holdout, indent=2) + "\n", encoding="utf-8")
        print(f"Holdout evidence: {evidence_path}")
        print("Pooled DTI:", json.dumps(holdout["pooled_dti"], sort_keys=True))
        print(
            "Fold wins:", holdout["candidate_wins"], "/", len(holdout["paired_fold_comparisons"]),
            "gate=", holdout["promotion_gate_passed"],
        )

    # Build final candidate from the complete visible catalogue.
    fields = build_structural_fields(known_faults, terrain, footprint, config)
    output_allowed = footprint & terrain.valid & (fields.score > 0)
    probability, emission = emit_probabilities(
        fields.score,
        output_allowed,
        expected_mass=args.total_mass,
        support_factor=args.support_factor,
    )
    output_tags = {
        "candidate_id": "H41-A",
        "method": "NW tip to nearest N-NNE trace corridor plus det_elev orientation concordance",
        "score_status": "unscored research candidate; no organizer score observed",
        "catalogue_exclusion_m": str(int(config.known_fault_exclusion_px * 100)),
        "expected_probability_mass": str(args.total_mass),
        "source_note": "public owner data bridge; hashes recorded in receipt; not organizer-authenticated",
    }
    file_receipt = write_submission(args.output, template, probability, output_tags)
    file_receipt["path"] = _display_path(args.output)
    candidate_stats = _candidate_record(
        fields, probability, emission, footprint, known_faults, known_faults
    )
    uniqueness = compare_prior_rasters(
        probability, footprint, args.compare_raster, template
    )
    receipt: dict[str, Any] = {
        "schema_version": 1,
        "candidate_id": "H41-A",
        "run_utc": datetime.now(timezone.utc).isoformat(),
        "submission_name": "GEMSDOE41-H41A-BIMODAL-TRANSFER",
        "submission_note": "NW fault-tip to N/NNE normal-family corridors; det_elev orientation concordance; 300 m mapped-trace exclusion; 30k expected probability mass; local proxy only, unscored",
        "score_status": "UNSCORED_RESEARCH_CANDIDATE",
        "slot_eligible": bool(holdout and holdout["promotion_gate_passed"]),
        "holdout": holdout,
        "config": jsonable_config(config),
        "grid": grid,
        "input_sha256": {
            "template": _sha_or_none(template),
            "known_faults": _sha_or_none(faults),
            "training_features": _sha_or_none(features),
        },
        "output": {**file_receipt, "sha256": sha256_file(args.output)},
        "candidate_distribution": candidate_stats,
        "uniqueness_checks": uniqueness,
        "limitations": [
            "No organizer score or hidden test labels are available to this build.",
            "Spatial holdout scores known-catalogue line recovery and is not a valid estimate of performance on unseen expert labels.",
            "The NW dextral and N/NNE normal interpretations are regional priors; the input raster does not carry trace-level slip-sense attributes.",
            "Raster skeleton strike is estimated at 100 m resolution, not from original fault-vector geometry.",
            "Terrain orientation is a detrended-elevation gradient-coherence proxy, not an independently field-mapped fault lineament.",
            "A 300 m exclusion intentionally avoids catalogue-density echoes but may miss valid new-fault corrections within that distance, which competition staff say can exist.",
            "NaN is preserved outside the local template footprint, following the competition page and sample nodata convention; the organizer's exact validator behavior cannot be tested without an authenticated submission account.",
            "Hashes authenticate the local files against the public owner-maintained bridge manifest, not against DrivenData's login-gated source files.",
        ],
    }
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(f"GeoTIFF: {args.output}")
    print(f"SHA-256: {receipt['output']['sha256']}")
    print(f"Build receipt: {args.receipt}")
    print(f"Nonzero cells: {file_receipt['positive_pixels']}; probability mass: {file_receipt['probability_mass']:.3f}")
    print(f"Unique comparisons run: {len(uniqueness)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
