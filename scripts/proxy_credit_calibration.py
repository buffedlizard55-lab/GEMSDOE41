#!/usr/bin/env python3
"""Calibrate a local (visible-catalogue) credit instrument against implied hidden credit.

Instruments
-----------
1. HIDDEN credit T_hidden.  For each archived submission with a reported score s we
   solve the metric identity  s = T / (0.8*K + 0.2*N)  using the emitted mass N
   measured from the file itself and the metric-calibrated K from the nested
   thinning ladder (evidence/score_response.json).  This is a scalar per file and
   is NOT a claim about which pixels are hidden truth.

2. PROXY credit T_proxy.  The same archived file, frozen, is scored on a spatially
   blocked holdout whose truth is *visible catalogue strands that were withheld*
   (20 km four-colour blocks; strand-level whole-trace withholding; 300 m guard).
   This measures how much the file's geometry overlaps real mapped faults it never
   influenced directly, i.e. a local, label-free precision proxy.

The ratio lambda = T_hidden / T_proxy is the empirical transfer factor of the
instrument.  If it is stable across files, a *new* candidate's hidden credit can be
projected as lambda * T_proxy(candidate) before any submission slot is spent.

Caveats printed into the output: the archived files were built using the complete
catalogue (including withheld strands), so T_proxy is optimistically biased for
catalogue-derived geometries; scores are owner/user reports, not organizer receipts.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import rasterio
from scipy.ndimage import binary_dilation, distance_transform_edt, label as cc_label

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems41.metric import dti  # noqa: E402

BLOCK_PX = 200          # 20 km blocks
STRAND_MERGE_PX = 6     # dilate -> label, as src/gems41/validate.py
MIN_STRAND_PX = 60
GUARD_PX = 3.0          # truth must be > 300 m from every retained catalogue pixel
K_CALIBRATED = 14_088   # from the nested thinning ladder, evidence/score_response.json

LEDGER = [
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


def read(path: Path) -> np.ndarray:
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float32)
    a[~np.isfinite(a)] = 0.0
    return np.clip(a, 0.0, 1.0)


def build_folds(cat: np.ndarray) -> list[dict]:
    grown = binary_dilation(cat, np.ones((3, 3), bool), iterations=STRAND_MERGE_PX)
    lab, n = cc_label(grown, structure=np.ones((3, 3), dtype=int))
    sizes = np.bincount(lab.ravel())
    rows, cols = np.mgrid[0 : cat.shape[0], 0 : cat.shape[1]]
    block = (rows // BLOCK_PX + 2 * (cols // BLOCK_PX)) % 4
    strand_block: dict[int, int] = {}
    for i in range(1, n + 1):
        if sizes[i] < MIN_STRAND_PX:
            continue
        ys, xs = np.nonzero(lab == i)
        strand_block[i] = int(np.bincount(block[ys, xs], minlength=4).argmax())
    folds = []
    for f in range(4):
        held_ids = [i for i, b in strand_block.items() if b == f]
        lut = np.zeros(n + 1, bool)
        lut[held_ids] = True
        held = lut[lab] & cat
        retained = cat & ~held
        d_ret = distance_transform_edt(~retained).astype(np.float32)
        truth = held & (d_ret > GUARD_PX)
        folds.append(dict(fold=f, held_px=int(held.sum()), retained_px=int(retained.sum()),
                          truth=truth, retained=retained, d_ret=d_ret,
                          n_strands=len(held_ids)))
        del lut, held
    return folds


def main() -> None:
    cat = (read(ROOT / "data/existing_faults.tif") > 0.5)
    foot = np.isfinite(read(ROOT / "data/sample_submission.tif"))
    folds = build_folds(cat)
    print(json.dumps([{k: v for k, v in f.items() if k in ("fold", "held_px", "retained_px", "n_strands")}
                      | {"truth_px": int(f["truth"].sum())} for f in folds], indent=1))

    # per-fold FP weight field: distance from every active pixel to nearest truth pixel
    for f in folds:
        f["d_truth"] = distance_transform_edt(~f["truth"]).astype(np.float32)
        f["active"] = foot & ~f["retained"]

    rows = []
    for name, rel, score in LEDGER:
        p = ROOT / rel
        if not p.exists():
            rows.append(dict(name=name, status="missing"))
            continue
        pred = read(p)
        n_emitted = int((pred > 0).sum())
        T_hidden = score * (0.8 * K_CALIBRATED + 0.2 * n_emitted)
        tp_sum = fp_sum = fn_sum = 0.0
        per_fold = []
        for f in folds:
            r = dti(pred, f["truth"], footprint=foot, known=f["retained"])
            tp_sum += r["tp"]; fp_sum += r["fp"]; fn_sum += r["fn"]
            per_fold.append(round(r["dti"], 6))
        d = tp_sum + 0.2 * fp_sum + 0.8 * fn_sum
        rows.append(dict(
            name=name, reported_score=score, emitted_px=n_emitted,
            T_hidden_implied=round(T_hidden, 1),
            proxy_tp=round(tp_sum, 2), proxy_fp=round(fp_sum, 1), proxy_truth_px=int(sum(int(f['truth'].sum()) for f in folds)),
            proxy_dti_pooled=round(tp_sum / d, 6) if d else 0.0,
            proxy_dti_folds=per_fold,
            proxy_credit_per_mass=round(tp_sum / max(n_emitted, 1), 6),
            lambda_transfer=round(T_hidden / tp_sum, 3) if tp_sum > 0 else None,
        ))
        del pred
    vals = [r["lambda_transfer"] for r in rows if r.get("lambda_transfer")]
    summary = dict(
        n_files=len(vals),
        lambda_mean=float(np.mean(vals)) if vals else None,
        lambda_median=float(np.median(vals)) if vals else None,
        lambda_min=float(np.min(vals)) if vals else None,
        lambda_max=float(np.max(vals)) if vals else None,
        lambda_sd=float(np.std(vals)) if vals else None,
    )
    out = dict(
        protocol=dict(blocks_px=BLOCK_PX, blocks_km=BLOCK_PX / 10,
                      fold_formula="(row//200 + 2*(col//200)) % 4",
                      strand_merge_px=STRAND_MERGE_PX, min_strand_px=MIN_STRAND_PX,
                      guard_px=GUARD_PX,
                      masking="predictions on the retained (visible) catalogue are excluded, as the official rule does for published faults",
                      truth="withheld catalogue strands >300 m from retained catalogue",
                      note="same protocol as docs/downloads/holdout.json for folds; strand merging as src/gems41/validate.py"),
        K_calibrated=K_CALIBRATED,
        files=rows,
        lambda_summary=summary,
        caveats=[
            "T_hidden is a scalar derived from reported scores and the metric identity; it is not a label map.",
            "Archived files were built with the complete catalogue, so their proxy credit is optimistically biased.",
            "Reported scores are owner/user reports, not organizer receipts (registry/irregularities.json).",
        ],
    )
    (ROOT / "evidence/proxy_credit_calibration.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps(summary, indent=1))
    for r in rows:
        if r.get("lambda_transfer") is not None:
            print(f"{r['name']:22s} score={r['reported_score']:.4f} N={r['emitted_px']:7d} "
                  f"T_hidden={r['T_hidden_implied']:7.0f} T_proxy={r['proxy_tp']:8.1f} "
                  f"lambda={r['lambda_transfer']:6.2f}")


if __name__ == "__main__":
    main()
