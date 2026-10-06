#!/usr/bin/env python3
"""Which evidence actually predicts faults that are NOT in the catalogue?

For every evidence layer this project can obtain, and for every archived artifact whose
reported score is on the ledger, compute the mass-weighted lift of that layer under the
file's own dots:

        lift = mean(layer | dots) / mean(layer | footprint)

A layer is a candidate predictor of the hidden set to the degree that (i) it is itself
lifted where independent-map (SGMC off-catalogue) faults are, and (ii) the *successful*
archived files sit on high values of it.  Both columns are reported, so the design of the
H42 surface can be justified from measurement instead of intuition.

Output: evidence/evidence_lift.json
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems41 import lidar as L  # noqa: E402

F32 = np.float32
BLOCK_PX = 200

ARCHIVED = [
    ("H33-2-B2", "data/comparison-h33.tif", 0.2778),
    ("H27-4-solo-d2.8", "data/scored/r02708-h27-4-solo-d2-8.tif", 0.2708),
    ("H32-1-prethin", "data/scored/r02649-h32-1-prethin-tip-euler.tif", 0.2649),
    ("H33d-stepover", "data/scored/r02632-h33d-analog-tip-stepover.tif", 0.2632),
    ("dotted-d2.8-44090", "data/scored/r02600-dotted-d2-8-44090.tif", 0.2600),
    ("dotted-d1.5", "data/scored/r02477-dotted-d1-5.tif", 0.2477),
    ("topo-gap-d1.5", "data/scored/r02449-topo-gap-closure-d1-5.tif", 0.2449),
    ("h19-5-powerlaw", "data/scored/r01922-h19-5-powerlaw.tif", 0.1922),
    ("h19-4-multiline", "data/scored/r01894-h19-4-multiline.tif", 0.1894),
    ("h16-1-topo-geophys", "data/scored/r01855-h16-1-topo-geophys.tif", 0.1855),
    ("h28-dotted-ridge", "data/scored/r01839-h28-dotted-ridge.tif", 0.1839),
    ("hedge-v2", "data/scored/r01563-hedge-v2.tif", 0.1563),
    ("ens12", "data/scored/r01563-ens12-adopted.tif", 0.1563),
    ("h25-ctx-ridge", "data/scored/r01280-h25-ctx-ridge.tif", 0.1280),
    ("r13-lattice", "data/scored/r00904-r13-lattice-s5.tif", 0.0904),
    ("placeholder-2314b599", "data/scored/r00107-placeholder-2314b599.tif", 0.0107),
]


def read_band(path: Path, band: int) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(band).astype(F32)
    a[~np.isfinite(a)] = 0.0
    a[a < -1e37] = 0.0
    return a


def main() -> None:
    cat = read_band(ROOT / "data/existing_faults.tif", 1) > 0.5
    with rasterio.open(ROOT / "data/sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as s:
        sgmc = s.read(1) > 0
    rows, cols = np.mgrid[0:cat.shape[0], 0:cat.shape[1]]
    parity = ((rows // BLOCK_PX) + (cols // BLOCK_PX)) % 2 == 0
    d_cat = distance_transform_edt(~cat).astype(F32)
    truth = sgmc & (d_cat > 3.0) & foot

    # ---------------- evidence layers ----------------
    layers: dict[str, np.ndarray] = {}
    tp = ROOT / "data/training_features.tif"
    band_names = {4: "band04_geod_2ndinv", 7: "band07_geod_shearrate", 12: "band12_det_elev",
                  15: "band15_depth_to_base", 16: "band16_ieq_density", 17: "band17_cond_surf",
                  3: "band03_tmi_hg", 18: "band18_iso_grav_hg", 19: "band19_det_elev_slope"}
    for idx, name in band_names.items():
        layers[name] = gaussian_filter(read_band(tp, idx), 2.0)
    prod = L.load_products(str(ROOT / "data/external/lidar_scarp_features_u8.tif"))
    layers["lidar_scarp_evidence"] = gaussian_filter(prod["evidence"], 2.0)
    layers["dist_to_catalogue_px"] = d_cat
    layers["near_catalogue_5px"] = np.exp(-d_cat / F32(5.0))
    # catalogue density itself (a control that must NOT dominate)
    layers["catalogue_density_10px"] = gaussian_filter(cat.astype(F32), 10.0)
    # independent-map density, in half A only, so its column is not circular w.r.t. truth B
    layers["sgmc_density_halfA"] = gaussian_filter((sgmc & parity & (d_cat > 3)).astype(F32), 3.0)
    # thermal anomaly density
    tr, tc, tt = [], [], []
    with open(ROOT / "data/external/gdr_wellspring_in_footprint.csv") as fh:
        for rec in csv.DictReader(fh):
            try:
                temp = float(rec["temp_c"])
            except (TypeError, ValueError):
                continue
            cls = (rec.get("thermalclass") or "").strip()
            if temp < 20.0 and cls not in ("Hot", "Warm"):
                continue
            r, c = int(rec["row"]), int(rec["col"])
            if 0 <= r < cat.shape[0] and 0 <= c < cat.shape[1]:
                tr.append(r); tc.append(c); tt.append(temp)
    g = np.zeros(cat.shape, F32)
    np.add.at(g, (np.array(tr), np.array(tc)), np.clip((np.array(tt) - 20) / 60, 0, 1))
    layers["thermal_density_offcat"] = gaussian_filter(g, 3.0)

    # ---------------- lifts ----------------
    def lift(layer: np.ndarray, mask: np.ndarray) -> dict:
        base = layer[foot & (layer > 0)]
        sel = layer[mask & foot]
        base_mean = float(base.mean()) if base.size else 0.0
        return dict(n=int(mask.sum()), mean_selected=float(sel.mean()) if sel.size else 0.0,
                    mean_footprint=base_mean,
                    lift=float(sel.mean() / base_mean) if base_mean > 0 and sel.size else None,
                    frac_above_footprint_median=float((sel > np.median(layer[foot])).mean()) if sel.size else None)

    out: dict[str, dict] = {}
    out["truth_sgmc_offcatalogue"] = {name: lift(layer, truth) for name, layer in layers.items()}
    # truth half B (used as the validation half) and half A
    for tag, m in (("truth_halfB", truth & ~parity), ("truth_halfA", truth & parity)):
        out[tag] = {name: lift(layer, m) for name, layer in layers.items()}
    for name, rel, score in ARCHIVED:
        p = ROOT / rel
        if not p.exists():
            continue
        a = read_band(p, 1)
        m = a > 0
        out[f"file:{name}"] = {k: lift(layer, m) for k, layer in layers.items()}
        out[f"file:{name}"]["_meta"] = dict(reported_score=score, dots=int(m.sum()),
                                            median_dist_to_catalogue_px=float(np.median(d_cat[m])) if m.any() else None)
    (ROOT / "evidence/evidence_lift.json").write_text(json.dumps(out, indent=1) + "\n")

    # console: lift on the SGMC truth, ranked
    print(f"{'layer':26s} {'lift@truthB':>11s} {'sel':>9s} {'frac>median':>11s}")
    ranked = sorted(out["truth_halfB"].items(), key=lambda kv: -(kv[1]["lift"] or 0))
    for k, v in ranked:
        print(f"{k:26s} {v['lift'] or 0:11.2f} {v['mean_selected']:9.4f} "
              f"{v['frac_above_footprint_median'] or 0:11.3f}")
    print()
    print("top-file mean lift per layer (H33-2-B2 vs worst file):")
    for k in layers:
        a = out["file:H33-2-B2"][k]["lift"] or 0
        b = out["file:placeholder-2314b599"][k]["lift"] or 0
        print(f"  {k:26s} H33={a:6.2f}  placeholder={b:6.2f}")


if __name__ == "__main__":
    main()
