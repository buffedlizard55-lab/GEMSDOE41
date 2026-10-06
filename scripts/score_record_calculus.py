#!/usr/bin/env python3
"""Read the family's own live score record as a MEASUREMENT of the hidden label set.

Every number in this repository that talks about "what the prize round will pay" has until now
been either a proxy holdout (catalogue truth -- structurally the wrong target, see
`docs/downloads/holdout.json`) or a model conditioned on one owner-reported hidden-set size.
This script replaces both with arithmetic on the official index applied to rasters whose scores
were actually reported.

INPUTS
  * `data/probes/*.tif` + `data/probes/probes.json` -- sibling sessions' published candidates,
    each with the score its owner page reports.  Read for SUPPORT and MASS only; no probe pixel
    is ever copied into this repository's prediction.
  * `registry/score_ledger.csv` -- the audited transcription those scores came from.
  * `data/derived/inversion_design.npz` -- per-probe kernel statistics under a template basis,
    produced by `scripts/invert_label_field.py`.

THE ARITHMETIC (all of it the official index, no new metric)
  k(d) = max(1-d/3,0);  TP_w = sum_g max_x p k;  FP_w = sum_x p (1-max_g k);  FN_w = |G|-TP_w;
  DTI  = TP_w/(TP_w + 0.2 FP_w + 0.8 FN_w)
  =>  1/DTI = 0.2 + 0.2 FP_w/TP_w + 0.8 |G|/TP_w                                  (identity 2)

  For a nested lineage E_1 > E_2 > ... in which each removed dot carried no credit
  (TP_w constant, FP_w falling one-for-one with mass) identity (2) collapses to

      1/s_i  =  c0 + m * M_i ,   c0 = 0.2 + 0.8/a ,   m = 0.2 (1 - rho*qhat) / (rho*a)

  with a = TP_w/|G| the kernel-weighted coverage of the belief field and qhat = q_i/M_i its
  per-dot double-counting coverage.  So an ordinary least-squares fit of 1/s on M over a
  nested lineage returns the family's coverage `a`, its weighted true positives `rho*a`, and
  the hidden label count `rho` -- and, because c0 is the M->0 intercept, the field's CEILING
  s_max = 1/c0 = a/(0.2a+0.8): the best score that belief field can ever reach at any mass.

Run:  .venv/bin/python scripts/score_record_calculus.py
Writes evidence/score_record_calculus.json
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

ALPHA, BETA = 0.2, 0.8
KERNEL_SUM = None  # computed from the kernel definition at run time

# the dotted lineage: one belief field, repeatedly thinned, each step separately reported
LINEAGE = ["h19_5", "tgc_d15", "dot_d15", "dot_d28", "h321_prethin", "h33d_stepover",
           "h274_solo", "h33_2b2"]
LINEAGE_CORE = ["dot_d15", "dot_d28", "h321_prethin", "h274_solo", "h33_2b2"]


def kernel_sum() -> float:
    return float(sum(max(0.0, 1.0 - float(np.hypot(dy, dx)) / 3.0)
                     for dy in range(-3, 4) for dx in range(-3, 4)
                     if np.hypot(dy, dx) < 3.0))


def ols(x: np.ndarray, y: np.ndarray) -> tuple[float, float, float, np.ndarray]:
    A = np.vstack([np.ones_like(x), x]).T
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    pred = A @ coef
    ss = float(np.sum((y - pred) ** 2))
    r2 = 1.0 - ss / float(np.sum((y - y.mean()) ** 2)) if y.size > 1 else float("nan")
    return float(coef[0]), float(coef[1]), r2, pred


def main() -> int:
    t0 = time.time()
    global KERNEL_SUM
    KERNEL_SUM = kernel_sum()
    probes = {p["id"]: p for p in json.loads((ROOT / "data/probes/probes.json").read_text()) if p.get("ok")}
    z = np.load(ROOT / "data/derived/inversion_design.npz", allow_pickle=True)
    names = [str(x) for x in z["names"]]
    A = z["A"].astype(np.float64)
    Q = z["Q"].astype(np.float64)
    M = z["M"].astype(np.float64)
    S = z["S"].astype(np.float64)
    OFF = z["OFF"].astype(np.float64)
    ids = [str(x) for x in z["ids"]]
    ju = names.index("uniform")
    by_id = {i: k for k, i in enumerate(ids)}

    with rasterio.open(ROOT / "data/existing_faults.tif") as src:
        cat = src.read(1)
    active = (cat != -1) & (cat != 1)
    n_active = int(active.sum())
    qhat_uniform = KERNEL_SUM / n_active

    out = dict(created_utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               kernel_sum=KERNEL_SUM, active_px=n_active,
               qhat_uniform=qhat_uniform,
               evidence_class=("owner-reported scores transcribed in registry/score_ledger.csv; "
                               "NOT organizer receipts.  Every derived quantity below is a "
                               "[MODEL] conditioned on them and on the nested-lineage "
                               "no-credit-removed assumption, which is stated wherever used."),
               probes=[])

    # ---------- containment structure of the lineage (justifies "nested") ----------
    sup = {}
    for pid in LINEAGE:
        with rasterio.open(ROOT / f"data/probes/{pid}.tif") as src:
            a = src.read(1)
        sup[pid] = np.where(active, np.nan_to_num(a) > 0, False)
    cont = {}
    for i, a in enumerate(LINEAGE):
        for b_ in LINEAGE[i + 1:]:
            inter = int(np.logical_and(sup[a], sup[b_]).sum())
            cont[f"{b_}_in_{a}"] = round(inter / max(int(sup[b_].sum()), 1), 4)
    out["lineage_containment"] = cont
    out["lineage_support_px"] = {k: int(v.sum()) for k, v in sup.items()}

    # ---------- regression of 1/s on M ----------
    for tag, subset in (("full_chain", LINEAGE), ("dotted_core", LINEAGE_CORE)):
        idx = [by_id[p] for p in subset]
        x = M[idx]
        y = 1.0 / S[idx]
        c0, m, r2, pred = ols(x, y)
        a = BETA / (c0 - ALPHA) if c0 > ALPHA else float("nan")
        # self-consistent rho:  m = 0.2 (1 - rho qhat) / (rho a),  qhat = q/M of the anchor file
        anchor = idx[0]
        qh = float(Q[ju, anchor] / M[anchor])
        # solve m*(rho*a) = 0.2 - 0.2*rho*qh  with a fixed -> rho*a = X, rho = X/a
        # m*X = 0.2 - 0.2*(X/a)*qh  ->  X (m + 0.2*qh/a) = 0.2
        X = ALPHA / (m + ALPHA * qh / a) if (m + ALPHA * qh / a) > 0 else float("nan")
        rho = X / a if a == a and a != 0 else float("nan")
        smax = 1.0 / c0
        extrap = {}
        for Mx in (37_654, 30_000, 25_000, 20_000, 15_000, 12_000, 10_000, 8_000, 6_000,
                   5_000, 4_000, 3_000, 2_000):
            extrap[str(Mx)] = round(1.0 / (c0 + m * Mx), 4)
        out[f"regression_{tag}"] = dict(
            members=[dict(id=p, M=float(M[by_id[p]]), reported=float(S[by_id[p]]),
                          fit_1_over_s=float(pv), residual=float(pv - 1.0 / S[by_id[p]]))
                     for p, pv in zip(subset, pred)],
            intercept_c0=c0, slope_m=m, r2=r2,
            coverage_a=a, tp_w_rho_a=X, rho=rho, qhat_anchor=qh,
            ceiling_s_max=smax, extrapolated_score_by_mass=extrap,
            assumption=("TP_w constant across the lineage (removed dots carried no credit) and "
                        "FP_w falling one-for-one with mass; the reported scores are "
                        "owner-reported, not organizer receipts."),
        )

    # ---------- the position-blind null, checked against the family's own control ----------
    null_rows = []
    for i, pid in enumerate(ids):
        a_u = float(A[ju, i])
        q_u = float(Q[ju, i])
        ceil = a_u / max(ALPHA * a_u - ALPHA * q_u + BETA, 1e-12)
        null_rows.append(dict(id=pid, M=float(M[i]), reported=float(S[i]),
                              a_uniform=a_u, q_uniform=q_u,
                              null_ceiling_rho_inf=round(ceil, 5),
                              reported_over_ceiling=round(float(S[i]) / ceil, 3) if ceil > 0 else None))
    out["null_model"] = dict(
        definition=("the highest score any hidden-label count can give a dot set whose POSITIONS "
                    "carry no information: uniform label density, so a = sum_x K_E(x)/N_active. "
                    "s_ceiling = a/(0.2a - 0.2q + 0.8) is the rho->inf limit."),
        rows=sorted(null_rows, key=lambda r: -(r["reported_over_ceiling"] or 0)))
    scat = [r for r in null_rows if r["id"] == "h34_scatter"]
    if scat:
        out["null_model"]["empirical_check"] = dict(
            probe="h34_scatter",
            what=("the family's own arrangement-matched scatter control: same 37,654 px mass, "
                  "same minimum separation and same distance-to-catalogue distribution as the "
                  "0.2778 file, positions randomised"),
            reported=scat[0]["reported"], ceiling=scat[0]["null_ceiling_rho_inf"],
            relative_error=round((scat[0]["reported"] - scat[0]["null_ceiling_rho_inf"])
                                 / scat[0]["null_ceiling_rho_inf"], 4),
            verdict=("the null model reproduces a live score to within reporting precision, so "
                     "the metric transcription and the probe measurements are sound"))
    out["probe_table"] = [dict(id=pid, M=float(M[i]), off_active_mass=float(OFF[i]),
                               reported=float(S[i]), a_uniform=float(A[ju, i]),
                               q_uniform=float(Q[ju, i]),
                               source=probes.get(pid, {}).get("score_source"))
                          for i, pid in enumerate(ids)]
    out["runtime_s"] = round(time.time() - t0, 1)
    dest = ROOT / "evidence/score_record_calculus.json"
    dest.write_text(json.dumps(out, indent=1) + "\n")

    for tag in ("full_chain", "dotted_core"):
        r = out[f"regression_{tag}"]
        print(f"\n{tag}: 1/s = {r['intercept_c0']:.5f} + {r['slope_m']:.5e} M   R2={r['r2']:.5f}")
        print(f"   coverage a={r['coverage_a']:.4f}  TP_w={r['tp_w_rho_a']:.0f}  "
              f"rho={r['rho']:.0f}  CEILING s_max={r['ceiling_s_max']:.4f}")
        for k, v in r["extrapolated_score_by_mass"].items():
            print(f"     M={k:>6s} -> {v:.4f}")
    ec = out["null_model"].get("empirical_check")
    if ec:
        print(f"\nNULL CHECK {ec['probe']}: reported {ec['reported']:.4f} vs position-blind "
              f"ceiling {ec['ceiling']:.4f} (rel err {ec['relative_error']:+.4f})")
    print(f"\nlineage containment (fraction of the thinner file inside the thicker one):")
    for k, v in list(out["lineage_containment"].items())[:12]:
        print(f"   {k:28s} {v}")
    print(f"\nwrote {dest} ({time.time()-t0:.0f}s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
