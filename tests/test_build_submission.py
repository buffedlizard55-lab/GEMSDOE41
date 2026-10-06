import sys
from pathlib import Path

import numpy as np
import rasterio
from rasterio.transform import from_origin

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_h41a_raster_submission import compare_prior_rasters  # noqa: E402


def _write_raster(path, transform):
    values = np.zeros((6, 8), dtype=np.float32)
    values[2, 3] = 0.5
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=values.shape[0],
        width=values.shape[1],
        count=1,
        dtype="float32",
        crs="EPSG:32611",
        transform=transform,
        nodata=np.nan,
    ) as dst:
        dst.write(values, 1)


def test_prior_comparison_checks_transform_against_template_grid(tmp_path):
    template = tmp_path / "template.tif"
    aligned = tmp_path / "aligned.tif"
    shifted = tmp_path / "shifted.tif"
    transform = from_origin(243350, 4508550, 100, 100)
    _write_raster(template, transform)
    _write_raster(aligned, transform)
    _write_raster(shifted, from_origin(243450, 4508550, 100, 100))

    candidate = np.zeros((6, 8), dtype=np.float32)
    candidate[2, 3] = 0.6
    footprint = np.ones(candidate.shape, dtype=bool)
    results = compare_prior_rasters(candidate, footprint, [aligned, shifted], template)

    assert results[0]["comparable"] is True
    assert results[0]["intersection"] == 1
    assert results[1]["comparable"] is False
    assert results[1]["reason"] == "transform mismatch to template"
