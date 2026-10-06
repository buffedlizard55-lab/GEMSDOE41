"""One preregistered H41-E test: exact kinematic filtering of H41-A anchors.

This script does not modify the published H41-A TIFF or consume a competition
submission slot. It uses the same four fixed whole-source spatial folds, held-out
truth, DTI, geometry, and topographic tangent field as the existing audit.
"""
from collections import Counter
import gc
import json
from pathlib import Path

import numpy as np
from scipy.ndimage import distance_transform_edt, gaussian_filter
from rasterio.features import shapes
from shapely import union_all
from shapely.geometry import shape

from metric import dti
from model import Config, geometry_field, predict, topo_orientation
from run_pipeline import ROOT, drop_heldout_traces, load_inputs, load_vectors

OUT = ROOT / "research/experiments/h41e-kinematic-holdout.json"


def apply_kinematic_screen(records):
    """Copy records and gate corridor eligibility on exact documented values.

    NW family 0 requires source ``SLIPSENSE=RL`` (right-lateral); N/NNE family
    1 requires ``SLIPSENSE=N`` (normal). All ambiguous, missing, or conflicting
    values remain in mapped geometry but cannot be corridor anchors/receivers.
    No values are inferred from strike, normalized from ``SS``, or imputed.
    """
    screened = []
    counts = Counter()
    for record in records:
        if record.get("family") not in (0, 1):
            raise ValueError(f"unrecognized geometric family: {record.get('family')!r}")
        item = dict(record)
        raw = record.get("source_properties", {}).get("SLIPSENSE")
        slip = "" if raw is None else str(raw).strip().upper()
        expected = "RL" if record["family"] == 0 else "N"
        keep = bool(record["eligible"] and slip == expected)
        item["eligible"] = keep
        counts[f"family_{record['family']}_slipsense_{slip or 'MISSING'}"] += 1
        if record["eligible"]:
            counts[f"eligible_before_family_{record['family']}"] += 1
        if keep:
            counts[f"eligible_after_family_{record['family']}"] += 1
        screened.append(item)
    return screened, dict(sorted(counts.items()))


def _evaluate_controls(candidate, training, footprint, evaluation, detected, labels):
    """Mass-match the existing two preregistered controls to this fold candidate."""
    d = distance_transform_edt(~training) * 100.0
    mass = float(candidate[evaluation].sum(dtype="float64"))
    density = gaussian_filter(training.astype("float32"), 10)
    if density.max() > 0:
        density /= density.max()
    controls = {
        "catalogue_density": density,
        "topography_only": detected.astype("float32"),
    }
    outputs = {}
    for name, values in controls.items():
        values = values.astype("float32", copy=True)
        values[~footprint | (d <= 200)] = 0
        denominator = float(values[evaluation].sum(dtype="float64"))
        if denominator > 0 and mass > 0:
            values = np.clip(values * (mass / denominator), 0, 1)
        else:
            values.fill(0)
        outputs[name] = dti(values, labels, evaluation)
        outputs[name]["prediction_mass"] = float(values[evaluation].sum(dtype="float64"))
        outputs[name]["non_vacuous"] = bool(mass > 0 and denominator > 0)
    return outputs


def evaluate_pair(records, footprint, labels, transform, orientation, detected):
    """Run H41-A and fixed H41-E side by side on each unchanged spatial fold."""
    rr, cc = np.indices(footprint.shape, sparse=True)
    fold_id = ((rr // 200) + 2 * (cc // 200)) % 4
    cfg = Config()
    folds = []
    for fold in range(4):
        print(f"Evaluate H41-A and H41-E spatial fold {fold}", flush=True)
        held = (fold_id == fold) & footprint
        forbidden = distance_transform_edt(~held) <= 3
        training = labels & ~forbidden
        polygons = [shape(g) for g, value in shapes(held.astype("uint8"), mask=held, transform=transform) if value == 1]
        exclusion_geometry = union_all(polygons).buffer(300, quad_segs=32)
        anchors, removed = drop_heldout_traces(records, forbidden, exclusion_geometry)
        e_anchors, e_counts = apply_kinematic_screen(anchors)
        evaluation = held & (distance_transform_edt(held) > 3)

        fold_models = {}
        for name, model_records in (("H41-A", anchors), ("H41-E", e_anchors)):
            corridor, _junction, distances, pairs = geometry_field(
                model_records, training, footprint, transform, cfg, forbidden=forbidden
            )
            candidate = predict(corridor, distances, orientation, detected, cfg)
            fold_models[name] = {
                "metrics": dti(candidate, labels, evaluation),
                "prediction_mass": float(candidate[evaluation].sum(dtype="float64")),
                "accepted_corridors": len(pairs),
                "eligible_anchors_by_family": {
                    str(family): sum(record["family"] == family and record["eligible"] for record in model_records)
                    for family in (0, 1)
                },
            }
            if name == "H41-E":
                fold_models[name]["matched_mass_controls"] = _evaluate_controls(
                    candidate, training, footprint, evaluation, detected, labels
                )
            del corridor, distances, candidate
            gc.collect()

        folds.append({
            "fold": fold,
            "validation_cells": int(evaluation.sum()),
            "validation_truth_pixels": int((labels & evaluation).sum()),
            "source_ids_removed": removed,
            "h41e_slip_sense_counts_after_source_withholding": e_counts,
            "models": fold_models,
        })
        del held, forbidden, training, evaluation
        gc.collect()

    means = {
        name: float(np.mean([fold["models"][name]["metrics"]["dti"] for fold in folds]))
        for name in ("H41-A", "H41-E")
    }
    control_means = {}
    for control in ("catalogue_density", "topography_only"):
        control_means[control] = float(np.mean([
            fold["models"]["H41-E"]["matched_mass_controls"][control]["dti"]
            for fold in folds
        ]))
    per_fold_not_worse = all(
        fold["models"]["H41-E"]["metrics"]["dti"] >= fold["models"]["H41-A"]["metrics"]["dti"]
        for fold in folds
    )
    strict_mean_win = means["H41-E"] > means["H41-A"]
    control_wins = {
        control: sum(
            fold["models"]["H41-E"]["matched_mass_controls"][control]["non_vacuous"]
            and fold["models"]["H41-E"]["metrics"]["dti"]
            > fold["models"]["H41-E"]["matched_mass_controls"][control]["dti"]
            for fold in folds
        )
        for control in ("catalogue_density", "topography_only")
    }
    return {
        "hypothesis_id": "H41-E",
        "design": "Fixed H41-A four-color 20 km spatial folds; complete source-feature withholding where geometry intersects held-out blocks plus 300 m; 300 m-eroded held-out interiors; unchanged DTI and unchanged H41-A geometry/topographic parameters.",
        "slip_sense_screen": {
            "NW_family_0": "SLIPSENSE exactly RL",
            "N_NNE_family_1": "SLIPSENSE exactly N",
            "ambiguous_missing_and_conflicting_values": "not eligible as corridor anchors/receivers; retained in all mapped-population distance and connected-fragment geometry",
            "source_values_not_recoded": True,
        },
        "folds": folds,
        "means": {**means, **control_means},
        "wins_of_four_vs_h41a": sum(
            fold["models"]["H41-E"]["metrics"]["dti"] > fold["models"]["H41-A"]["metrics"]["dti"]
            for fold in folds
        ),
        "wins_of_four_vs_non_vacuous_controls": control_wins,
        "strict_mean_improvement_over_h41a": strict_mean_win,
        "not_worse_in_every_fold": per_fold_not_worse,
        "clean_historical_best_oof_available": False,
        "weekly_slot_eligible": False,
        "decision": "No weekly submission slot is used. A strict proxy-fold improvement cannot establish superiority to the hidden expert-labeled test set or unavailable clean historical-best OOF predictions.",
        "limitations": [
            "The four-fold target is withheld known-fault catalogue geometry, not the hidden expert-mapped fault set.",
            "Source slip-sense values are imperfect/heterogeneous and the archive's bundled field definitions disagree with some observed RL/LL codes.",
            "Strike family remains geometric; the source attribute screen improves kinematic specificity but cannot prove reservoir connectivity or geothermal activity.",
        ],
    }


def main():
    footprint, profile, labels, elevation, valid = load_inputs()
    records = load_vectors(profile, footprint)
    orientation, detected = topo_orientation(elevation, valid)
    del elevation, valid
    result = evaluate_pair(records, footprint, labels, profile["transform"], orientation, detected)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({
        "hypothesis_id": result["hypothesis_id"],
        "means": result["means"],
        "wins_of_four_vs_h41a": result["wins_of_four_vs_h41a"],
        "wins_of_four_vs_non_vacuous_controls": result["wins_of_four_vs_non_vacuous_controls"],
        "strict_mean_improvement_over_h41a": result["strict_mean_improvement_over_h41a"],
        "not_worse_in_every_fold": result["not_worse_in_every_fold"],
        "weekly_slot_eligible": result["weekly_slot_eligible"],
        "receipt": str(OUT.relative_to(ROOT)),
    }, indent=2))


if __name__ == "__main__":
    main()
