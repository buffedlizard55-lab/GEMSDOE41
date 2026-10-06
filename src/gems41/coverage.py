"""H43: coverage-maximising emission -- the metric's own optimum, solved as a facility-location
problem instead of a threshold on a belief field.

WHY THIS MODULE EXISTS
----------------------
The official index is

    DTI = TP_w / (0.2 TP_w + 0.2 FP_w + 0.8 FN_w),   FN_w = |G| - TP_w
    TP_w = sum_{g in G} max_{x} p(x) k(d(x,g)),      k(d) = max(1 - d/3, 0)

`TP_w` takes a MAXIMUM over predictions for every truth pixel, so a second dot inside the
300 m kernel of a truth pixel that is already covered earns **nothing** and still pays
0.2 of its mass in `FP_w`.  Thresholding or fixed-separation packing a belief field
therefore wastes budget on redundant dots.  The measured consequence is in this family's own
live record (`evidence/score_record_calculus.json`): across the dotted lineage the
kernel-weighted coverage `a` is statistically CONSTANT at 0.287 while the emitted mass falls
from 121,131 px to 37,654 px, i.e. 69 % of the mass carried no credit at all, and 1/score is
linear in mass with slope 1.787e-5 (R^2 = 0.992 over the eight-point chain).

So the correct emission operator is: choose the dot set E that maximises

    F(E) = sum_x pi(x) * max_{y in E} k(d(x,y))          (expected TP_w, pi = belief)

subject to |E| = M, and stop when the marginal gain falls below the metric's own bar.
F is monotone submodular, so CELF lazy greedy is (1-1/e)-optimal and, in practice, returns
the same set as exact greedy at a small fraction of the cost.

THE STOPPING RULE (derived, not tuned)
--------------------------------------
With a = F(E)/sum(pi) and q the double-counting analogue, adding one more dot changes DTI
positively iff its marginal coverage gain g obeys

    g > 0.2 * DTI / rho        (rho = sum(pi) = expected hidden label count)

which is `marginal_bar` below -- the probabilistic form of the repository's existing
`k > alpha * DTI` rule (`src/gems41/metric.py`), restated per unit of belief mass.
"""
from __future__ import annotations

import heapq

import numpy as np

F32 = np.float32
RADIUS = 3.0
ALPHA = 0.2
BETA = 0.8


def kernel_offsets() -> list[tuple[int, int, float]]:
    """Identical convention to `gems41.metric._OFFSETS` (d <= R, k = max(1-d/R, 0)),
    with the zero-weight cells dropped so the loops are shorter but the sums identical."""
    out = []
    for dy in range(-3, 4):
        for dx in range(-3, 4):
            d = float(np.hypot(dy, dx))
            if d <= RADIUS:
                k = max(1.0 - d / RADIUS, 0.0)
                if k > 0.0:
                    out.append((dy, dx, k))
    return out


OFFS = kernel_offsets()
KERNEL_SUM = float(sum(k for _, _, k in OFFS))


def marginal_bar(dti: float, rho: float) -> float:
    """Coverage gain per unit belief above which one more dot raises DTI."""
    return ALPHA * dti / max(rho, 1e-12)


def shifted(a: np.ndarray, dy: int, dx: int) -> np.ndarray:
    """out[y, x] = a[y+dy, x+dx], ZERO outside the grid.

    `np.roll` would wrap the array edges, which is not what the official index does:
    `gems41.metric.dti` bounds-checks every offset.  Wrapping matters at the grid border and
    would silently move kernel mass from one edge of Nevada to the other.
    """
    H, W = a.shape
    out = np.zeros_like(a)
    y0, y1 = max(0, -dy), H - max(0, dy)
    x0, x1 = max(0, -dx), W - max(0, dx)
    if y0 >= y1 or x0 >= x1:
        return out
    out[y0:y1, x0:x1] = a[max(0, dy):H - max(0, -dy), max(0, dx):W - max(0, -dx)]
    return out


def coverage_field(mask: np.ndarray) -> np.ndarray:
    """K_E(x) = max_{y in E} k(d(x,y)) for an emission mask E."""
    p = np.asarray(mask, F32)
    out = np.zeros(p.shape, F32)
    for dy, dx, k in OFFS:
        np.maximum(out, shifted(p, dy, dx) * F32(k), out=out)
    return out


def coverage_sum_field(mask: np.ndarray) -> np.ndarray:
    """S_E(x) = sum_{y in E} k(d(x,y)) -- the double-counting version used for FP_w."""
    p = np.asarray(mask, F32)
    out = np.zeros(p.shape, F32)
    for dy, dx, k in OFFS:
        out += shifted(p, dy, dx) * F32(k)
    return out


def expected_coverage(pi: np.ndarray, mask: np.ndarray) -> float:
    """F(E) = sum_x pi(x) K_E(x) = the model's expected TP_w."""
    return float(np.sum(np.asarray(pi, np.float64) * coverage_field(mask).astype(np.float64)))


def model_dti(pi: np.ndarray, mask: np.ndarray, rho: float | None = None,
              exact_fp: bool = True) -> dict:
    """Expected DTI of an emission set under the belief field pi.

    pi(x) is the per-pixel probability that x is a hidden label pixel, so
    rho = sum(pi) is the expected hidden label count |G|.

    E[TP_w] = sum_x pi(x) * max_{y in E} k(d(x,y))            (exact: TP_w is a max)
    E[FP_w] = sum_{y in E} p(y) * prod_x (1 - pi(x) k(d(x,y)))
            ~ sum_{y in E} p(y) * exp(-(pi * k)(y))            (Poisson approximation)
    E[FN_w] = rho - E[TP_w]
    """
    pi = np.asarray(pi, np.float64)
    r = float(pi.sum()) if rho is None else float(rho)
    p = np.asarray(mask, F32)
    M = float(p.sum())
    A = float(np.sum(pi * coverage_field(p).astype(np.float64)))
    S = coverage_sum_field(pi.astype(F32)).astype(np.float64)  # (pi * k)(y)
    if exact_fp:
        F = float(np.sum(np.where(p > 0, np.exp(-np.minimum(S, 700.0)), 0.0)))
    else:
        F = float(M - np.sum(p.astype(np.float64) * S))
    F = max(F, 0.0)
    denom = ALPHA * A + ALPHA * F + BETA * r
    return dict(a=A / r if r > 0 else 0.0, q=float(np.sum(p.astype(np.float64) * S)) / r if r > 0 else 0.0,
                M=M, rho=r, expected_tp=A, expected_fp=F,
                dti=float(A / denom) if denom > 0 else 0.0)


def _gains_batch(pi: np.ndarray, K: np.ndarray, idx: np.ndarray, W: int, H: int) -> np.ndarray:
    """Marginal coverage gain of every flat index in `idx`, vectorised."""
    y = idx // W
    x = idx - y * W
    g = np.zeros(idx.shape, np.float64)
    for dy, dx, k in OFFS:
        ny = y + dy
        nx = x + dx
        ok = (ny >= 0) & (ny < H) & (nx >= 0) & (nx < W)
        if not ok.any():
            continue
        flat = (ny * W + nx)[ok]
        room = pi.ravel()[flat].astype(np.float64) * np.maximum(0.0, k - K.ravel()[flat].astype(np.float64))
        g[ok] += room
    return g


def _gain_one(pi: np.ndarray, K: np.ndarray, j: int, W: int, H: int) -> float:
    y, x = divmod(j, W)
    g = 0.0
    for dy, dx, k in OFFS:
        ny, nx = y + dy, x + dx
        if 0 <= ny < H and 0 <= nx < W:
            room = k - K[ny, nx]
            if room > 0.0:
                g += float(pi[ny, nx]) * room
    return g


def max_cover_greedy(
    pi: np.ndarray,
    allowed: np.ndarray,
    budget: int,
    *,
    pool_cap: int = 400_000,
    priority: np.ndarray | None = None,
    stop_gain: float | None = None,
    checkpoints: tuple[int, ...] = (),
) -> dict:
    """CELF lazy-greedy maximum-coverage emission.

    Parameters
    ----------
    pi      : belief field (expected hidden-label intensity), >= 0.
    allowed : boolean emission domain.
    budget  : maximum number of dots.
    pool_cap: the candidate shortlist, taken as the top `pool_cap` pixels by
              `priority` (default: the kernel-smoothed belief, i.e. the expected
              coverage a single dot would earn).
    stop_gain: stop early once the marginal coverage gain falls below this bar.
    checkpoints: masses at which to snapshot the emission mask.

    Returns dict(selected=flat indices in order, mask=(H,W) bool, K=coverage field,
                 gains=[...], snapshots={m: mask}).
    """
    pi = np.asarray(pi, np.float64)
    H, W = pi.shape
    if priority is None:
        # exact single-dot gain: (pi * k)(y), the SUM convolution, not the max.  pi is NOT
        # masked by `allowed`: the belief about where hidden truth sits is defined everywhere,
        # only the EMISSION is restricted to the allowed domain.  Truncating pi to `allowed`
        # discards exactly the belief mass the emitter is supposed to cover.
        priority = coverage_sum_field(pi.astype(F32)).astype(np.float64)
    cand = np.flatnonzero(allowed.ravel() & (priority.ravel() > 0))
    if cand.size == 0:
        return dict(selected=np.array([], np.int64), mask=np.zeros(pi.shape, bool),
                    K=np.zeros(pi.shape, F32), gains=[], snapshots={})
    if cand.size > pool_cap:
        top = np.argpartition(-priority.ravel()[cand], pool_cap)[:pool_cap]
        pool = cand[top]
    else:
        pool = cand
    g0 = _gains_batch(pi, np.zeros(pi.shape, F32), pool, W, H)
    order = np.argsort(-g0)
    pool = pool[order]
    gain = g0[order]

    heap = [(-float(gain[i]), int(pool[i]), 0) for i in range(pool.size)]
    heapq.heapify(heap)
    K = np.zeros(pi.shape, F32)
    selected: list[int] = []
    gains: list[float] = []
    snapshots: dict[int, np.ndarray] = {}
    version = 0
    flatK = K.ravel()
    flatpi = pi.ravel()
    ck = sorted(set(int(c) for c in checkpoints if 0 < c <= budget))
    while len(selected) < budget and heap:
        neg, j, v = heapq.heappop(heap)
        if v < version:
            g = _gain_one(pi, K, j, W, H)
            heapq.heappush(heap, (-g, j, version))
            continue
        g = -neg
        if stop_gain is not None and g < stop_gain:
            break
        if g <= 0.0:
            break
        selected.append(j)
        gains.append(float(g))
        y, x = divmod(j, W)
        for dy, dx, k in OFFS:
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and k > flatK[ny * W + nx]:
                flatK[ny * W + nx] = k
        version += 1
        if ck and len(selected) == ck[0]:
            m = np.zeros(pi.shape, bool)
            m.ravel()[np.array(selected, np.int64)] = True
            snapshots[len(selected)] = m
            ck.pop(0)
    mask = np.zeros(pi.shape, bool)
    if selected:
        mask.ravel()[np.array(selected, np.int64)] = True
    return dict(selected=np.array(selected, np.int64), mask=mask, K=K, gains=gains,
                snapshots=snapshots, pool_size=int(pool.size))
