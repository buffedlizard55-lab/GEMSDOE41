#!/usr/bin/env python3
"""Declared design sweep: which pre-registered surface beats the archived benchmark?

Benchmark on the independent-map (SGMC off-catalogue) half instrument, measured with the
same protocol for every artifact: H33-2-B2 credit-per-mass = 0.147 (full truth) and the
16-file ladder in evidence/h42_density.json.  Any candidate surface must beat that on the
SAME instrument before it is worth a submission slot; this script measures a small,
pre-declared family of surfaces and reports all of them, in both half directions, so the
instrument's own noise floor is visible.

Surfaces (declared before running; deliberately few, each physically motivated):
  S1 slope            : det_elev_slope only (the measured strongest single predictor, lift 1.93)
  S2 slope_scarp      : geometric mean of det_elev_slope and LiDAR scarp evidence
  S3 slope_scarp_map  : S2 plus independent-map density from the OTHER half only
  S4 dense_multi      : geometric mean of the eight dense terms (no independent map)
  S5 thermal_stub     : the H42 thermal-anchor surface alone (hypothesis C1 in isolation)
  S6 catalogue_free   : S3 normalised by the catalogue density (explicitly avoids catalogue echo)

Emission is the greedy packing from src/gemsdoe41/density.py at the declared separations.

Output: evidence/h42_surface_sweep.json
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

from gems41 import catalogue as C  # noqa: E402
from gems41 import lidar as L  # noqa: E402
from gems41 import structure as S  # noqa: E402
from gems41.metric import dti  # noqa: E402
from gemsdoe41 import density as D  # noqa: E402

F32 = np.float32
BLOCK_PX = 200
K_CALIBRATED = 14_088
LAMBDA_HALF = 1.76   # median T_hidden / T_half over the 16-file ledger (evidence/h42_density.json)


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
    truth_A, truth_B = truth & parity, truth & ~parity
    allowed = foot & ~cat

    # ---- dense evidence terms -------------------------------------------------
    slope = read_band(ROOT / "data/training_features.tif", 19)
    det_elev = read_band(ROOT / "data/training_features.tif", 12)
    tmi_hg = read_band(ROOT / "data/training_features.tif", 3)
    cond = read_band(ROOT / "data/training_features.tif", 17)
    shearrate = read_band(ROOT / "data/training_features.tif", 7)
    secondinv = read_band(ROOT / "data/training_features.tif", 4)
    ieq = read_band(ROOT / "data/training_features.tif", 16)
    depth = read_band(ROOT / "data/training_features.tif", 15)
    prod = L.load_products(str(ROOT / "data/external/lidar_scarp_features_u8.tif"))
    scarp = prod["evidence"]
    valid = prod["valid"]

    T = dict(
        slope=D.norm01(D.smooth(slope, 1.0), foot),
        scarp=D.norm01(D.smooth(scarp, 1.0), foot & valid),
        tmi_hg=D.norm01(D.smooth(tmi_hg, 1.0), foot),
        cond=D.norm01(D.smooth(cond, 1.0), foot),
        shearrate=D.norm01(D.smooth(shearrate, 1.0), foot),
        secondinv=D.norm01(D.smooth(secondinv, 1.0), foot),
        ieq=D.norm01(D.smooth(ieq, 1.0), foot),
        depth=D.norm01(D.smooth(-depth, 1.0), foot),      # shallower basement = higher
        det_elev=D.norm01(D.smooth(det_elev, 1.0), foot),
    )
    # structural completion (catalogue-derived, H41 geometry)
    traces = C.extract_traces(cat)
    A, B, _ = C.population_masks(cat.shape, traces)
    elems = S.build_elements(traces, A, B)
    corridor = elems["transfer"] | elems["extension"] | elems["relay"]
    T["structural"] = D.norm01(D.dilate_blur(corridor, 3.0), foot)
    del A, B, elems, corridor, traces
    # thermal anchors + structure-aligned lines through them
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
            if 0 <= r < cat.shape[0] and 0 <= c < cat.shape[1] and d_cat[r, c] > 3.0:
                tr.append(r); tc.append(c); tt.append(temp)
    tr, tc, tt = np.array(tr), np.array(tc), np.array(tt, dtype=F32)
    g = np.zeros(cat.shape, F32); np.add.at(g, (tr, tc), np.clip((tt - 20) / 60, 0, 1))
    T["thermal_density"] = D.norm01(D.smooth(g, 3.0), foot)
    line = np.zeros(cat.shape, bool)
    strike_l = prod["strike"]; valid_l = prod["valid"]
    for r, c in zip(tr, tc):
        th = float(strike_l[r, c]) if valid_l[r, c] else 10.0
        theta = np.deg2rad(th)
        dr, dc = -np.cos(theta), np.sin(theta)
        for s in range(-15, 16, 2):
            rr, cc = int(round(r + dr * s)), int(round(c + dc * s))
            if 0 <= rr < cat.shape[0] and 0 <= cc < cat.shape[1]:
                line[rr, cc] = True
    line &= ~cat
    T["thermal_line"] = D.norm01(D.dilate_blur(line, 2.0), foot)

    mapA = D.norm01(D.smooth((sgmc & parity & (d_cat > 3)).astype(F32), 3.0), foot)
    mapB = D.norm01(D.smooth((sgmc & ~parity & (d_cat > 3)).astype(F32), 3.0), foot)
    cat_dens = D.norm01(D.smooth(cat.astype(F32), 5.0), foot)

    # ---- surfaces -------------------------------------------------------------
    def gm(*names, weights=None):
        w = {n: (weights[i] if weights else 1.0) for i, n in enumerate(names)}
        return D.geometric_mean({n: T[n] for n in names}, w)

    def surfaces(feature_map: np.ndarray) -> dict[str, np.ndarray]:
        s = {}
        s["S1_slope"] = gm("slope")
        s["S2_slope_scarp"] = gm("slope", "scarp", weights=[0.6, 0.4])
        s["S3_slope_scarp_map"] = D.geometric_mean(
            dict(S2_slope_scarp=s["S2_slope_scarp"], independent_map=feature_map),
            {"S2_slope_scarp": 0.5, "independent_map": 0.5})
        s["S4_dense_multi"] = gm("slope", "scarp", "tmi_hg", "cond", "shearrate",
                                 "secondinv", "ieq", "depth", "structural")
        s["S5_thermal_structural"] = gm("thermal_line", "structural")
        s["S6_map_scarp_slope_catfree"] = D.geometric_mean(
            dict(S3=s["S3_slope_scarp_map"], not_catalogue=1.0 - np.clip(cat_dens * 4.0, 0, 1)),
            {"S3": 0.75, "not_catalogue": 0.25})
        return s

    results = []
    for tag, feat, tru in (("A->B", mapA, truth_B), ("B->A", mapB, truth_A)):
        for name, surf in surfaces(feat).items():
            for sep in (2.0, 3.0, 4.0):
                for budget in (10_000, 20_000, 40_000, 60_000):
                    sel = D.greedy_pack(surf, allowed, min_sep=sep, budget=budget)
                    r = dti(sel.astype(F32), tru, footprint=foot, known=cat)
                    n = int(sel.sum())
                    proj = LAMBDA_HALF * r["tp"] / (0.8 * K_CALIBRATED + 0.2 * n) if n else 0.0
                    results.append(dict(tag=tag, surface=name, min_sep=sep, budget=budget,
                                        emitted=n, T=round(r["tp"], 1),
                                        cpm=round(r["credit_per_mass"], 5),
                                        projected_hidden_dti=round(proj, 5)))
                    del sel

    # controls
    rng = np.random.default_rng(11)
    for tag, tru in (("A->B", truth_B), ("B->A", truth_A)):
        for sep in (3.0,):
            for budget in (20_000, 40_000):
                flatfield = np.zeros(cat.shape, F32)
                cand = np.flatnonzero(allowed.ravel())
                flatfield.ravel()[rng.choice(cand, size=min(budget * 3, cand.size), replace=False)] = 1.0
                sel = D.greedy_pack(flatfield, allowed, min_sep=sep, budget=budget)
                r = dti(sel.astype(F32), tru, footprint=foot, known=cat)
                results.append(dict(tag=tag, surface="CONTROL_uniform_random", min_sep=sep,
                                    budget=budget, emitted=int(sel.sum()), T=round(r["tp"], 1),
                                    cpm=round(r["credit_per_mass"], 5), projected_hidden_dti=None))
                del flatfield, sel

    rows_by = {}
    for r in results:
        rows_by.setdefault(r["surface"], []).append(r)
    out = dict(
        benchmark=dict(
            archived_best_cpm=0.14653, archived_best="H33-2-B2 (reported 0.2778)",
            archived_best_projected_dti=0.2778,
            note="credit-per-mass on the SGMC off-catalogue instrument; the same protocol used for every surface below",
        ),
        lambda_half_used=LAMBDA_HALF,
        truth_A_px=int(truth_A.sum()), truth_B_px=int(truth_B.sum()),
        results=results,
        best_per_surface={
            k: max(v, key=lambda r: (r["cpm"] or 0)) for k, v in rows_by.items()
        },
        caveats=[
            "The SGMC instrument's truth is a state-map compilation, largely traced from topography, so surfaces dominated by terrain slope are partly self-fulfilling on it.",
            "Reported scores are owner/user reports, not organizer receipts.",
            "Design selection here is instrument-driven; evidence/h42_density.json records the alternative weightings.",
        ],
    )
    (ROOT / "evidence/h42_surface_sweep.json").write_text(json.dumps(out, indent=1) + "\n")
    print(f"{'surface':32s} {'tag':5s} {'sep':>4s} {'N':>7s} {'T':>8s} {'cpm':>8s} {'proj':>7s}")
    for name, best in sorted(out["best_per_surface"].items(),
                             key=lambda kv: -(kv[1]["cpm"] or 0)):
        print(f"{name:32s} {best['tag']:5s} {best['min_sep']:4.1f} {best['emitted']:7d} "
              f"{best['T']:8.0f} {best['cpm']:8.5f} {str(best['projected_hidden_dti']):>7s}")
    print("\nbenchmark to beat: cpm 0.14653")


if __name__ == "__main__":
    main()
