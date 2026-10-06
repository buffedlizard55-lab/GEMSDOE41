"""Structural elements (H41-A): the strain-transfer corridors of the Walker Lane.

HYPOTHESIS BEING ENCODED
------------------------
Where a NW-striking dextral (Walker Lane) trace *ends*, dextral shear is transferred
into the NNE-to-N-striking normal faults of the Basin and Range, and the linkage itself
is where unmapped faults live (Faulds et al. 2005; Siler et al., Emerson Pass).  Three
geometric element families follow directly from that framework:

  TIP-TRANSFER   : from a population-A endpoint to the nearest population-B trace
                   (the transfer corridor).  Emerson Pass type locality: Pyramid Lake
                   fault -> Lake Range fault, INSIDE this footprint.
  TIP-EXTENSION  : along-strike continuation beyond a mapped endpoint (a fault that is
                   real but unmapped further along its own trend).
  RELAY-RAMP     : between two en-echelon A endpoints (overlapping, similar strike),
                   the left-stepping relay ramps the 2005 paper describes.

All three are pure geometry on the published catalogue -- no new geophysical transform,
exactly as the brief requires.
"""

from __future__ import annotations

import numpy as np

from . import catalogue as C


def _nearest_pixel(mask_ys: np.ndarray, mask_xs: np.ndarray, r: int, c: int):
    if mask_ys.size == 0:
        return None
    d2 = (mask_ys - r) ** 2 + (mask_xs - c) ** 2
    j = int(np.argmin(d2))
    return int(mask_ys[j]), int(mask_xs[j]), float(np.sqrt(d2[j]))


def build_elements(
    traces: list[C.Trace],
    A: np.ndarray,
    B: np.ndarray,
    max_transfer_px: float = 200.0,  # 20 km
    tip_extension_px: float = 100.0,  # 10 km
    relay_max_px: float = 150.0,  # 15 km
    relay_min_px: float = 20.0,  # 2 km
    relay_strike_tol: float = 30.0,
) -> dict:
    """Rasterise the three element families onto the 100 m grid."""
    shape = A.shape
    ys_a, xs_a = np.nonzero(A)
    ys_b, xs_b = np.nonzero(B)

    transfer = np.zeros(shape, bool)
    extension = np.zeros(shape, bool)
    relay = np.zeros(shape, bool)

    def draw(mask: np.ndarray, r0: int, c0: int, r1: int, c1: int) -> None:
        n = int(max(abs(r1 - r0), abs(c1 - c0))) + 1
        rr = np.linspace(r0, r1, n).round().astype(int)
        cc = np.linspace(c0, c1, n).round().astype(int)
        ok = (rr >= 0) & (rr < shape[0]) & (cc >= 0) & (cc < shape[1])
        mask[rr[ok], cc[ok]] = True

    a_traces = [t for t in traces if C.classify_population(t) == "A"]
    b_traces = [t for t in traces if C.classify_population(t) == "B"]

    n_transfer = n_extension = n_relay = 0

    # --- TIP-TRANSFER: A endpoints -> nearest B trace pixel
    for t in a_traces:
        for (r, c) in (t.endpoint_a, t.endpoint_b):
            hit = _nearest_pixel(ys_b, xs_b, r, c)
            if hit is None:
                continue
            br, bc, d = hit
            if d > max_transfer_px:
                continue
            draw(transfer, r, c, br, bc)
            n_transfer += 1

    # --- TIP-EXTENSION: continue each A trace beyond both endpoints along its strike
    for t in a_traces:
        th = np.radians(t.strike)
        # direction with azimuth == strike: (dx, dy_south) = (sin, -cos)
        ux, uy = np.sin(th), -np.cos(th)
        for (r, c), sgn in ((t.endpoint_a, +1), (t.endpoint_b, -1)):
            r2 = int(round(r + sgn * uy * tip_extension_px))
            c2 = int(round(c + sgn * ux * tip_extension_px))
            draw(extension, r, c, r2, c2)
            n_extension += 1

    # --- RELAY-RAMP: en-echelon A endpoints within [relay_min, relay_max], similar strike
    ends = []
    for t in a_traces:
        ends.append((t.endpoint_a, t))
        ends.append((t.endpoint_b, t))
    for i in range(len(ends)):
        (r1, c1), t1 = ends[i]
        for j in range(i + 1, len(ends)):
            (r2, c2), t2 = ends[j]
            if t1.trace_id == t2.trace_id:
                continue
            d = np.hypot(r2 - r1, c2 - c1)
            if not (relay_min_px <= d <= relay_max_px):
                continue
            ds = abs(t1.strike - t2.strike)
            ds = min(ds, 180.0 - ds)
            if ds > relay_strike_tol:
                continue
            draw(relay, r1, c1, r2, c2)
            n_relay += 1

    return dict(
        transfer=transfer,
        extension=extension,
        relay=relay,
        counts=dict(transfer=n_transfer, extension=n_extension, relay=n_relay),
        a_traces=len(a_traces),
        b_traces=len(b_traces),
    )


def pyramid_lake_check(row: int, col: int) -> bool:
    """Emerson Pass / Pyramid Lake type locality lies inside the footprint (verified)."""
    return 0 <= row < 3730 and 0 <= col < 3292
