#!/usr/bin/env python3
"""Admissibility probe: can any surface reach the ledger's hidden-truth profile?

The full sweep (evidence/h42_submission.json) found that every candidate that scores well on the
independent-map instrument does so by carpeting high detrended elevation (det_elev enrichment
1.5-2.1) while the five highest-scoring archived artifacts sit *below* the footprint average
(det_elev enrichment 0.89).  Mass-controlled partial correlation across the 16-file ledger says
that mismatch is the wrong direction (det_elev rho_partial -0.56).

This probe asks the narrow question: if emission is restricted to the low detrended-elevation
band (basin fill), what happens to (a) the instrument projection and (b) the profile?  It only
reads public/provided layers and the archived artifacts; it uses SGMC as the instrument truth on
the non-feature half only, exactly as the builder does.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems41 import lidar as L  # noqa: E402
from gems41.metric import dti  # noqa: E402
from gemsdoe41 import density as D  # noqa: E402

F32 = np.float32
BLOCK = 200
K = 14_088
LAM = 1.76
ARCHIVED = [
    ("H33-2-B2", "data/comparison-h33.tif", 0.2778),
    ("H27-4-solo-d2.8", "data/scored/r02708-h27-4-solo-d2-8.tif", 0.2708),
    ("H32-1-prethin", "data/scored/r02649-h32-1-prethin-tip-euler.tif", 0.2649),
    ("H33d-stepover", "data/scored/r02632-h33d-analog-tip-stepover.tif", 0.2632),
    ("dotted-d2.8-44090", "data/scored/r02600-dotted-d2-8-44090.tif", 0.2600),
]


def rb(p, b=1):
    with rasterio.open(p) as s:
        a = s.read(b).astype(F32)
    a[~np.isfinite(a)] = 0.0
    a[a < -1e37] = 0.0
    return a


def main() -> None:
    cat = rb(ROOT / "data/existing_faults.tif") > 0.5
    with rasterio.open(ROOT / "data/sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as s:
        sgmc = s.read(1) > 0
    rr, cc = np.mgrid[0:cat.shape[0], 0:cat.shape[1]]
    parity = ((rr // BLOCK) + (cc // BLOCK)) % 2 == 0
    d_cat = distance_transform_edt(~cat).astype(F32)
    truth = sgmc & (d_cat > 3.0) & foot
    tA, tB = truth & parity, truth & ~parity
    open_allowed = foot & ~cat
    slope = D.norm01(D.smooth(rb(ROOT / "data/training_features.tif", 19), 1.0), foot)
    det_elev = D.norm01(D.smooth(rb(ROOT / "data/training_features.tif", 12), 1.0), foot)
    tmi = D.norm01(D.smooth(rb(ROOT / "data/training_features.tif", 3), 1.0), foot)
    scarp = D.norm01(D.smooth(L.load_products(str(ROOT / "data/external/lidar_scarp_features_u8.tif"))["evidence"], 1.0), foot)
    mapA = D.norm01(D.smooth((sgmc & parity & (d_cat > 3)).astype(F32), 3.0), foot)
    mapB = D.norm01(D.smooth((sgmc & ~parity & (d_cat > 3)).astype(F32), 3.0), foot)
    near_cat = np.exp(-d_cat / F32(15.0)).astype(F32)

    layers = {"slope": slope, "scarp": scarp, "tmi_hg": tmi, "det_elev": det_elev, "dist_cat": d_cat}
    base = {k: float(v[foot].mean()) for k, v in layers.items()}
    ref = {}
    for _, rel, _ in ARCHIVED:
        m = rb(ROOT / rel) > 0
        ref.setdefault("rows", []).append({k: float(layers[k][m].mean() / base[k]) for k in layers})
    ref_profile = {k: float(np.mean([r[k] for r in ref["rows"]])) for k in layers}
    print("top5 reference profile:", json.dumps({k: round(v, 3) for k, v in ref_profile.items()}))

    def surfaces(feat):
        return {
            "SA_slope_scarp": D.geometric_mean({"s": slope, "k": scarp}, {"s": 0.6, "k": 0.4}),
            "SF_basinmargin": D.geometric_mean(
                {"f": (slope ** 0.5) * ((1 - np.clip(det_elev, 0, 1)) ** 0.5), "k": scarp,
                 "t": tmi, "n": near_cat}, {"f": 0.40, "k": 0.30, "t": 0.15, "n": 0.15}),
            "SH_front_heavy": D.geometric_mean(
                {"f": ((slope ** 0.5) * ((1 - np.clip(det_elev, 0, 1)) ** 0.5)) ** 0.7,
                 "k": scarp, "t": tmi}, {"f": 0.40, "k": 0.30, "t": 0.30}),
        }

    rows = []
    for mask_name, mask in (("open", open_allowed),
                            ("lowband60", open_allowed & (det_elev <= 0.60))):
        for tag, feat, tru in (("A->B", mapA, tB), ("B->A", mapB, tA)):
            for sname, surf in surfaces(feat).items():
                for sep in (3.0, 4.0):
                    for budget in (20_000, 40_000):
                        t0 = time.time()
                        sel = D.greedy_pack(surf, mask, min_sep=sep, budget=budget,
                                            candidate_cap=3_000_000)
                        r = dti(sel.astype(F32), tru, footprint=foot, known=cat)
                        n = int(sel.sum())
                        prof = {k: float(layers[k][sel].mean() / base[k]) for k in layers}
                        proj = LAM * r["tp"] / (0.8 * K + 0.2 * n) if n else 0.0
                        rows.append(dict(mask=mask_name, tag=tag, surface=sname, min_sep=sep,
                                         budget=budget, emitted=n, T=round(r["tp"], 1),
                                         cpm=round(r["credit_per_mass"], 5),
                                         projected_hidden_dti=round(proj, 5),
                                         profile={k: round(v, 3) for k, v in prof.items()},
                                         seconds=round(time.time() - t0, 1)))
                        print(f"{mask_name:9s} {tag} {sname:16s} sep={sep} N={budget} -> N={n} "
                              f"T={r['tp']:.0f} proj={proj:.4f} det={prof['det_elev']:.2f} "
                              f"cat={prof['dist_cat']:.2f}", flush=True)
                        del sel

    # two-direction consistency + admissibility (declared here, before seeing the numbers)
    DET_MAX = 1.35 * ref_profile["det_elev"]     # 1.20
    CAT_MIN = ref_profile["dist_cat"] / 1.35     # 0.64
    idx = {(r["mask"], r["surface"], r["min_sep"], r["budget"], r["tag"]): r for r in rows}
    summary = []
    for (mask, sname, sep, budget, tag), r in idx.items():
        if tag != "A->B":
            continue
        m = idx.get((mask, sname, sep, budget, "B->A"))
        if m is None:
            continue
        lo, hi = sorted((r["projected_hidden_dti"], m["projected_hidden_dti"]))
        consistent = hi > 0 and (hi - lo) / hi <= 0.20
        admissible = bool(r["profile"]["det_elev"] <= DET_MAX
                          and r["profile"]["dist_cat"] >= CAT_MIN and consistent)
        summary.append(dict(mask=mask, surface=sname, min_sep=sep, budget=budget,
                            proj_AB=r["projected_hidden_dti"], proj_BA=m["projected_hidden_dti"],
                            min_pair=lo, det_elev=r["profile"]["det_elev"],
                            dist_cat=r["profile"]["dist_cat"],
                            two_direction_consistent=bool(consistent), admissible=admissible))
    summary.sort(key=lambda s: -s["min_pair"])
    out = dict(reference_profile=ref_profile, det_elev_max=DET_MAX, dist_cat_min=CAT_MIN,
               rows=rows, summary=summary,
               admissible_best=[s for s in summary if s["admissible"]][:5],
               verdict="admissible candidate exists" if any(s["admissible"] for s in summary)
                       else "NO admissible candidate in this probe")
    (ROOT / "evidence/h42_admissibility.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(dict(admissible_best=out["admissible_best"], verdict=out["verdict"]), indent=1))
    print("top 8 by min-pair projection:")
    for s in summary[:8]:
        print(" ", json.dumps(s))


if __name__ == "__main__":
    main()
