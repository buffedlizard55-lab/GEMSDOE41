#!/usr/bin/env python3
"""Audit local competition rasters against the owner-mirror manifest and each other."""
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

from gemsdoe41.structural import sha256_file  # noqa: E402


def display_path(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)


def audit(data_dir: Path, manifest_path: Path) -> dict[str, Any]:
    template_path = data_dir / "example_submission.tif"
    faults_path = data_dir / "existing_faults.tif"
    features_path = data_dir / "training_features.tif"
    required = [template_path, faults_path, features_path, manifest_path]
    missing = [str(path) for path in required if not path.is_file()]
    if missing:
        raise FileNotFoundError("missing audit input(s): " + ", ".join(missing))

    source_manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest_items = source_manifest.get("files", [])
    expected_sha: dict[str, str] = {}
    for item in manifest_items:
        expected_sha[item["name"]] = item["sha256"]
        if item.get("canonical"):
            expected_sha[item["canonical"]] = item["sha256"]
    expected_sha["example_submission.tif"] = next(
        item["sha256"]
        for item in manifest_items
        if item["name"] == "example_submission.tif"
    )
    input_hashes = {
        "example_submission.tif": sha256_file(template_path),
        "existing_faults.tif": sha256_file(faults_path),
        "training_features.tif": sha256_file(features_path),
    }
    manifest_match = {
        name: input_hashes[name] == expected_sha.get(name)
        for name in input_hashes
    }

    with rasterio.open(template_path) as template, rasterio.open(faults_path) as faults:
        template_grid = {
            "crs": template.crs.to_string() if template.crs else None,
            "shape": [template.height, template.width],
            "transform": list(template.transform)[:6],
            "bounds": [
                template.bounds.left,
                template.bounds.bottom,
                template.bounds.right,
                template.bounds.top,
            ],
            "dtype": template.dtypes[0],
            "count": template.count,
            "nodata": "NaN" if template.nodata is not None and np.isnan(template.nodata) else template.nodata,
        }
        faults_grid = {
            "crs": faults.crs.to_string() if faults.crs else None,
            "shape": [faults.height, faults.width],
            "transform": list(faults.transform)[:6],
            "bounds": [
                faults.bounds.left,
                faults.bounds.bottom,
                faults.bounds.right,
                faults.bounds.top,
            ],
            "dtype": faults.dtypes[0],
            "count": faults.count,
            "nodata": faults.nodata,
        }
        grid_match = (
            template.crs == faults.crs
            and template.transform == faults.transform
            and template.shape == faults.shape
            and template.bounds == faults.bounds
        )
        if not grid_match:
            raise ValueError("example and fault raster grids do not match")

        pixel_counts = {
            "template_valid_pixels": 0,
            "template_positive_pixels": 0,
            "fault_positive_pixels": 0,
            "positive_mask_disagreements": 0,
            "fault_positive_outside_template_finite_mask": 0,
            "template_positive_outside_faults": 0,
        }
        for _, window in template.block_windows(1):
            template_values = template.read(1, window=window)
            fault_values = faults.read(1, window=window)
            template_valid = np.isfinite(template_values)
            template_positive = template_valid & (template_values > 0)
            fault_positive = fault_values > 0
            pixel_counts["template_valid_pixels"] += int(template_valid.sum())
            pixel_counts["template_positive_pixels"] += int(template_positive.sum())
            pixel_counts["fault_positive_pixels"] += int(fault_positive.sum())
            pixel_counts["positive_mask_disagreements"] += int(
                np.count_nonzero(template_positive != fault_positive)
            )
            pixel_counts["fault_positive_outside_template_finite_mask"] += int(
                np.count_nonzero(fault_positive & ~template_valid)
            )
            pixel_counts["template_positive_outside_faults"] += int(
                np.count_nonzero(template_positive & ~fault_positive)
            )

    with rasterio.open(features_path) as features:
        feature_grid_match = (
            features.crs == rasterio.crs.CRS.from_string(template_grid["crs"])
            and features.shape == tuple(template_grid["shape"])
            and list(features.transform)[:6] == template_grid["transform"]
        )
        descriptions = list(features.descriptions)
        det_elev_matches = [
            index
            for index, description in enumerate(descriptions, start=1)
            if description and description.split(" - ")[0].strip() == "det_elev"
        ]
        det_elev_slope_matches = [
            index
            for index, description in enumerate(descriptions, start=1)
            if description and description.split(" - ")[0].strip() == "det_elev_slope"
        ]

    return {
        "audit_utc": datetime.now(timezone.utc).isoformat(),
        "source": {
            "manifest_path": display_path(manifest_path),
            "manifest_generator": source_manifest.get("generated_by"),
            "owner_mirror_hash_match": manifest_match,
            "organizer_download_authenticated": False,
        },
        "inputs": {
            "example_submission.tif": {"path": display_path(template_path), "sha256": input_hashes["example_submission.tif"]},
            "existing_faults.tif": {"path": display_path(faults_path), "sha256": input_hashes["existing_faults.tif"]},
            "training_features.tif": {"path": display_path(features_path), "sha256": input_hashes["training_features.tif"]},
        },
        "template_grid": template_grid,
        "fault_grid": faults_grid,
        "template_fault_grid_match": grid_match,
        "feature_grid_match": feature_grid_match,
        "feature_band_count": len(descriptions),
        "det_elev_band_indices": det_elev_matches,
        "det_elev_slope_band_indices": det_elev_slope_matches,
        "pixelwise_check": {
            **pixel_counts,
            "template_positive_mask_equals_fault_positive_mask": pixel_counts["positive_mask_disagreements"] == 0,
            "irregularity": "The owner-mirror example_submission positive mask is identical to existing_faults despite the official problem page describing its sample as total fault absence. Treat its pixel values only as a footprint/grid template; never as predictions.",
        },
        "audit_passed": (
            all(manifest_match.values())
            and grid_match
            and feature_grid_match
            and det_elev_matches == [12]
            and det_elev_slope_matches == [19]
            and pixel_counts["positive_mask_disagreements"] == 0
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, default=ROOT / "data/raw")
    parser.add_argument(
        "--manifest", type=Path, default=ROOT / "data/raw/source_manifest.json"
    )
    parser.add_argument(
        "--output", type=Path, default=ROOT / "docs/evidence/h41a_raster_input_audit_20261005.json"
    )
    args = parser.parse_args()
    result = audit(args.data_dir, args.manifest)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2))
    print(f"Evidence written to {args.output}")
    return 0 if result["audit_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
