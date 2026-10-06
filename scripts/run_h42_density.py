#!/usr/bin/env python3
"""H42 density-ranked packing: build the evidence surface, sweep emission, project the score.

Pipeline (all pre-registered in research/hypotheses-v2.md before any number below was seen):

 1. EVIDENCE TERMS   eight independent, public, licence-checked layers -> [0,1] fields
                     (thermal density and thermal lineaments; catalogue structural
                     completion; LiDAR scarp evidence; geodetic strain; conductivity;
                     seismicity density; independent-map fault density).
 2. EMISSION         greedy maximum-score packing (src/gemsdoe41/density.py) at a minimum
                     separation comparable to the 300 m kernel, for a mass ladder.
 3. INSTRUMENTS      (a) SGMC off-catalogue *half* truth - the independent-map instrument
                         whose credit-per-mass ranks the 16 archived artifacts with
                         Spearman +0.83 against their reported scores;
                     (b) the same instrument on the mirrored half, as a symmetry check;
                     (c) the catalogue-strand holdout, reported only as a known
                         anti-informative control (see evidence/proxy_credit_calibration.json).
 4. PROJECTION       DTI_hidden(N) ~= lambda_half * T_half(N) / (0.8*K + 0.2*N), with
                     lambda_half measured from the archived artifacts on the same half truth.

Output: evidence/h42_density.json  (no submission is written here)
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import label as cc_label

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
TEMP_MIN = 20.0
ANOMALY_OFFCAT_PX = 3.0     # 300 m: the metric kernel radius / official novelty exclusion
LINE_HALF_LEN_PX = 15       # +/- 1.5 km of structure-aligned line through a thermal anomaly
LINE_STEP_PX = 2
POP_NW_AZ = 315.0
POP_NNE_AZ = 10.0

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
    a[a < -1e37] = 0.0
    a[~np.isfinite(a)] = 0.0
    return a


def spearman(x: np.ndarray, y: np.ndarray) -> float:
    rx = np.argsort(np.argsort(x)).astype(float); rx -= rx.mean()
    ry = np.argsort(np.argsort(y)).astype(float); ry -= ry.mean()
    den = float(np.sqrt((rx ** 2).sum() * (ry ** 2).sum()))
    return float((rx * ry).sum() / den) if den else 0.0


def build_terms(cat: np.ndarray, foot: np.ndarray, blocks_feature: np.ndarray,
                sgmc: np.ndarray, thermal: dict, lidar_products: dict,
                bands: dict, verbose: bool = True) -> D.EvidenceTerms:
    """Construct the eight evidence terms.  `blocks_feature` selects the SGMC feature half."""
    t0 = time.time()
    terms = D.EvidenceTerms()
    d_cat = __import__("scipy.ndimage", fromlist=["distance_transform_edt"]).distance_transform_edt(~cat).astype(F32)

    # ---- 1. thermal anomaly density (off-catalogue only) -----------------
    rows, cols, temps, kinds = thermal["row"], thermal["col"], thermal["temp"], thermal["kind"]
    keep = d_cat[rows, cols] > ANOMALY_OFFCAT_PX
    rows, cols, temps, kinds = rows[keep], cols[keep], temps[keep], kinds[keep]
    w = np.clip((temps - TEMP_MIN) / 60.0, 0.0, 1.0) * 0.8 + 0.2 + 0.1 * (kinds == "spring")
    grid = np.zeros(cat.shape, F32)
    np.add.at(grid, (rows, cols), w.astype(F32))
    terms.add("thermal_density", D.norm01(D.smooth(grid, 3.0), foot),
              f"{rows.size} off-catalogue thermal anomalies (>={TEMP_MIN} C, >={ANOMALY_OFFCAT_PX*100:.0f} m from catalogue)")

    # ---- 2. structure-aligned lineaments through those anomalies ---------
    line = np.zeros(cat.shape, bool)
    strike = lidar_products["strike"]
    valid = lidar_products["valid"]
    for r, c in zip(rows, cols):
        th = float(strike[r, c]) if valid[r, c] else None
        if th is None or not np.isfinite(th) or th <= 0:
            # fall back to the closer of the two mapped populations, chosen geometrically
            th = 135.0 if abs(((135.0 - float(POP_NNE_AZ)) + 90) % 180 - 90) < 45 else 135.0
            th = float(min([135.0, float(POP_NNE_AZ)],
                           key=lambda p: abs(((p - 0.0) + 90) % 180 - 90)))
        theta = np.deg2rad(th)
        dr, dc = -np.cos(theta), np.sin(theta)   # strike measured from +x (east), y south
        for s in range(-LINE_HALF_LEN_PX, LINE_HALF_LEN_PX + 1, LINE_STEP_PX):
            rr = int(round(r + dr * s)); cc = int(round(c + dc * s))
            if 0 <= rr < cat.shape[0] and 0 <= cc < cat.shape[1]:
                line[rr, cc] = True
    line &= ~cat
    terms.add("thermal_line", D.norm01(D.dilate_blur(line, 2.0), foot),
              f"structure-aligned dotted lines (+/-{LINE_HALF_LEN_PX*100} m) through the same anomalies; orientation from the LiDAR strike band, else the nearer population strike")

    # ---- 3. catalogue structural completion (transfer / tip-extension / relay) ----
    traces = C.extract_traces(cat)
    A, B, _ = C.population_masks(cat.shape, traces)
    elems = S.build_elements(traces, A, B)
    corridor = elems["transfer"] | elems["extension"] | elems["relay"]
    terms.add("structural", D.norm01(D.dilate_blur(corridor, 3.0), foot),
              f"H41 geometry on the mapped catalogue: {len(traces)} traces, {elems['counts']}")
    del A, B, elems, corridor

    # ---- 4. LiDAR scarp evidence -----------------------------------------
    ev = lidar_products["evidence"]
    terms.add("scarp", D.norm01(D.smooth(ev, 2.0), foot & valid),
              "3DEP-derived scarp evidence (step and crest/base breaks, coherence-weighted); USGS 3DEP, no use restrictions")

    # ---- 5-7. in-stack geophysical / geodetic / seismic percentiles ------
    terms.add("strain", D.norm01(D.smooth(bands["geod_2ndinv"] + bands["geod_shearrate"], 3.0), foot),
              "competition bands 4 + 7 (geodetic second invariant, shear rate), smoothed")
    terms.add("conductivity", D.norm01(D.smooth(bands["cond_surf"], 3.0), foot),
              "competition band 17 (conductivity surface), smoothed")
    terms.add("seismicity", D.norm01(D.smooth(bands["ieq"], 3.0), foot),
              "competition band 16 (earthquake density), smoothed")

    # ---- 8. independent-map density (feature half only) ------------------
    feat = sgmc & (d_cat > ANOMALY_OFFCAT_PX) & blocks_feature
    terms.add("independent_map", D.norm01(D.smooth(feat.astype(F32), 3.0), foot),
              "USGS SGMC-derived fault density, feature half only, faults >300 m from the catalogue")
    if verbose:
        print(f"  terms built in {time.time()-t0:.1f}s; independent-map feature px={int(feat.sum())}")
    return terms


def main() -> None:
    cat = read_band(ROOT / "data/existing_faults.tif", 1) > 0.5
    with rasterio.open(ROOT / "data/sample_submission.tif") as s:
        foot = np.isfinite(s.read(1))
    with rasterio.open(ROOT / "data/external/derived_sgmc_faults_100m_u8.tif") as s:
        sgmc = s.read(1) > 0
    rows, cols = np.mgrid[0:cat.shape[0], 0:cat.shape[1]]
    parity = ((rows // BLOCK_PX) + (cols // BLOCK_PX)) % 2 == 0

    from scipy.ndimage import distance_transform_edt
    d_cat = distance_transform_edt(~cat).astype(F32)
    truth_all = sgmc & (d_cat > ANOMALY_OFFCAT_PX) & foot
    truth_A = truth_all & parity
    truth_B = truth_all & ~parity
    print(f"SGMC off-catalogue truth: total={int(truth_all.sum())} halfA={int(truth_A.sum())} halfB={int(truth_B.sum())}")

    # ---- thermal anomalies (GDR 1391, CC BY 4.0) -------------------------
    import csv
    tr, tc, tt, tk = [], [], [], []
    with open(ROOT / "data/external/gdr_wellspring_in_footprint.csv") as fh:
        for rec in csv.DictReader(fh):
            try:
                temp = float(rec["temp_c"])
            except (TypeError, ValueError):
                continue
            cls = (rec.get("thermalclass") or "").strip()
            if temp < TEMP_MIN and cls not in ("Hot", "Warm"):
                continue
            r, c = int(rec["row"]), int(rec["col"])
            if not (0 <= r < cat.shape[0] and 0 <= c < cat.shape[1]):
                continue
            tr.append(r); tc.append(c); tt.append(temp)
            tk.append("spring" if "spring" in rec["layer"] else "well")
    thermal = dict(row=np.array(tr), col=np.array(tc), temp=np.array(tt, dtype=F32),
                   kind=np.array(tk))
    # de-duplicate identical cells, keeping the maximum temperature
    order = np.lexsort((-thermal["temp"], thermal["row"], thermal["col"]))
    r_, c_, t_, k_ = (thermal["row"][order], thermal["col"][order],
                      thermal["temp"][order], thermal["kind"][order])
    keep = np.ones(r_.size, bool)
    keep[1:] = (r_[1:] != r_[:-1]) | (c_[1:] != c_[:-1])
    thermal = dict(row=r_[keep], col=c_[keep], temp=t_[keep], kind=k_[keep])
    print(f"thermal anomalies used: {thermal['row'].size} unique cells (>= {TEMP_MIN} C or Hot/Warm)")

    lidar_products = L.load_products(str(ROOT / "data/external/lidar_scarp_features_u8.tif"))
    print("lidar valid px:", lidar_products["valid_px"])
    bands = dict(
        geod_2ndinv=read_band(ROOT / "data/training_features.tif", 4),
        geod_shearrate=read_band(ROOT / "data/training_features.tif", 7),
        ieq=read_band(ROOT / "data/training_features.tif", 16),
        cond_surf=read_band(ROOT / "data/training_features.tif", 17),
    )

    # ---- lambda calibration for the half-truth instrument ---------------
    calib = []
    for name, rel, score in ARCHIVED:
        p = ROOT / rel
        if not p.exists():
            continue
        pred = read_band(p, 1)
        with rasterio.open(p) as s:
            arr = s.read(1)
        arr[~np.isfinite(arr)] = 0.0
        pred = np.clip(arr, 0.0, 1.0).astype(F32)
        n_emitted = int((pred > 0).sum())
        rb = dti(pred, truth_B, footprint=foot, known=cat)
        ra = dti(pred, truth_A, footprint=foot, known=cat)
        T_hidden = score * (0.8 * K_CALIBRATED + 0.2 * n_emitted)
        calib.append(dict(name=name, reported_score=score, emitted_px=n_emitted,
                          T_hidden=round(T_hidden, 1),
                          T_halfA=round(ra["tp"], 1), T_halfB=round(rb["tp"], 1),
                          cpm_halfB=round(rb["credit_per_mass"], 5),
                          lambda_halfB=round(T_hidden / rb["tp"], 3) if rb["tp"] > 0 else None,
                          lambda_halfA=round(T_hidden / ra["tp"], 3) if ra["tp"] > 0 else None))
        del pred, arr
    lam = np.array([c["lambda_halfB"] for c in calib if c["lambda_halfB"]])
    lam_trim = np.array([v for v in lam if v < np.percentile(lam, 90)])
    scores = np.array([c["reported_score"] for c in calib if c["lambda_halfB"]])
    print(f"lambda_halfB: n={lam.size} median={np.median(lam):.2f} "
          f"trimmed-mean={lam_trim.mean():.2f} spread=[{lam.min():.2f},{lam.max():.2f}]")
    print(f"spearman(cpm_halfB, reported score) = "
          f"{spearman(np.array([c['cpm_halfB'] for c in calib if c['lambda_halfB']]), scores):.3f}")

    # ---- build the evidence surface for both halves ----------------------
    results = []
    for feat_half, truth_half, tag in ((parity, truth_B, "A->B"), (~parity, truth_A, "B->A")):
        print(f"[{tag}] building terms with feature half {'A' if tag=='A->B' else 'B'}")
        terms = build_terms(cat, foot, feat_half, sgmc, thermal, lidar_products, bands)
        allowed = foot & ~cat
        for wname, weights in D.WEIGHTINGS.items():
            surface = D.geometric_mean(terms.terms, weights)
            for sep in D.MIN_SEP_GRID:
                for budget in D.MASS_GRID:
                    sel = D.greedy_pack(surface, allowed, min_sep=sep, budget=budget)
                    r = dti(sel.astype(F32), truth_half, footprint=foot, known=cat)
                    n = int(sel.sum())
                    lam_use = float(np.median(lam))
                    proj = lam_use * r["tp"] / (0.8 * K_CALIBRATED + 0.2 * n) if n else 0.0
                    results.append(dict(tag=tag, weighting=wname, min_sep=sep, budget=budget,
                                        emitted=int(n), T_half=round(r["tp"], 1),
                                        cpm=round(r["credit_per_mass"], 5),
                                        projected_hidden_dti=round(proj, 5)))
                    del sel
            # controls at one separation/mass: uniform random, and catalogue-distance
        # controls (declared, matched mass)
        rng = np.random.default_rng(41)
        for sep in (4.0,):
            for budget in (10_000, 40_000):
                rnd = np.zeros(cat.shape, F32)
                cand = np.flatnonzero(allowed.ravel())
                pick = rng.choice(cand, size=min(budget * 3, cand.size), replace=False)
                flat = rnd.ravel(); flat[pick] = 1.0
                sel = D.greedy_pack(rnd, allowed, min_sep=sep, budget=budget)
                r = dti(sel.astype(F32), truth_half, footprint=foot, known=cat)
                results.append(dict(tag=tag, weighting="CONTROL_uniform_random", min_sep=sep,
                                    budget=budget, emitted=int(sel.sum()),
                                    T_half=round(r["tp"], 1),
                                    cpm=round(r["credit_per_mass"], 5),
                                    projected_hidden_dti=None))
                del rnd, sel
                near = np.zeros(cat.shape, F32)
                flat = near.ravel(); flat[np.flatnonzero(allowed.ravel())] = 1.0
                near = np.exp(-d_cat / F32(3.0)) * (allowed)
                sel = D.greedy_pack(near, allowed, min_sep=sep, budget=budget)
                r = dti(sel.astype(F32), truth_half, footprint=foot, known=cat)
                results.append(dict(tag=tag, weighting="CONTROL_near_catalogue", min_sep=sep,
                                    budget=budget, emitted=int(sel.sum()),
                                    T_half=round(r["tp"], 1),
                                    cpm=round(r["credit_per_mass"], 5),
                                    projected_hidden_dti=None))
                del near, sel
        del terms

    out = dict(
        hypothesis="H42 density-ranked packing of a multi-evidence surface",
        protocol=dict(temp_min_c=TEMP_MIN, anomaly_offcat_px=ANOMALY_OFFCAT_PX,
                      line_half_len_px=LINE_HALF_LEN_PX, line_step_px=LINE_STEP_PX,
                      block_px=BLOCK_PX, K_calibrated=K_CALIBRATED,
                      min_sep_grid=list(D.MIN_SEP_GRID), mass_grid=list(D.MASS_GRID),
                      weightings={k: v for k, v in D.WEIGHTINGS.items()}),
        instrument=dict(
            truth="USGS SGMC-derived fault pixels >=300 m from the catalogue, split by 20 km block parity",
            truth_all_px=int(truth_all.sum()), truth_A_px=int(truth_A.sum()),
            truth_B_px=int(truth_B.sum()),
            masking="catalogue pixels excluded from the scored domain",
            symmetry="A->B and B->A computed; the submitted file uses both halves as features and is therefore reported from these two disjoint evaluations, not from a single full-truth number",
        ),
        lambda_calibration=dict(per_file=calib, median_halfB=float(np.median(lam)),
                                trimmed_mean_halfB=float(lam_trim.mean()),
                                spearman_cpm_vs_reported=round(float(spearman(
                                    np.array([c["cpm_halfB"] for c in calib if c["lambda_halfB"]]),
                                    scores)), 3),
                                method="T_hidden = reported_score*(0.8*K + 0.2*N_emitted); lambda = T_hidden / T_half"),
        results=results,
        controls_note="uniform-random and near-catalogue packings at matched mass are the declared negative/naive controls",
    )
    (ROOT / "evidence/h42_density.json").write_text(json.dumps(out, indent=1) + "\n")
    print("wrote evidence/h42_density.json")
    # compact console table
    print(f"\n{'tag':5s} {'weighting':18s} {'sep':>4s} {'budget':>7s} {'N':>7s} {'T_half':>8s} {'cpm':>7s} {'projDTI':>8s}")
    for r in results:
        print(f"{r['tag']:5s} {r['weighting']:18s} {r['min_sep']:4.1f} {r['budget']:7d} {r['emitted']:7d} "
              f"{r['T_half']:8.0f} {r['cpm']:7.4f} {str(r['projected_hidden_dti']):>8s}")


if __name__ == "__main__":
    main()
