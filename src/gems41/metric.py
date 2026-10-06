"""The official Distance-Weighted Tversky Index (DTI), transcribed line by line.

SOURCE (official, verified 2026-10-05):
  https://www.drivendata.org/competitions/306/competition-doe-gems/page/967/
  section "Performance metric" / "Mathematical representation".

  k(d)   = max(1 - d / R, 0),  R = 300 m  (= 3 px at 100 m)
  TP_w   = sum_{g in G} max_{x: d(x,g) <= R} p(x) * k(d(x,g))
  FP_w   = sum_{x: p(x) > 0} p(x) * [1 - max_{g in G} k(d(x,g))]
  FN_w   = sum_{g in G} [1 - max_{x: d(x,g) <= R} p(x) * k(d(x,g))]
  DTI    = TP_w / (TP_w + alpha*FP_w + beta*FN_w + eps),  alpha = 0.2, beta = 0.8

TWO IDENTITIES USED THROUGHOUT THIS PROJECT (both proved in `tests/test_metric.py`
against a brute-force transcription):

  (1)  FN_w = |G| - TP_w                       exactly, always.
  (2)  1/DTI = alpha + alpha*(F/T) + beta*(K/T)
              = 0.2 + 0.2*FP_w/TP_w + 0.8*|G|/TP_w

OBSERVATIONS THAT DRIVE THE EMISSION DESIGN:

  * Adding one unit of mass at a pixel whose best covering kernel weight is k
    changes DTI by  (k*D - alpha*T) / (D + alpha)^2  with D = TP_w + alpha*FP_w + beta*FN_w.
    Hence **added mass pays for itself iff k > alpha * DTI** (0.056 at DTI = 0.28).
  * Mass farther than 300 m from every hidden truth pixel (k = 0) strictly *lowers*
    the score.  There is no such thing as a "harmless" false positive.

VERIFIED OFFICIAL SCORING CONVENTION (DrivenData staff, forum thread 11516, post 2):
    "Pixels corresponding to known USGS/INGENIOUS faults are masked / excluded from
     evaluation, so they do not count towards penalty terms."  Round 2 is masked too.
  -> predictions on the published catalogue are inert; predictions *near* it but not
     on it are ordinary {TP, FP} pixels.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import distance_transform_edt

ALPHA = 0.2
BETA = 0.8
RADIUS_PX = 3.0
EPS = 1e-12

# Kernel offsets: (dy, dx, k(d)) for every cell within R = 3 px.
_OFFSETS: list[tuple[int, int, float]] = []
for _dy in range(-3, 4):
    for _dx in range(-3, 4):
        _d = float(np.hypot(_dy, _dx))
        if _d <= RADIUS_PX:
            _OFFSETS.append((_dy, _dx, max(1.0 - _d / RADIUS_PX, 0.0)))


def kernel(d: np.ndarray | float) -> np.ndarray:
    return np.maximum(1.0 - np.asarray(d, dtype=np.float64) / RADIUS_PX, 0.0)


def dti(
    prediction: np.ndarray,
    truth: np.ndarray,
    footprint: np.ndarray | None = None,
    known: np.ndarray | None = None,
) -> dict:
    """Official DTI with the official masking convention.

    Parameters
    ----------
    prediction : (H, W) float, values in [0, 1]; NaN treated as 0.
    truth      : (H, W) boolean/0-1; the *hidden* fault set G.
    footprint  : (H, W) bool; the scored domain. Defaults to all pixels.
    known      : (H, W) bool; published-catalogue pixels to exclude (official rule).
    """
    pred = np.asarray(prediction, dtype=np.float64)
    tru = np.asarray(truth)
    if pred.shape != tru.shape:
        raise ValueError("prediction and truth must be the same shape")
    if footprint is None:
        footprint = np.ones(pred.shape, bool)
    if known is None:
        known = np.zeros(pred.shape, bool)

    # Official masking: the scored domain excludes published-catalogue pixels.
    active = np.asarray(footprint, bool) & ~np.asarray(known, bool)
    p = np.where(active & np.isfinite(pred), pred, 0.0)
    p = np.clip(p, 0.0, 1.0)
    g = active & (tru > 0)

    ys, xs = np.nonzero(g)
    n_truth = int(ys.size)
    if n_truth == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0, dti=0.0)

    # --- TP_w: for each truth pixel, the best kernel-weighted prediction in range.
    best = np.zeros(n_truth, dtype=np.float64)
    H, W = p.shape
    for dy, dx, k in _OFFSETS:
        ny, nx = ys + dy, xs + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        if not ok.any():
            continue
        cand = np.zeros(n_truth, dtype=np.float64)
        cand[ok] = p[ny[ok], nx[ok]] * k
        np.maximum(best, cand, out=best)
    tp = float(best.sum())

    # --- FP_w: every unit of mass pays (1 - its own best kernel weight).
    #     Computed exactly: distance from every active pixel to the nearest truth pixel.
    if n_truth:
        dist_to_truth = distance_transform_edt(~g)
        k_own = kernel(dist_to_truth)
        weight = np.where(active, p, 0.0) * (1.0 - np.minimum(k_own, 1.0))
        fp = float(weight.sum())
    else:
        fp = float(p.sum())

    fn = float(n_truth) - tp  # identity (1)
    denom = tp + ALPHA * fp + BETA * fn + EPS
    return dict(
        tp=tp,
        fp=fp,
        fn=fn,
        n_truth=n_truth,
        dti=float(tp / denom),
        # the two quantities the identity (2) is written in
        credit_per_mass=(tp / float(p.sum())) if p.sum() > 0 else 0.0,
        mass=float(p.sum()),
    )


def dti_bruteforce(
    prediction: np.ndarray, truth: np.ndarray, footprint: np.ndarray | None = None, known=None
) -> dict:
    """Deliberately naive O(|G| x |P|) transcription of the official formulas.

    Used only by the test suite as an independent check of `dti`.
    """
    pred = np.asarray(prediction, dtype=np.float64)
    tru = np.asarray(truth)
    if footprint is None:
        footprint = np.ones(pred.shape, bool)
    if known is None:
        known = np.zeros(pred.shape, bool)
    active = np.asarray(footprint, bool) & ~np.asarray(known, bool)
    p = np.where(active & np.isfinite(pred), pred, 0.0)
    g = active & (tru > 0)
    gy, gx = np.nonzero(g)
    py, px = np.nonzero(p > 0)
    if gy.size == 0:
        return dict(tp=0.0, fp=float(p.sum()), fn=0.0, n_truth=0, dti=0.0)
    # TP_w
    tp = 0.0
    for yy, xx in zip(gy, gx):
        if py.size == 0:
            break
        d = np.hypot(py - yy, px - xx)
        tp += float(np.max(p[py, px] * kernel(d)))
    # FP_w
    fp = 0.0
    for yy, xx in zip(py, px):
        d = np.hypot(gy - yy, gx - xx)
        fp += float(p[yy, xx] * (1.0 - min(float(np.max(kernel(d))), 1.0)))
    fn = float(gy.size) - tp
    return dict(tp=tp, fp=fp, fn=fn, n_truth=int(gy.size), dti=tp / (tp + ALPHA * fp + BETA * fn + EPS))


def marginal_bar(dti_value: float) -> float:
    """The kernel weight above which an added unit of mass raises DTI: alpha * DTI."""
    return ALPHA * dti_value


def truth_size_from_scores(
    files_px: list[int], scores: list[float], remove_px: list[int] | None = None
) -> list[float]:
    """Invert identity (2) for |G| from nested emission files with known live scores.

    For a nested chain F_0 superset F_1 superset ... with total emitted pixels
    `files_px` and owner-reported live scores `scores`, assuming the removed mass
    carried no credit (the group's own finding: it was dead weight), each adjacent
    pair gives an independent estimate

        K = ( alpha*s_i*S_i - alpha*s_j*S_j ) / ( beta*(s_j - s_i) )

    which is returned, one entry per adjacent pair.
    """
    out = []
    for i in range(len(files_px) - 1):
        s_i, s_j = scores[i], scores[i + 1]
        S_i, S_j = files_px[i], files_px[i + 1]
        denom = BETA * (s_j - s_i)
        if denom == 0:
            continue
        out.append((ALPHA * s_i * S_i - ALPHA * s_j * S_j) / denom)
    return out
