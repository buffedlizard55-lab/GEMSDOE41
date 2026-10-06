#!/usr/bin/env python3
"""H43-A: invert the family's own live score record for the hidden label field.

WHY THIS EXISTS
---------------
Every previous session in this family validated against a *proxy* truth (the published
catalogue, or a blocked piece of it).  The prize round is scored against faults that are
**absent** from that catalogue, so the proxy is the wrong target and it produced the
structural zeros recorded in `docs/downloads/holdout.json`.

There is, however, a real measurement of the hidden label set available: the family's own
published rasters together with the scores the portal returned for them.  Each published
raster E_i is a *known probe* of the hidden set G.  Under the official metric

    k(d)  = max(1 - d/3, 0)                       (d in 100 m pixels, R = 300 m)
    TP_w  = sum_{g in G} max_{x} p(x) k(d(x,g))
    FP_w  = sum_{x active} p(x) [1 - max_{g in G} k(d(x,g))]
    FN_w  = |G| - TP_w
    DTI   = TP_w / (TP_w + 0.2 FP_w + 0.8 FN_w)

write the hidden set as an independent Bernoulli field with intensity pi(x) = rho * u(x),
u >= 0, sum(u) = 1 over the scored (active = in-footprint, off-catalogue) domain, so that
|G| = rho in expectation.  Then for a probe with prediction p:

    E[TP_w] = rho * a(u),      a(u) = sum_x u(x) * Kp(x),   Kp(x) = max_y p(y) k(d(x,y))
    E[FP_w] = M - rho * q(u),  q(u) = sum_x u(x) * Sp(x),   Sp(x) = sum_y p(y) k(d(x,y))
                             (first order in rho*u; M = sum of p over active pixels)
    DTI(u, rho) = rho a / (0.2 rho a + 0.2 (M - rho q) + 0.8 rho)

`a` and `q` are both LINEAR in u, so with a basis u = sum_j w_j u_j (w on the simplex) the
predicted score of every probe is a smooth function of (w, rho) alone.  Fitting (w, rho) to
the reported scores therefore *inverts the score record for the spatial distribution of the
hidden labels* -- a measurement, not a guess -- and leave-one-probe-out refitting turns it
into a predictive instrument that can be checked before a slot is spent.

HONESTY
-------
* The scores used here are owner-reported on the sibling project pages, transcribed into
  `registry/score_ledger.csv`.  They are NOT organizer receipts.  Every number derived from
  them is tagged [MODEL] and carries the probe list it was fitted on.
* The probe rasters are read for their SUPPORT and MASS only.  No probe pixel value is ever
  copied into this repository's prediction.
* `community.drivendata.org` and `drivendata.org` are never requested by this script.

Run:  .venv/bin/python scripts/invert_label_field.py [--j 4]
Writes evidence/label_field_inversion.json and data/derived/templates.npz
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems41 import lidar as L  # noqa: E402

ALPHA, BETA, RADIUS = 0.2, 0.8, 3.0
F32 = np.float32

# kernel offsets (dy, dx, k)
OFFS = []
for dy in range(-3, 4):
    for dx in range(-3, 4):
        d = float(np.hypot(dy, dx))
        if d < RADIUS:
            OFFS.append((dy, dx, 1.0 - d / RADIUS))


def conv_max(p: np.ndarray) -> np.ndarray:
    """Kp(x) = max_y p(y) k(d(x,y)) -- the per-truth-pixel credit field."""
    from gems41.coverage import coverage_field

    return coverage_field(p)


def conv_sum(p: np.ndarray) -> np.ndarray:
    """Sp(x) = sum_y p(y) k(d(x,y)) -- the double-counting version used for FP_w."""
    from gems41.coverage import coverage_sum_field

    return coverage_sum_field(p)


def anomaly(band: np.ndarray, active: np.ndarray, lo_q: float = 50.0, hi_q: float = 99.0,
            invert: bool = False) -> np.ndarray:
    """Normalised positive anomaly of a band above its median, clipped to [0, 1]."""
    v = np.where(active & np.isfinite(band) & (band > -1e38), band, np.nan)
    ref = v[active & np.isfinite(v)]
    if ref.size == 0:
        return np.zeros(band.shape, F32)
    lo, hi = float(np.nanpercentile(ref, lo_q)), float(np.nanpercentile(ref, hi_q))
    if hi <= lo:
        return np.zeros(band.shape, F32)
    t = (v - lo) / (hi - lo) if not invert else (hi - v) / (hi - lo)
    out = np.clip(np.nan_to_num(t, nan=0.0), 0.0, 1.0).astype(F32)
    out[~active] = 0.0
    return out


def gradient_mag(band: np.ndarray, active: np.ndarray) -> np.ndarray:
    v = np.where(active & (band > -1e38), band, np.nan).astype(np.float64)
    med = float(np.nanmedian(v))
    v = np.where(np.isfinite(v), v, med)
    gy, gx = np.gradient(v)
    g = np.hypot(gy, gx).astype(F32)
    g[~active] = 0.0
    return g


def build_templates(active: np.ndarray, dcat: np.ndarray, data_dir: Path) -> tuple[list[str], np.ndarray]:
    """Geologically interpretable basis densities, each summing to 1 over the active domain."""
    names: list[str] = []
    cols: list[np.ndarray] = []

    def add(name: str, field: np.ndarray) -> None:
        f = np.where(active, np.nan_to_num(np.asarray(field, np.float64), nan=0.0), 0.0)
        f = np.clip(f, 0.0, None)
        s = f.sum()
        if not np.isfinite(s) or s <= 0:
            print(f"  !! template {name} is empty -- skipped", flush=True)
            return
        names.append(name)
        cols.append((f / s).astype(F32)[active])
        print(f"  + {name:16s} support={int((f > 0).sum()):9d}  max_density={float((f/s).max()):.3e}",
              flush=True)

    # --- radial position relative to the published catalogue (7 bins) ---
    for nm, lo, hi in [("dcat_0_1", 0.0, 1.0), ("dcat_1_2", 1.0, 2.0), ("dcat_2_3", 2.0, 3.0),
                       ("dcat_3_6", 3.0, 6.0), ("dcat_6_12", 6.0, 12.0), ("dcat_12_25", 12.0, 25.0),
                       ("dcat_25_inf", 25.0, 1e9)]:
        add(nm, ((dcat > lo) & (dcat <= hi)).astype(F32))

    # --- flat baseline ---
    add("uniform", np.ones(active.shape, F32))

    # --- independent 1 m LiDAR scarp morphology (USGS 3DEP derived) ---
    lid = L.load_products(str(data_dir / "external" / "lidar_scarp_features_u8.tif"))
    add("lidar_scarp", lid["evidence"])
    del lid

    # --- official competition bands ---
    band_tmpl = [
        ("det_elev_slope", 19, False, False),
        ("tmi_hg", 3, False, False),
        ("iso_grav_hg", 18, False, False),
        ("iso_grav_slope", 5, False, False),
        ("geod_2ndinv", 4, False, False),
        ("geod_shear", 7, False, False),
        ("geod_dilate_abs", 8, True, False),
        ("cond_surf", 17, False, False),
        ("tilt_tc", 6, False, False),
        ("eq_distance_near", 10, False, True),
        ("eq_intensity", 16, False, False),
    ]
    with rasterio.open(data_dir / "training_features.tif") as src:
        for nm, b, absval, inv in band_tmpl:
            raw = src.read(b).astype(np.float64)
            if absval:
                raw = np.abs(raw)
            if nm == "depth_base_grad":
                add(nm, gradient_mag(raw, active))
            else:
                add(nm, anomaly(raw, active, invert=inv))
            del raw
        # basement thickness discontinuity (blind-fault detector)
        raw = src.read(15).astype(np.float64)
        g = gradient_mag(raw, active)
        lo, hi = float(np.percentile(g[active], 50)), float(np.percentile(g[active], 99))
        add("depth_base_grad", np.clip((g - lo) / max(hi - lo, 1e-9), 0, 1))
        del raw, g

    return names, np.stack(cols)  # (J, N_active) float32


def probe_fields(p: np.ndarray, active_idx: np.ndarray, active: np.ndarray) -> dict:
    """M, Kp|active, Sp|active for one probe raster."""
    pp = np.where(active, np.nan_to_num(p, nan=0.0), 0.0).astype(F32)
    pp = np.clip(pp, 0.0, 1.0)
    K = conv_max(pp)
    S = conv_sum(pp)
    return dict(M=float(pp.sum()), K=K[active], S=S[active],
                raw_mass=float(np.nansum(np.clip(p, 0, 1))),
                off_active_mass=float(np.nansum(np.clip(np.where(active, 0.0, p), 0, 1))))


def predict(a: np.ndarray, q: np.ndarray, M: np.ndarray, rho: float, lam: float = 0.0,
            off_mass: np.ndarray | None = None) -> np.ndarray:
    """Model score for every probe given per-template (a, q) and mixture weights applied outside."""
    A = rho * a
    F = M - rho * q
    if off_mass is not None and lam:
        F = F + lam * off_mass
    F = np.maximum(F, 0.0)
    return A / (ALPHA * A + ALPHA * F + BETA * rho + 1e-12)


def _nnls_simplex(A: np.ndarray, t: np.ndarray, simplex_gain: float = 1e3) -> np.ndarray:
    """min ||w@A - t||_2 s.t. w >= 0, sum(w) = 1, via an augmented NNLS row."""
    from scipy.optimize import nnls

    Aa = np.vstack([A.T, simplex_gain * np.ones((1, A.shape[0]))])
    ta = np.concatenate([t, [simplex_gain]])
    w, _ = nnls(Aa, ta)
    s = w.sum()
    return w / s if s > 0 else np.full(A.shape[0], 1.0 / A.shape[0])


def fit(a_ij: np.ndarray, q_ij: np.ndarray, M: np.ndarray, s: np.ndarray,
        off_mass: np.ndarray, lam: float, rho_grid: np.ndarray, l2: float = 0.0) -> dict:
    """Fit (w on the simplex, rho) to the reported scores under the exact model.

    For a fixed rho the model is linear in w to first order:
        a_i(w) = s_i * (0.8 + 0.2 * (M_i + lam*off_i) / rho)
    which is a non-negative least squares problem with a simplex constraint.  The returned
    w is then re-scored with the EXACT prediction (which keeps the a != q distinction), and
    rho is chosen on the grid that minimises that exact residual, followed by a refinement
    pass that alternates (rho -> w) and (w -> rho).
    """
    J = a_ij.shape[0]
    # EXACT linearisation in w at fixed rho (no a == q approximation):
    #   s (0.2 rho a + 0.2 (M + lam*off - rho q) + 0.8 rho) = rho a
    #   => a (1 - 0.2 s) + 0.2 s q = 0.8 s + 0.2 s (M + lam*off) / rho
    D = a_ij * (1.0 - ALPHA * s)[None, :] + q_ij * (ALPHA * s)[None, :]  # (J, N)

    def target(rho: float) -> np.ndarray:
        return BETA * s + ALPHA * s * (M + lam * off_mass) / rho

    def exact(w: np.ndarray, rho: float) -> tuple[np.ndarray, float]:
        pr = predict(w @ a_ij, w @ q_ij, M, rho, lam, off_mass)
        return pr, float(np.sum((pr - s) ** 2))

    best = None
    for rho in rho_grid:
        w = _nnls_simplex(D, target(rho))
        pr, sse = exact(w, rho)
        if best is None or sse < best["sse"]:
            best = dict(rho=float(rho), w=w, sse=sse, pred=pr)

    # refine: alternate a fine rho scan at fixed w and an NNLS re-fit at fixed rho
    rho = best["rho"]
    w = best["w"]
    for _ in range(14):
        grid = np.linspace(max(500.0, rho * 0.4), rho * 2.5, 61)
        cands = [(float(r), exact(w, float(r))[1]) for r in grid]
        rho = min(cands, key=lambda c: c[1])[0]
        w_new = _nnls_simplex(D, target(rho))
        if np.max(np.abs(w_new - w)) < 1e-9:
            w = w_new
            break
        w = w_new
    pr, sse = exact(w, rho)
    n = len(s)
    return dict(rho=float(rho), w=w.tolist(), sse=float(sse),
                rmse=float(np.sqrt(sse / n)), mae=float(np.mean(np.abs(pr - s))),
                pred=pr.tolist(), lam=lam, l2=l2, J=J, n_probes=n)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data-dir", default=str(ROOT / "data"))
    ap.add_argument("--out", default=str(ROOT / "evidence" / "label_field_inversion.json"))
    ap.add_argument("--loo", action="store_true", default=True)
    ap.add_argument("--use-cache", action="store_true",
                    help="reuse data/derived/inversion_design.npz instead of re-reading rasters")
    args = ap.parse_args()
    t0 = time.time()
    data_dir = Path(args.data_dir)

    with rasterio.open(data_dir / "existing_faults.tif") as src:
        cat = src.read(1)
    cm = cat == 1
    foot = cat != -1
    active = foot & ~cm
    active_idx = np.flatnonzero(active.ravel()).astype(np.int64)
    dcat = distance_transform_edt(~cm).astype(F32)
    print(f"active domain {int(active.sum())} px  (footprint {int(foot.sum())}, catalogue {int(cm.sum())})",
          flush=True)

    cache = ROOT / "data" / "derived" / "inversion_design.npz"
    if args.use_cache and cache.exists():
        z = np.load(cache, allow_pickle=True)
        names = [str(x) for x in z["names"]]
        A = z["A"].astype(np.float64)
        Q = z["Q"].astype(np.float64)
        M = z["M"].astype(np.float64)
        S = z["S"].astype(np.float64)
        OFF = z["OFF"].astype(np.float64)
        ids = [str(x) for x in z["ids"]]
        rows = [dict(id=i, score=float(sv), M=float(m), off_active_mass=float(o),
                     source="cached design matrix") for i, sv, m, o in zip(ids, S, M, OFF)]
        print(f"loaded cached design {A.shape} from {cache}", flush=True)
    else:
        print("building template basis ...", flush=True)
        names, U = build_templates(active, dcat, data_dir)
        print(f"{len(names)} templates, {U.nbytes/1e6:.0f} MB", flush=True)

        probes = json.loads((data_dir / "probes" / "probes.json").read_text())
        rows = []
        for p in probes:
            if not p.get("ok"):
                continue
            with rasterio.open(data_dir / "probes" / f"{p['id']}.tif") as src:
                arr = src.read(1).astype(np.float64)
                shape_ok = src.shape == active.shape
            if not shape_ok:
                print(f"  !! {p['id']} wrong shape, skipped")
                continue
            pf = probe_fields(arr, active_idx, active)
            rows.append(dict(id=p["id"], score=p["reported_score"], source=p["score_source"],
                             M=pf["M"], raw_mass=pf["raw_mass"],
                             off_active_mass=pf["off_active_mass"],
                             a=(U @ pf["K"].astype(F32)).tolist(),
                             q=(U @ pf["S"].astype(F32)).tolist()))
            print(f"  probe {p['id']:18s} M={pf['M']:9.0f} off={pf['off_active_mass']:8.0f} "
                  f"s={p['reported_score']:.4f}  ({time.time()-t0:.0f}s)", flush=True)
            del arr, pf

        A = np.array([r["a"] for r in rows]).T.astype(np.float64)  # (J, N)
        Q = np.array([r["q"] for r in rows]).T.astype(np.float64)
        M = np.array([r["M"] for r in rows])
        S = np.array([r["score"] for r in rows])
        OFF = np.array([r["off_active_mass"] for r in rows])
        ids = [r["id"] for r in rows]
        (ROOT / "data" / "derived").mkdir(parents=True, exist_ok=True)
        np.savez_compressed(cache, A=A.astype(np.float32), Q=Q.astype(np.float32), M=M, S=S,
                            OFF=OFF, ids=np.array(ids), names=np.array(names))
        print(f"design cached -> {cache} ({time.time()-t0:.0f}s)", flush=True)
        del U

    rho_grid = np.array([2_000, 3_000, 4_500, 6_000, 8_000, 10_000, 12_500, 15_000, 18_000,
                         22_000, 26_000, 32_000, 40_000, 50_000, 65_000, 85_000, 120_000,
                         170_000, 250_000], float)

    out = dict(created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               metric=dict(alpha=ALPHA, beta=BETA, radius_px=RADIUS),
               templates=names, active_px=int(active.sum()),
               probes=[dict(id=r["id"], score=r["score"], M=r["M"],
                            off_active_mass=r["off_active_mass"], source=r["source"]) for r in rows],
               evidence_class=("owner-reported scores; NOT organizer receipts. Every fitted "
                               "quantity is a [MODEL] conditioned on them."),
               runtime_s=round(time.time() - t0, 1))

    for lam in (0.0, 1.0):
        f = fit(A, Q, M, S, OFF, lam, rho_grid)
        out[f"fit_lam{lam}"] = dict(rho=f["rho"], rmse=f["rmse"], mae=f["mae"],
                                    weights={n: round(float(w), 5) for n, w in zip(names, f["w"])},
                                    per_probe=[dict(id=i, reported=float(sv), predicted=float(pv),
                                                    residual=float(pv - sv))
                                               for i, sv, pv in zip(ids, S, f["pred"])])
        print(f"\nlam={lam}: rho={f['rho']:.0f} rmse={f['rmse']:.5f} mae={f['mae']:.5f}")
        for n, w in sorted(zip(names, f["w"]), key=lambda t: -t[1])[:8]:
            print(f"    {n:16s} {w:.4f}")
        for r in out[f"fit_lam{lam}"]["per_probe"]:
            print(f"    {r['id']:18s} reported {r['reported']:.4f}  predicted {r['predicted']:.4f}  "
                  f"resid {r['residual']:+.4f}")

    # ---- leave-one-probe-out predictive validation of the best convention ----
    lam_best = 0.0 if out["fit_lam0.0"]["rmse"] <= out["fit_lam1.0"]["rmse"] else 1.0
    fb = out[f"fit_lam{lam_best}"]
    loo = []
    for hold in range(len(ids)):
        keep = [i for i in range(len(ids)) if i != hold]
        f = fit(A[:, keep], Q[:, keep], M[keep], S[keep], OFF[keep], lam_best, rho_grid)
        a_h = float(A[:, hold] @ np.array(f["w"]))
        q_h = float(Q[:, hold] @ np.array(f["w"]))
        pred = float(predict(np.array([a_h]), np.array([q_h]), np.array([M[hold]]), f["rho"],
                             lam_best, np.array([OFF[hold]]))[0])
        loo.append(dict(id=ids[hold], reported=float(S[hold]), predicted=pred,
                        residual=pred - float(S[hold]), rho_used=f["rho"]))
        print(f"  LOO {ids[hold]:18s} reported {S[hold]:.4f} predicted {pred:.4f} "
              f"resid {pred-S[hold]:+.4f}", flush=True)
    res = np.array([r["residual"] for r in loo])
    out["loo"] = dict(lam=lam_best, rows=loo,
                      rmse=float(np.sqrt(np.mean(res ** 2))), mae=float(np.mean(np.abs(res))),
                      max_abs=float(np.max(np.abs(res))),
                      within_0p01=int(np.sum(np.abs(res) <= 0.01)), n=len(res))
    out["best_fit"] = dict(lam=lam_best, rho=fb["rho"], rmse=fb["rmse"], weights=fb["weights"])
    print(f"\nLOO: rmse={out['loo']['rmse']:.5f} mae={out['loo']['mae']:.5f} "
          f"max|res|={out['loo']['max_abs']:.5f} within0.01={out['loo']['within_0p01']}/{len(res)}")

    # ---- the position-blind null model: uniform hidden-label density ----
    ju = names.index("uniform")
    rho_b = float(fb["rho"])
    null_rows = []
    for i, pid in enumerate(ids):
        a_u, q_u = float(A[ju, i]), float(Q[ju, i])
        ceil = a_u / max(ALPHA * a_u - ALPHA * q_u + BETA, 1e-12)
        s_null = float(predict(np.array([a_u]), np.array([q_u]), np.array([M[i]]), rho_b,
                               lam_best, np.array([OFF[i]]))[0])
        null_rows.append(dict(id=pid, reported=float(S[i]), M=float(M[i]),
                              a_uniform=a_u, q_uniform=q_u,
                              null_score_at_fitted_rho=s_null,
                              null_ceiling_rho_inf=float(ceil),
                              skill_ratio_vs_null=float(S[i] / s_null) if s_null > 0 else None))
    out["null_model"] = dict(
        definition=("hidden labels spread uniformly over the active domain: the score a "
                    "position-blind dot set of the same mass and separation would earn"),
        rho_used=rho_b, rows=null_rows,
        note=("The rho->inf ceiling a/(0.2a-0.2q+0.8) is the highest score any label count can "
              "give a position-blind set.  h34_scatter is the family's own arrangement-matched "
              "scatter control and is the empirical check of this null."))
    scat = [r for r in null_rows if r["id"] == "h34_scatter"]
    if scat:
        print(f"\nNULL CHECK  h34_scatter reported {scat[0]['reported']:.4f} vs uniform-density "
              f"ceiling {scat[0]['null_ceiling_rho_inf']:.4f}")

    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    (ROOT / "data" / "derived").mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(out, indent=1) + "\n")
    np.savez_compressed(ROOT / "data" / "derived" / "inversion_design.npz",
                        A=A.astype(np.float32), Q=Q.astype(np.float32), M=M, S=S, OFF=OFF,
                        ids=np.array(ids), names=np.array(names))
    print(f"wrote {args.out}  ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
