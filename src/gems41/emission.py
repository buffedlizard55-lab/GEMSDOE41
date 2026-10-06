"""Emission rules: how a score field becomes a submission raster.

THE METRIC'S OWN ARITHMETIC (proved in tests/test_metric.py)
-----------------------------------------------------------
    DTI = T / (0.2*S + 0.8*M + 0.2*(T - Mk))        (exact, with the official masks)
    marginal rule: added mass pays iff  k > 0.2 * DTI

Consequences used here:

  * MASS IS A COST.  Every emitted pixel adds 0.2 to the denominator regardless of where
    it lands, and only pixels within 300 m of a *hidden* truth pixel can earn anything.
  * REDUNDANCY IS A COST.  A truth pixel is credited once (max over predictions), so
    packing dots closer than the kernel support buys nothing and pays twice.
  * MEASURED FACT (this checkout): the best-known live-scored artifact
    (`dotted-h19-5-d2-8`, owner-reported 0.2600, 44,090 px) has a MINIMUM
    nearest-neighbour distance of exactly 2*sqrt(2) = 2.828 px and a median of 3.0 px.
    It is a minimum-separation dot set, not a solid line.  Its owner-reported successors
    (0.2708, 0.2778) are strict subsets of it, i.e. every live gain in the family's
    record came from REMOVING mass, never from adding a better field.
  => the packing separation is a first-class parameter of the submission, and it is
     swept here against a spatially blocked holdout rather than assumed.
"""

from __future__ import annotations

import numpy as np


def greedy_pack(
    score: np.ndarray,
    allowed: np.ndarray,
    *,
    min_sep_px: float,
    budget: int,
    candidate_cap: int = 400_000,
) -> np.ndarray:
    """Highest-score-first packing with a minimum pairwise separation constraint.

    Parameters
    ----------
    score   : (H, W) priority field.  Higher is better.
    allowed : (H, W) bool mask of candidate pixels (e.g. off-catalogue, footprint).
    min_sep_px, budget : the packing geometry and the mass budget.

    Returns a boolean (H, W) emission mask.
    """
    cand_all = np.argwhere(allowed & np.isfinite(score) & (score > 0))
    if cand_all.size == 0:
        return np.zeros(score.shape, bool)
    vals = score[cand_all[:, 0], cand_all[:, 1]]
    order = np.argsort(-vals, kind="stable")
    cand_all = cand_all[order]

    r2 = int(np.ceil(min_sep_px)) + 1
    offs = [
        (dy, dx)
        for dy in range(-r2, r2 + 1)
        for dx in range(-r2, r2 + 1)
        if dy * dy + dx * dx <= min_sep_px * min_sep_px
    ]
    keep = np.zeros(score.shape, bool)
    taken: set[tuple[int, int]] = set()
    n = 0
    # Expand the candidate pool only as far as needed: the pool is consumed in score
    # order, so a small pool usually fills the budget.
    cap = min(candidate_cap, cand_all.shape[0])
    while n < budget and cap > 0:
        for (y, x) in cand_all[:cap]:
            y = int(y)
            x = int(x)
            hit = False
            for dy, dx in offs:
                if (y + dy, x + dx) in taken:
                    hit = True
                    break
            if hit:
                continue
            taken.add((y, x))
            keep[y, x] = True
            n += 1
            if n >= budget:
                break
        if cap >= cand_all.shape[0]:
            break
        cap = min(cap * 2, cand_all.shape[0])
    return keep


def thin_support(
    support: np.ndarray,
    *,
    min_sep_px: float,
    budget: int | None = None,
    priority: np.ndarray | None = None,
) -> np.ndarray:
    """Re-emit an existing support at a minimum separation (the thrift arm).

    This is the operation the family's own record shows working: 1.5 px -> 2.8 px
    spacing raised the live score at constant coverage.  Here it is swept further and
    measured against a blocked holdout instead of being asserted.
    """
    score = np.ones(support.shape) if priority is None else np.asarray(priority, np.float64)
    score = np.where(support, score, 0.0)
    # spread tied priorities so the greedy step is deterministic and spatially even
    if priority is None:
        yy, xx = np.indices(support.shape)
        score = np.where(support, 1.0 + 1e-6 * ((yy * 7919 + xx * 104729) % 1009), 0.0)
    return greedy_pack(
        score, support, min_sep_px=min_sep_px, budget=budget if budget else int(support.sum())
    )


def union(*masks: np.ndarray) -> np.ndarray:
    out = np.zeros(masks[0].shape, bool)
    for m in masks:
        out |= m
    return out


def describe(mask: np.ndarray) -> dict:
    n = int(mask.sum())
    if n == 0:
        return dict(n=0)
    from scipy.spatial import cKDTree

    p = np.argwhere(mask).astype(np.float64)
    t = cKDTree(p)
    d, _ = t.query(p, k=2)
    nn = d[:, 1]
    return dict(
        n=n,
        nn_min=float(nn.min()),
        nn_median=float(np.median(nn)),
        nn_p95=float(np.percentile(nn, 95)),
    )
