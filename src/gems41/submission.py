"""Submission assembly + the portal checks that must pass before a file is offered.

THE PORTAL'S OWN REQUIREMENTS (official, page 967 "Submission format", verified 2026-10-05)
  * same projected CRS as the training data (UTM 11N / EPSG:32611)
  * same resolution as the training data (100 m)
  * same bounds, data outside the bounds null or NaN
  * a single layer, 32-bit float, values between 0 and 1

AND THE ERROR THE OWNER HIT ON THE REAL SUBMISSION FORM
  "Predicted values must be in range [0, 1]"
  -> the field is clipped into [0, 1] and re-read from the bytes on disk before the file is
     offered for download; `check()` is the gate.

COMPRESSION: DEFLATE with horizontal differencing (predictor 2) and 512x512 tiles.
The same footprint costs 49 MB uncompressed and ~0.4 MB compressed; the previous session's
49 MB download is the reason this is explicit here.
"""

from __future__ import annotations

import hashlib
import json
import os
import zipfile

import numpy as np
import rasterio

from . import grid as G


def sha256(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def check(path: str, footprint: np.ndarray | None = None) -> dict:
    """Re-read the bytes on disk and verify every official format requirement."""
    with rasterio.open(path) as src:
        arr = src.read(1)
        checks = {
            "driver_gtiff": src.driver == "GTiff",
            "single_band": src.count == 1,
            "dtype_float32": src.dtypes[0] == "float32",
            "crs_epsg32611": str(src.crs) == G.CRS,
            "width_3292": src.width == G.WIDTH,
            "height_3730": src.height == G.HEIGHT,
            "res_100m": tuple(round(float(r), 6) for r in src.res) == (100.0, 100.0),
            "transform_matches": all(
                abs(a - b) < 1e-6 for a, b in zip(tuple(src.transform)[:6], G.TRANSFORM)
            ),
        }
        nodata = src.nodata

    nan = np.isnan(arr)
    vals = arr[~nan]
    checks.update(
        {
            "values_in_0_1": bool(vals.size == 0 or (vals.min() >= 0.0 and vals.max() <= 1.0)),
            "all_values_finite_or_nan": bool(np.isfinite(arr[~nan]).all()),
            "has_mass": bool(vals.size and (vals > 0).any()),
            "n_positive_px": int((vals > 0).sum()),
            "min": float(vals.min()) if vals.size else None,
            "max": float(vals.max()) if vals.size else None,
            "nodata_nan": (nodata is None) or bool(np.isnan(nodata)),
        }
    )
    if footprint is not None:
        fp = np.asarray(footprint, bool)
        checks["nothing_outside_footprint"] = bool((arr[~fp] == 0).all() or np.isnan(arr[~fp]).all())
        checks["nan_exactly_outside_footprint"] = bool(np.array_equal(nan, ~fp))
        checks["mass_inside_footprint_only"] = bool((vals > 0).sum() == (arr[fp] > 0).sum())
    checks["sha256"] = sha256(path)
    checks["bytes"] = os.path.getsize(path)
    checks["path"] = path
    checks["all_pass"] = bool(
        all(v for k, v in checks.items() if isinstance(v, bool)) and checks["n_positive_px"] > 0
    )
    return checks


def finalize(
    mask: np.ndarray,
    footprint: np.ndarray,
    *,
    name: str,
    outdir: str = "docs/downloads",
    value: float = 1.0,
    make_zip: bool = True,
    stamp: str = "20261005T000000Z",
) -> dict:
    """Write the single-band float32 GeoTIFF and gate it on `check`."""
    os.makedirs(outdir, exist_ok=True)
    data = np.zeros(mask.shape, dtype="float32")
    data[mask & footprint] = np.float32(value)
    data[~footprint] = np.nan
    fname = f"gemsdoe41-{name}-{stamp}.tif"
    path = os.path.join(outdir, fname)
    _write(path, data)
    checks = check(path, footprint)
    if not checks["all_pass"]:
        raise RuntimeError(f"portal checks failed for {path}: {checks}")
    if make_zip:
        zpath = path[:-4] + ".zip"
        with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(path, arcname=os.path.basename(path))
        checks["zip_path"] = zpath
        checks["zip_bytes"] = os.path.getsize(zpath)
    json.dump(checks, open(path + ".checks.json", "w"), indent=1)
    return checks


def _write(path: str, data: np.ndarray) -> None:
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=G.HEIGHT,
        width=G.WIDTH,
        count=1,
        dtype="float32",
        crs=G.CRS,
        transform=rasterio.transform.Affine(*G.TRANSFORM),
        nodata=float("nan"),
        compress="deflate",
        predictor=2,
        tiled=True,
        blockxsize=512,
        blockysize=512,
        zlevel=9,
    ) as dst:
        dst.write(data, 1)
