"""Audit cross-run raster reproducibility on the template's valid footprint.

Artifact SHA-256 identifies exact delivered bytes. Scientific cross-run comparison
requires the same grid and valid-data mask, finite [0,1] values inside that mask, and
at most 8 float32 epsilons of absolute error. Outside-footprint storage is also recorded
and must match exactly; the mask may represent outside values as numeric zeros or NaNs.
"""
import json
from pathlib import Path

import numpy as np
import rasterio
from download_data import sha256


def compare(expected_path, actual_path):
    with rasterio.open(expected_path) as expected, rasterio.open(actual_path) as actual:
        assert (
            expected.shape == actual.shape
            and expected.crs == actual.crs
            and expected.transform == actual.transform
            and expected.bounds == actual.bounds
        )
        valid = expected.dataset_mask() > 0
        actual_valid = actual.dataset_mask() > 0
        assert np.array_equal(valid, actual_valid)
        assert valid.any(), "template has no valid pixels"

        expected_values = expected.read(1)
        actual_values = actual.read(1)
        expected_inside = expected_values[valid]
        actual_inside = actual_values[valid]
        assert np.isfinite(expected_inside).all()
        assert np.isfinite(actual_inside).all()
        assert 0 <= expected_inside.min() <= expected_inside.max() <= 1
        assert 0 <= actual_inside.min() <= actual_inside.max() <= 1

        expected_outside = expected_values[~valid]
        actual_outside = actual_values[~valid]
        outside_values_exact = bool(
            np.array_equal(expected_outside, actual_outside, equal_nan=True)
        )
        delta = np.abs(
            expected_inside.astype("float64") - actual_inside.astype("float64")
        )
        tolerance = 8 * np.finfo("float32").eps
        result = {
            "expected_sha256": sha256(expected_path),
            "actual_sha256": sha256(actual_path),
            "valid_cells_compared": int(valid.sum()),
            "exact_pixels": bool(np.array_equal(expected_inside, actual_inside)),
            "different_pixels": int(np.count_nonzero(expected_inside != actual_inside)),
            "max_absolute_error": float(delta.max(initial=0.0)),
            "sum_absolute_error": float(delta.sum()),
            "outside_values_exact": outside_values_exact,
            "outside_expected_all_nan": bool(
                expected_outside.size == 0 or np.isnan(expected_outside).all()
            ),
            "outside_actual_all_nan": bool(
                actual_outside.size == 0 or np.isnan(actual_outside).all()
            ),
            "absolute_tolerance": float(tolerance),
            "numerically_reproducible": bool(
                delta.max(initial=0.0) <= tolerance and outside_values_exact
            ),
        }
    print("::notice title=Cross-run raster comparison::" + json.dumps(result))
    return result


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("expected")
    parser.add_argument("actual")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    result = compare(args.expected, args.actual)
    Path(args.output).write_text(json.dumps(result, indent=2) + "\n")
    if not result["numerically_reproducible"]:
        raise SystemExit("Rebuilt field or outside encoding differs beyond the fixed tolerance")
