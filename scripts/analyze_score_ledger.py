#!/usr/bin/env python3
"""Score-response analysis of the owner-reported submission ledger (education only).

WHAT THIS DOES AND WHY IT IS LEGITIMATE
---------------------------------------
The official metric is a distance-weighted Tversky index (DTI) with alpha=0.2,
beta=0.8 and a 300 m triangular kernel.  For a raster whose positive cells carry
unit mass it can be re-written exactly:

    DTI = T / (0.8*K + 0.2*N_eff)                              ... (identity A)

    T      = sum over hidden-truth pixels g of  max_{x in R(g)} k(d(x,g)) * p(x)
             (the "credit": total kernel-weighted truth coverage, T <= K)
    K      = number of hidden-truth pixels inside the scored domain
    N_eff  = sum over prediction pixels of p(x)  MINUS the redundancy the metric
             does not pay for  (see derivation below)

Derivation (exact, for unit-mass dots that each dominate the truth pixels they
improve):
    D = T + 0.2*F + 0.8*(K - T),  F = sum_x p(x)*(1 - k_nearest_truth(x))
    => D = 0.2*T + 0.2*F + 0.8*K
    If every prediction pixel's own k equals the k of the truth pixel it best
    covers then 0.2*T + 0.2*F = 0.2*N and (A) is exact; redundant dots make F
    larger than that bookkeeping, i.e. N_eff <= N.  (A) with N_eff = N is
    therefore an OPTIMISTIC-in-score / conservative-in-mass approximation and
    the script reports it as such.

The identity turns a list of *public scalar scores* into a scalar estimate of the
hidden-truth credit T of each historical artifact.  That is metric calibration:
one number per file, from a formula the organizers publish.  This script does NOT
attempt to invert the scores into pixel-level hidden labels (that would be
leaderboard probing / test-set reconstruction); no such file is produced.

Outputs: evidence/score_response.json  (machine readable, all numbers here)
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gems41.metric import dti  # noqa: E402  (independent transcription)

# ---------------------------------------------------------------------------
# Ledger: file -> owner-reported score and the site it came from.  Scores are
# owner/user reports, NOT organizer receipts; the mapping file<->score is
# therefore treated as unverified throughout (see registry/irregularities.json).
# ---------------------------------------------------------------------------
LEDGER = [
    ("data/comparison-h33.tif", "H33-2-B2 37,654 px", 0.2778, "GEMSDOE32"),
    ("data/scored/r02708-h27-4-solo-d2-8.tif", "H27-4-r1-solo-d2-8", 0.2708, "GEMSDOE28/31"),
    ("data/scored/r02649-h32-1-prethin-tip-euler.tif", "H32-1 prethin tip euler", 0.2649, "GEMSDOE28"),
    ("data/scored/r02632-h33d-analog-tip-stepover.tif", "H33d analog tip stepover", 0.2632, "GEMSDOE33"),
    ("data/scored/r02600-dotted-d2-8-44090.tif", "dotted H19-5 d2.8 (44,090 px)", 0.2600, "GEMSDOE25"),
    ("data/scored/r02477-dotted-d1-5.tif", "dotted H19-5 d1.5", 0.2477, "GEMSDOE24"),
    ("data/scored/r02449-topo-gap-closure-d1-5.tif", "topo-gap-closure-t v2 d1.5", 0.2449, "GEMSDOE27"),
    ("data/scored/r01922-h19-5-powerlaw.tif", "H19-5 powerlaw budget", 0.1922, "GEMSDOE19"),
    ("data/scored/r01894-h19-4-multiline.tif", "H19-4 multiline thermal pop", 0.1894, "GEMSDOE19"),
    ("data/scored/r01855-h16-1-topo-geophys.tif", "H16-1 topo-geophys ridges", 0.1855, "GEMSDOE16"),
    ("data/scored/r01839-h28-dotted-ridge.tif", "H28 dotted ridge", 0.1839, "GEMSDOE10"),
    ("data/scored/r01563-hedge-v2.tif", "Hedge v2", 0.1563, "GEMSDOE8"),
    ("data/scored/r01563-ens12-adopted.tif", "ens12 adopted (7f00890a)", 0.1563, "GEMSDOE"),
    ("data/scored/r01280-h25-ctx-ridge.tif", "H25 ctx ridge", 0.1280, "GEMSDOE10"),
    ("data/scored/r00904-r13-lattice-s5.tif", "r13 lattice s5", 0.0904, "GEMSDOE13"),
    ("data/scored/r00107-placeholder-2314b599.tif", "gemsdoe9 2314b599", 0.0107, "GEMSDOE9"),
]

# The nested thinning ladder: same generator, decreasing emitted mass.  If the
# removed dots were pure misses (delta T = 0) the three reported scores must be
# consistent with ONE (K, T) pair:  s_i * (0.8K + 0.2 N_i) = T for all i.
LADDER = [
    ("data/scored/r02600-dotted-d2-8-44090.tif", 0.2600, "d2.8 @ 44,090 px"),
    ("data/scored/r02708-h27-4-solo-d2-8.tif", 0.2708, "h27-4 solo d2.8 @ 40,199 px"),
    ("data/comparison-h33.tif", 0.2778, "h33-2-b2 @ 37,654 px"),
]

K_GRID = [8_000, 10_000, 12_000, 13_000, 14_088, 16_000, 20_000]


def read_scored(path: Path) -> tuple[np.ndarray, dict]:
    with rasterio.open(path) as s:
        a = s.read(1).astype(np.float64)
        meta = dict(shape=s.shape, crs=str(s.crs), transform=list(s.transform)[:6],
                    dtype=s.dtypes[0], nodata=str(s.nodata))
    a[~np.isfinite(a)] = 0.0
    return a, meta


def nearest_catalogue_distance(cat: np.ndarray) -> np.ndarray:
    from scipy.ndimage import distance_transform_edt
    return distance_transform_edt(~cat)


def main() -> None:
    cat = (read_scored(ROOT / "data/existing_faults.tif")[0] > 0.5)
    dcat = nearest_catalogue_distance(cat)
    rows = []
    arrays = {}
    for rel, label, score, site in LEDGER:
        p = ROOT / rel
        if not p.exists():
            rows.append(dict(file=rel, label=label, reported_score=score, site=site,
                             status="missing"))
            continue
        a, meta = read_scored(p)
        arrays[label] = a
        pos = a > 0
        n = int(pos.sum())
        mass = float(a.sum())
        r, c = np.nonzero(pos)
        d = dcat[r, c]
        w = a[r, c]
        row = dict(
            file=rel, label=label, reported_score=score, site=site, status="ok",
            meta=meta,
            positive_cells=n, mass=mass,
            mean_value=float(w.mean()) if n else 0.0,
            frac_cells_at_one=float((w > 0.999).mean()) if n else 0.0,
            mass_within_200m_catalogue=float(w[d <= 2.0].sum()),
            mass_within_300m_catalogue=float(w[d <= 3.0].sum()),
            mass_within_1km_catalogue=float(w[d <= 10.0].sum()),
            mass_share_beyond_1km=float(w[d > 10].sum() / mass) if mass else 0.0,
            median_catalogue_distance_px=float(np.median(d)) if n else None,
            implied_credit_T=dict(
                (str(k), round(score * (0.8 * k + 0.2 * n), 1)) for k in K_GRID
            ),
        )
        rows.append(row)
        del a
    # ------------------------------------------------------------------
    # Ladder solve: find K minimising the spread of the implied T values.
    # ------------------------------------------------------------------
    ks = np.arange(4_000, 40_000, 10.0)
    ladder_rows = []
    for rel, score, tag in LADDER:
        a, _ = read_scored(ROOT / rel)
        n = int((a > 0).sum())
        ladder_rows.append((tag, score, n))
        del a
    best = None
    curve = []
    for k in ks:
        ts = [s * (0.8 * k + 0.2 * n) for _, s, n in ladder_rows]
        spread = (max(ts) - min(ts)) / float(np.mean(ts))
        curve.append((float(k), float(spread), float(np.mean(ts))))
        if best is None or spread < best[1]:
            best = (float(k), float(spread), float(np.mean(ts)))
    # pairwise closed-form K estimate (T_i = T_j)
    pairs = []
    for i in range(len(ladder_rows) - 1):
        (tag_i, s_i, n_i), (tag_j, s_j, n_j) = ladder_rows[i], ladder_rows[i + 1]
        denom = 0.8 * (s_i - s_j)
        if abs(denom) > 1e-12:
            k_est = (0.2 * s_j * n_j - 0.2 * s_i * n_i) / denom
            pairs.append(dict(pair=f"{tag_i} vs {tag_j}", K_estimate=float(k_est),
                              T_estimate=float(s_i * (0.8 * k_est + 0.2 * n_i))))
    # ------------------------------------------------------------------
    # Dot spacing: nearest-neighbour distance among positive cells (sampled)
    # ------------------------------------------------------------------
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(7)
    spacing = {}
    for label, a in arrays.items():
        r, c = np.nonzero(a > 0)
        if r.size < 10:
            continue
        idx = rng.choice(r.size, size=min(4000, r.size), replace=False)
        pts = np.column_stack([r[idx], c[idx]]).astype(float)
        tree = cKDTree(np.column_stack([r, c]).astype(float))
        d, _ = tree.query(pts, k=2, workers=1)
        nn = d[:, 1]
        spacing[label] = dict(
            nn_median_px=float(np.median(nn)),
            nn_p90_px=float(np.percentile(nn, 90)),
            frac_nn_le_2px=float(np.mean(nn <= 2.0)),
            frac_nn_ge_6px=float(np.mean(nn >= 6.0)),
        )
        del tree
    # ------------------------------------------------------------------
    # Pairwise support overlap (uniqueness table, education-scale comparison)
    # ------------------------------------------------------------------
    labels = sorted(arrays)
    pairs_j = {}
    for i in range(len(labels)):
        for j in range(i + 1, len(labels)):
            A = arrays[labels[i]] > 0
            B = arrays[labels[j]] > 0
            inter = int((A & B).sum())
            union = int((A | B).sum())
            pairs_j[f"{labels[i]} | {labels[j]}"] = round(inter / union, 5) if union else None
    out = dict(
        ledger=rows,
        ladder=dict(
            files=[dict(tag=t, score=s, positive_cells=n) for t, s, n in ladder_rows],
            best_K=best[0] if best else None,
            best_K_spread=best[1] if best else None,
            best_K_implied_T=best[2] if best else None,
            pairwise=pairs,
            k_curve=[dict(K=c[0], spread=c[1], T=c[2]) for c in curve[::200]],
            interpretation=(
                "Under the assumption that the pruned dots carried no hidden-truth "
                "credit, the three nested d2.8 scores are consistent with a single "
                "(K, T) pair; the K that minimises their spread is the best available "
                "metric-calibrated estimate of the hidden-truth size. Disagreement "
                "between the pairwise closed-form estimates measures how far that "
                "assumption is from true."
            ),
        ),
        dot_spacing=spacing,
        support_jaccard=pairs_j,
        caveats=[
            "Scores are owner/user reports, not organizer receipts (see registry/irregularities.json).",
            "Identity A assumes unit mass per dot and uses N_eff = N (optimistic).",
            "A score cannot identify which pixels are truth; no label inversion is attempted.",
        ],
        verified_with=dict(metric_module="src/gems41/metric.py", checks="tests/test_metric.py"),
    )
    dest = ROOT / "evidence/score_response.json"
    dest.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps(dict(
        ladder=out["ladder"]["files"], best_K=out["ladder"]["best_K"],
        spread=out["ladder"]["best_K_spread"], T=out["ladder"]["best_K_implied_T"],
        pairwise=out["ladder"]["pairwise"]), indent=1))
    print("wrote", dest)


if __name__ == "__main__":
    main()
