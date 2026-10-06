#!/usr/bin/env python3
"""Independently reopen the H41-A-R GeoTIFF and validate it against its template."""
from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def validate(
    submission_path: Path,
    template_path: Path,
    expected_mass: float,
    prior_paths: list[Path],
) -> dict[str, Any]:
    with rasterio.open(template_path) as template:
        template_values = template.read(1)
        footprint = np.isfinite(template_values)
        if template.nodata is not None and np.isfinite(template.nodata):
            footprint &= ~np.isclose(
                template_values, template.nodata, rtol=0.0, atol=0.0
            )
        expected = {
            "crs": template.crs,
            "shape": template.shape,
            "transform": template.transform,
            "bounds": template.bounds,
        }
    with rasterio.open(submission_path) as dataset:
        values = dataset.read(1)
        nodata_is_nan = dataset.nodata is not None and np.isnan(dataset.nodata)
        same_grid = (
            dataset.crs == expected["crs"]
            and dataset.shape == expected["shape"]
            and dataset.transform == expected["transform"]
            and dataset.bounds == expected["bounds"]
        )
        inside = values[footprint]
        outside = values[~footprint]
        inside_finite = bool(np.isfinite(inside).all())
        outside_nan = bool(outside.size == 0 or np.isnan(outside).all())
        in_range = bool(
            inside_finite
            and np.all((inside >= 0.0) & (inside <= 1.0))
        )
        mass = float(inside.sum(dtype=np.float64))
        receipt: dict[str, Any] = {
            "audit_utc": datetime.now(timezone.utc).isoformat(),
            "submission_path": display_path(submission_path),
            "template_path": display_path(template_path),
            "sha256": sha256(submission_path),
            "crs": dataset.crs.to_string() if dataset.crs else None,
            "shape": [dataset.height, dataset.width],
            "dtype": dataset.dtypes[0],
            "band_count": dataset.count,
            "transform": list(dataset.transform)[:6],
            "bounds": [
                dataset.bounds.left,
                dataset.bounds.bottom,
                dataset.bounds.right,
                dataset.bounds.top,
            ],
            "nodata": "NaN" if nodata_is_nan else dataset.nodata,
            "matches_template_grid": same_grid,
            "inside_footprint_pixels": int(footprint.sum()),
            "outside_footprint_pixels": int((~footprint).sum()),
            "inside_footprint_all_finite": inside_finite,
            "outside_footprint_all_nan": outside_nan,
            "in_footprint_values_within_0_1": in_range,
            "in_footprint_min": float(inside.min()) if inside.size else None,
            "in_footprint_max": float(inside.max()) if inside.size else None,
            "positive_pixels": int(np.count_nonzero(inside > 0)),
            "probability_mass": mass,
            "expected_probability_mass": float(expected_mass),
            "mass_absolute_error": abs(mass - expected_mass),
            "mass_matches_target_within_0_01": abs(mass - expected_mass) <= 0.01,
            "prior_support_comparisons": [],
        }

    candidate_support = footprint & (values > 0)
    for prior_path in prior_paths:
        with rasterio.open(prior_path) as prior_ds:
            if (
                prior_ds.crs != expected["crs"]
                or prior_ds.shape != expected["shape"]
                or prior_ds.transform != expected["transform"]
                or prior_ds.bounds != expected["bounds"]
            ):
                receipt["prior_support_comparisons"].append(
                    {
                        "path": display_path(prior_path),
                        "comparable": False,
                        "reason": "grid mismatch to template",
                    }
                )
                continue
            prior = prior_ds.read(1)
        prior_support = footprint & np.isfinite(prior) & (prior > 0)
        intersection = int(np.count_nonzero(candidate_support & prior_support))
        union = int(np.count_nonzero(candidate_support | prior_support))
        candidate_count = int(candidate_support.sum())
        receipt["prior_support_comparisons"].append(
            {
                "path": display_path(prior_path),
                "sha256": sha256(prior_path),
                "comparable": True,
                "candidate_nonzero": candidate_count,
                "prior_nonzero": int(prior_support.sum()),
                "intersection": intersection,
                "jaccard": intersection / union if union else 1.0,
                "candidate_contained_in_prior": intersection / candidate_count if candidate_count else 0.0,
            }
        )

    receipt["format_audit_passed"] = bool(
        receipt["crs"] == "EPSG:32611"
        and receipt["shape"] == [3730, 3292]
        and receipt["dtype"] == "float32"
        and receipt["band_count"] == 1
        and nodata_is_nan
        and same_grid
        and inside_finite
        and outside_nan
        and in_range
        and receipt["mass_matches_target_within_0_01"]
    )
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--submission",
        type=Path,
        default=ROOT / "docs/downloads/gemsdoe41-h41a-raster-bimodal-transfer-20261005.tif",
    )
    parser.add_argument("--template", type=Path, help="override sample_submission.tif or example_submission.tif template")
    parser.add_argument("--expected-mass", type=float, default=30000.0)
    parser.add_argument("--compare-raster", type=Path, action="append", default=[])
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/evidence/h41a_raster_format_audit.json"
    )
    args = parser.parse_args()
    template_path = args.template or next(
        (
            path
            for path in (
                ROOT / "data/sample_submission.tif",
                ROOT / "data/raw/example_submission.tif",
            )
            if path.is_file()
        ),
        ROOT / "data/sample_submission.tif",
    )
    receipt = validate(args.submission, template_path, args.expected_mass, args.compare_raster)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(receipt, indent=2))
    print(f"Independent format audit: {'PASS' if receipt['format_audit_passed'] else 'FAIL'}")
    print(f"Evidence written to {args.output}")
    return 0 if receipt["format_audit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
