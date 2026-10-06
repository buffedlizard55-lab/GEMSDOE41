"""Grid + I/O primitives for the DOE GEMS Prize (DrivenData #306) footprint.

Every constant here is MEASURED from the official competition rasters
(`existing_faults.tif`, `example_submission.tif`) whose sha256 digests are pinned in
`registry/data_manifest.json` and were verified byte-for-byte in this checkout.

Official geometry (verified 2026-10-05, sha256 match):
    width  = 3292        height = 3730
    crs    = EPSG:32611  (UTM zone 11N)
    res    = 100 m
    transform = (100, 0, 243350, 0, -100, 4508550)
    footprint = 5,167,373 px ; outside = 7,111,787 px (nodata -1 / NaN)
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import rasterio

WIDTH = 3292
HEIGHT = 3730
CRS = "EPSG:32611"
RES = 100.0
ORIGIN_X = 243350.0
ORIGIN_Y = 4508550.0
TRANSFORM = (RES, 0.0, ORIGIN_X, 0.0, -RES, ORIGIN_Y)

FOOTPRINT_PX = 5_167_373
CATALOGUE_PX = 60_988
NODATA_CATALOGUE = -1

SHAPE = (HEIGHT, WIDTH)


@dataclass(frozen=True)
class Raster:
    """A single-band float32 prediction grid plus the verified footprint mask."""

    data: np.ndarray  # (HEIGHT, WIDTH) float32 in [0, 1], NaN outside footprint
    in_footprint: np.ndarray  # (HEIGHT, WIDTH) bool


def footprint_mask(catalogue: np.ndarray) -> np.ndarray:
    """In-footprint = any pixel that is not the catalogue's nodata value."""
    if catalogue.shape != SHAPE:
        raise ValueError(f"catalogue shape {catalogue.shape} != {SHAPE}")
    return catalogue != NODATA_CATALOGUE


def read_band(path: str, band: int = 1) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(band)


def write_prediction(path: str, data: np.ndarray, dtype: str = "float32") -> None:
    """Write a single-band GeoTIFF matching the official submission format exactly."""
    data = np.asarray(data)
    if data.shape != SHAPE:
        raise ValueError(f"prediction shape {data.shape} != {SHAPE}")
    finite = data[np.isfinite(data)]
    if finite.size and (finite.min() < 0.0 or finite.max() > 1.0):
        raise ValueError(
            f"prediction outside [0, 1]: min={finite.min()!r} max={finite.max()!r}. "
            "The portal rejects this ('Predicted values must be in range [0, 1]')."
        )
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=HEIGHT,
        width=WIDTH,
        count=1,
        dtype=dtype,
        crs=CRS,
        transform=rasterio.transform.Affine(*TRANSFORM),
        nodata=np.nan,
    ) as dst:
        dst.write(data.astype(dtype), 1)


def to_submission(scores: np.ndarray, in_footprint: np.ndarray) -> np.ndarray:
    """Normalise a raw score field to [0, 1] and null everything outside the footprint."""
    out = np.asarray(scores, dtype=np.float64)
    out = np.where(in_footprint, out, 0.0)
    lo, hi = float(out.min()), float(out.max())
    if hi > lo:
        out = (out - lo) / (hi - lo)
    else:
        out = np.zeros_like(out)
    out = np.clip(out, 0.0, 1.0).astype("float32")
    out[~in_footprint] = np.nan
    return out
