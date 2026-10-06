"""The 12-band LiDAR scarp stack: decode + scarp evidence (memory-lean).

PROVENANCE (verified in this checkout; docs/sources.html, evidence/lidar_provenance.json)
  7GEMSDOE / GEMSDOE24 `external/dem/lidar_scarp_features_u8.tif`, producer record
  `external/dem/lidar_scarp_features.json`:
      source           : USGS 3DEP 1 m DEM tiles (official bucket URLs)
      work resolution  : 2.0 m, aggregated onto the competition 100 m grid
      tiles            : 716 total (706 ok, 10 failed)
      cells with lidar : 3,892,964  (MEASURED here: 3,894,460 valid px = 75.4 % of the
                         5,167,373 in-footprint cells)
      rights           : "USGS 3DEP products are available without use restrictions"
      caveats          : "uncalibrated terrain descriptors, not fault detections";
                         "roads, channels, terrace risers, paleo-shorelines, landslides
                          and mines also create steps"

BAND DECODE (producer's `quantisation` block, transcribed line by line)
      q = 1 + round(254 * t(clip(x / xmax, 0, 1))),  t in {sqrt, linear};  0 = no lidar
      inverse: sqrt bands   x = xmax * ((q - 1)/254)**2
               linear bands x = xmax * ((q - 1)/254)
"""

from __future__ import annotations

import numpy as np
import rasterio

BANDS = (
    "ex_max", "ex_mean", "step_max", "lapneg_max", "lappos_max", "downface_max",
    "upface_max", "cross_max", "relief", "coh100", "strike", "valid",
)
QUANT = {
    "ex_max": (1.5, "sqrt"),
    "ex_mean": (0.3, "sqrt"),
    "step_max": (1.0, "sqrt"),
    "lapneg_max": (0.05, "sqrt"),
    "lappos_max": (0.05, "sqrt"),
    "downface_max": (1.0, "sqrt"),
    "upface_max": (1.0, "sqrt"),
    "cross_max": (1.0, "sqrt"),
    "relief": (300.0, "sqrt"),
    "coh100": (1.0, "linear"),
    "strike": (180.0, "linear"),
    "valid": (1.0, "linear"),
}
F32 = np.float32


def decode(band_u8: np.ndarray, name: str) -> np.ndarray:
    xmax, t = QUANT[name]
    q = band_u8.astype(F32)
    frac = np.clip((q - F32(1.0)) / F32(254.0), F32(0.0), F32(1.0))
    return (F32(xmax) * frac**2) if t == "sqrt" else (F32(xmax) * frac)


def _read(path: str, band: int) -> np.ndarray:
    with rasterio.open(path) as src:
        return src.read(band)


def _norm01(x: np.ndarray, valid: np.ndarray) -> np.ndarray:
    v = x[valid]
    if v.size == 0:
        return np.zeros_like(x)
    hi = float(np.percentile(v, 99.5))
    if hi <= 0:
        return np.zeros_like(x)
    return np.clip(x / F32(hi), F32(0.0), F32(1.0))


def load_products(path: str) -> dict:
    """Return the two products the field needs: scarp `evidence` and local `strike`.

    Bands are read one at a time and decoded to float32; nothing else is retained, so the
    peak footprint stays modest (the host for this run has 3 GB of RAM).
    """
    # --- step term: max of normalised step_max and ex_max
    valid_mask = _read(path, BANDS.index("valid") + 1)
    vm = valid_mask > 0
    b_step = _norm01(decode(_read(path, BANDS.index("step_max") + 1), "step_max"), vm)
    b_ex = _norm01(decode(_read(path, BANDS.index("ex_max") + 1), "ex_max"), vm)
    step = np.maximum(b_step, b_ex)
    del b_step, b_ex
    # --- break pair: crest convexity AND base concavity
    lapn = _norm01(decode(_read(path, BANDS.index("lapneg_max") + 1), "lapneg_max"), vm)
    lapp = _norm01(decode(_read(path, BANDS.index("lappos_max") + 1), "lappos_max"), vm)
    break_pair = np.minimum(lapn, lapp)
    del lapn, lapp
    # --- coherence
    coh = np.clip(decode(_read(path, BANDS.index("coh100") + 1), "coh100"), 0.0, 1.0)
    evidence = (F32(0.5) * step + F32(0.5) * break_pair) * coh
    evidence[~vm] = 0.0
    np.clip(evidence, 0.0, 1.0, out=evidence)
    del step, break_pair, coh
    # --- local lineament strike
    strike = np.mod(decode(_read(path, BANDS.index("strike") + 1), "strike"), F32(180.0))
    return dict(evidence=evidence.astype(F32), strike=strike.astype(F32), valid=vm, valid_px=int(vm.sum()))


def scarp_evidence_from_decoded(dec: dict[str, np.ndarray]) -> np.ndarray:
    """Same product when a caller already holds the decoded dict (tests)."""
    vm = dec["valid"] > 0
    step = np.maximum(_norm01(dec["step_max"], vm), _norm01(dec["ex_max"], vm))
    break_pair = np.minimum(_norm01(dec["lapneg_max"], vm), _norm01(dec["lappos_max"], vm))
    coh = np.clip(dec["coh100"], 0.0, 1.0)
    ev = (F32(0.5) * step + F32(0.5) * break_pair) * coh
    ev[~vm] = 0.0
    return np.clip(ev, 0.0, 1.0).astype(F32)
