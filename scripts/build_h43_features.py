#!/usr/bin/env python3
"""H43 feature stack: the official 19 competition bands + independent terrain products,
materialised once as a pixel-interleaved float32 memmap so a 3 GB / 2-core host can train
and predict over all 5.1 million scored pixels without ever holding the 419 MB source
raster and its derivatives in RAM at the same time.

Every feature is an OBSERVATION from an official source:
  * bands 1-19  : `training_features.tif`, the organizer feature raster (band names read
                  from the file's own per-band tags, transcribed in the FEATURE_NAMES table).
  * bands 20-26 : local morphology of the organizer's own detrended elevation and of the
                  official magnetic / gravity / geodetic gradient bands (numpy/scipy only).
  * bands 27-29 : USGS 3DEP 1 m derived scarp morphology, from the checksum-pinned
                  `external/lidar_scarp_features_u8.tif` (provenance in `src/gems41/lidar.py`).

Sentinel handling: `training_features.tif` stores nodata as -3.4028234663852886e+38 on
3,061 pixels INSIDE the scoring footprint (measured here, matching the sibling project's
independent measurement).  Those cells are replaced by the band's in-footprint median, and
a `sentinel` indicator feature records where it happened, so no -3.4e38 value can ever reach
a submission and the portal's "Predicted values must be in range [0, 1]" rejection cannot
be triggered by an input artefact.

Run:  .venv/bin/python scripts/build_h43_features.py
Writes data/derived/h43_features.f32  and  evidence/h43_feature_receipt.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import maximum_filter, uniform_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from gems41 import lidar as L  # noqa: E402

F32 = np.float32
DATA = ROOT / "data"
DERIVED = DATA / "derived"
OUT = DERIVED / "h43_features.f32"

BAND_NAMES = {
    1: "mag_anom", 2: "rtp", 3: "tmi_hg", 4: "geod_2ndinv", 5: "iso_grav_anom_slope",
    6: "tc", 7: "geod_shearrate", 8: "geod_dilaterate", 9: "tmi_vg", 10: "deq_n100a15",
    11: "iso_grav_anom_vg", 12: "det_elev", 13: "iso_grav_anom", 14: "tmi",
    15: "depth_to_base_surf", 16: "ieq_n100a15", 17: "cond_surf", 18: "iso_grav_anom_hg",
    19: "det_elev_slope",
}

# name, kind
DERIVED_FEATURES = [
    ("det_elev_std5", "std5_12"),
    ("det_elev_coherence5", "coh5_12"),
    ("det_elev_maxcurv", "curv_12"),
    ("tmi_hg_max3", "max3_3"),
    ("iso_grav_hg_max3", "max3_18"),
    ("geod_2ndinv_max3", "max3_4"),
    ("depth_base_gradmag", "grad_15"),
    ("lidar_scarp_evidence", "lidar_ev"),
    ("lidar_strike_nw_align", "lidar_nw"),
    ("lidar_strike_nne_align", "lidar_nne"),
    ("lidar_valid", "lidar_valid"),
    ("input_sentinel_count", "sentinel"),
]


def feature_names() -> list[str]:
    return [BAND_NAMES[i] for i in range(1, 20)] + [n for n, _ in DERIVED_FEATURES]


def _std5(x: np.ndarray) -> np.ndarray:
    m = uniform_filter(x, 5)
    m2 = uniform_filter(x * x, 5)
    return np.sqrt(np.maximum(m2 - m * m, 0.0))


def _coherence5(x: np.ndarray) -> np.ndarray:
    """Structure-tensor coherence: 1 = perfectly lineated, 0 = isotropic.  Scale 5 px."""
    gy, gx = np.gradient(x.astype(np.float64))
    jxx = uniform_filter(gx * gx, 5)
    jyy = uniform_filter(gy * gy, 5)
    jxy = uniform_filter(gx * gy, 5)
    tr = jxx + jyy
    det = jxx * jyy - jxy * jxy
    disc = np.sqrt(np.maximum(tr * tr - 4.0 * det, 0.0))
    l1 = 0.5 * (tr + disc)
    l2 = 0.5 * (tr - disc)
    with np.errstate(divide="ignore", invalid="ignore"):
        c = np.where(l1 > 1e-9, (l1 - l2) / l1, 0.0)
    return np.clip(np.nan_to_num(c), 0.0, 1.0).astype(F32)


def _curv(x: np.ndarray) -> np.ndarray:
    """Signed laplacian of the surface (scarp break-in-slope detector)."""
    k = np.array([[0.0, 1.0, 0.0], [1.0, -4.0, 1.0], [0.0, 1.0, 0.0]], F32)
    from scipy.signal import convolve2d

    return convolve2d(x.astype(F32), k, mode="same", boundary="symm").astype(F32)


def _gradmag(x: np.ndarray) -> np.ndarray:
    gy, gx = np.gradient(np.nan_to_num(x.astype(np.float64), nan=0.0))
    return np.hypot(gy, gx).astype(F32)


def angular_similarity(strike_deg: np.ndarray, ref_deg: float) -> np.ndarray:
    """|cos 2(theta - ref)| : 1 when the local lineament is parallel to the reference strike."""
    d = np.deg2rad(strike_deg.astype(np.float64) - float(ref_deg))
    return np.abs(np.cos(2.0 * d)).astype(F32)


def main() -> int:
    t0 = time.time()
    DERIVED.mkdir(parents=True, exist_ok=True)
    with rasterio.open(DATA / "existing_faults.tif") as src:
        cat = src.read(1)
    shape = cat.shape
    n = int(np.prod(shape))
    foot = cat != -1
    names = feature_names()
    F = len(names)

    mm = np.memmap(OUT, dtype=np.float32, mode="w+", shape=(n, F))
    receipt = dict(created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   path=str(OUT.relative_to(ROOT)), shape=[n, F], features=names,
                   footprint_px=int(foot.sum()), notes=[])

    # ---- the 19 official bands, sentinel-sanitised ----
    sentinel_total = 0
    with rasterio.open(DATA / "training_features.tif") as src:
        for i in range(1, 20):
            b = src.read(i).astype(np.float64)
            tag = src.tags(i)
            assert tag.get("band_name") == BAND_NAMES[i], (
                f"band {i} tag {tag.get('band_name')!r} != expected {BAND_NAMES[i]!r}")
            bad = (~np.isfinite(b)) | (b < -1e38)
            sentinel_total += int((bad & foot).sum())
            if bad.any():
                med = float(np.median(b[foot & ~bad])) if (foot & ~bad).any() else 0.0
                b = np.where(bad, med, b)
            mm[:, i - 1] = b.ravel().astype(F32)
            del b
            print(f"  band {i:2d} {BAND_NAMES[i]:20s} ({time.time()-t0:.0f}s)", flush=True)
    receipt["sentinel_cells_inside_footprint"] = sentinel_total

    def _clean(i: int) -> np.ndarray:
        with rasterio.open(DATA / "training_features.tif") as src:
            b = src.read(i).astype(np.float64)
        bad = (~np.isfinite(b)) | (b < -1e38)
        if bad.any():
            b = np.where(bad, float(np.median(b[foot & ~bad])) if (foot & ~bad).any() else 0.0, b)
        return b.astype(np.float32)

    e12, e3, e18, e4, e15 = _clean(12), _clean(3), _clean(18), _clean(4), _clean(15)

    base = 19
    lid = L.load_products(str(DATA / "external" / "lidar_scarp_features_u8.tif"))
    receipt["lidar_valid_px"] = lid["valid_px"]
    sentinel_field = np.zeros(shape, F32)
    with rasterio.open(DATA / "training_features.tif") as src:
        for i in range(1, 20):
            b = src.read(i)
            sentinel_field += ((~np.isfinite(b)) | (b < -1e38)).astype(F32)
            del b
    for j, (nm, kind) in enumerate(DERIVED_FEATURES):
        if kind == "std5_12":
            v = _std5(e12)
        elif kind == "coh5_12":
            v = _coherence5(e12)
        elif kind == "curv_12":
            v = _curv(e12)
        elif kind == "max3_3":
            v = maximum_filter(e3, 3).astype(F32)
        elif kind == "max3_18":
            v = maximum_filter(e18, 3).astype(F32)
        elif kind == "max3_4":
            v = maximum_filter(e4, 3).astype(F32)
        elif kind == "grad_15":
            v = _gradmag(e15)
        elif kind == "lidar_ev":
            v = lid["evidence"]
        elif kind == "lidar_nw":
            v = np.where(lid["valid"], angular_similarity(lid["strike"], 135.0), 0.0).astype(F32)
        elif kind == "lidar_nne":
            v = np.where(lid["valid"], angular_similarity(lid["strike"], 15.0), 0.0).astype(F32)
        elif kind == "lidar_valid":
            v = lid["valid"].astype(F32)
        elif kind == "sentinel":
            v = sentinel_field
        else:
            raise ValueError(kind)
        v = np.nan_to_num(np.asarray(v, np.float64), nan=0.0, posinf=0.0, neginf=0.0)
        mm[:, base + j] = v.ravel().astype(F32)
        print(f"  derived {nm:24s} ({time.time()-t0:.0f}s)", flush=True)
        del v
    del lid, sentinel_field

    mm.flush()
    del mm
    receipt["runtime_s"] = round(time.time() - t0, 1)
    receipt["bytes"] = OUT.stat().st_size
    # re-open and verify every feature is finite
    chk = np.memmap(OUT, dtype=np.float32, mode="r", shape=(n, F))
    lo = np.full(F, np.inf, np.float64)
    hi = np.full(F, -np.inf, np.float64)
    bad = 0
    step = 1 << 19
    for a in range(0, n, step):
        blk = np.asarray(chk[a:a + step])
        bad += int((~np.isfinite(blk)).sum())
        lo = np.minimum(lo, np.nanmin(blk, axis=0))
        hi = np.maximum(hi, np.nanmax(blk, axis=0))
    receipt["nonfinite_feature_cells"] = bad
    assert bad == 0, "non-finite values written to the feature memmap"
    receipt["per_feature_minmax"] = {names[j]: [float(lo[j]), float(hi[j])] for j in range(F)}
    del chk
    (ROOT / "evidence" / "h43_feature_receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({k: v for k, v in receipt.items() if k != "per_feature_minmax"}, indent=1))
    print(f"done in {time.time()-t0:.0f}s")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
