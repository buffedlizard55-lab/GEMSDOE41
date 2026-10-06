"""Catalogue traces + the two-population kinematic classification.

THE STRUCTURAL FRAMEWORK (verified against primary literature, links in docs/sources.html)

  Faulds, J.E., Henry, C.D., Hinz, N.H., 2005, "Kinematics of the northern Walker Lane:
  an incipient transform fault along the Pacific-North American plate boundary",
  Geology 33(6), 505-508, doi:10.1130/G21274.1.  Verbatim from the paper:
      "The northern Walker Lane consists of kinematically linked systems of NW-striking,
       left-stepping dextral faults, N-striking normal faults, and subordinate
       ENE-striking sinistral faults"
      "The strike-slip faults end in arrays of ~N-striking normal faults, suggesting
       that dextral shear diffuses into extension in the Great Basin."

  Siler et al., "Structural controls of the Emerson Pass geothermal system, northwestern
  Nevada: characterization of a 'blind' system" (OSTI 1110519), verbatim:
      "NW-directed dextral shear is transferred to WNW extension accommodated by N-to-NNE
       striking normal faults of the Basin and Range."
      "The NW-striking right-lateral Pyramid Lake fault, a major structure of the
       northern Walker Lane, terminates at the southern end of Pyramid Lake and
       transfers strain to the NNE-striking down to the west Lake Range fault"

MEASURED IN THIS CHECKOUT (not assumed) -- see evidence/catalogue_kinematics.json:
  * The official catalogue's own `slip_sense` attribute (GDR/USGS QFaults) splits it:
       RL (right-lateral)  : 62 in-footprint traces, length-weighted mean strike 142 deg
                             (= 322 az), 77.3 % of its length NW-striking (100-170 deg),
                             longitudes 117.80-119.74 W  (the western, Walker Lane side)
       N  (normal)         : 242 in-footprint traces, length-weighted mean strike 8.6 deg,
                             48.4 % of its length NNE-to-N, spread across the footprint
       LL (left-lateral)   : 13 traces, mean 69 deg  -> a real third, minor population
  So the bimodal framing is a measured property of this exact catalogue, with the
  honest caveat that a subordinate sinistral population exists (Faulds et al. 2005 say
  the same thing).
"""

from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from scipy.ndimage import label as cc_label

MIN_TRACE_PX = 20  # a shorter component cannot carry a reliable strike

# Population reference strikes, in the "azimuth mod 180, clockwise from north" convention
# (0 = N-S, 45 = NE, 90 = E-W, 135 = NW).  Values are the length-weighted means MEASURED
# from the official catalogue's QFaults slip_sense attributes in this checkout.
NW_REF_DEG = 142.0  # Walker Lane, dextral
NNE_REF_DEG = 8.6  # Basin and Range, normal


def strike_mod180(dx: float, dy_south: float) -> float:
    """Strike azimuth (mod 180) from a direction vector in array coordinates.

    Array coordinates are (col=+x east, row=+y south), so north = -y.
    """
    return math.degrees(math.atan2(dx, -dy_south)) % 180.0


def angular_similarity(a_deg: np.ndarray | float, b_deg: float) -> np.ndarray:
    """|cos(2*(a-b))|: 1 when the two strikes are parallel or anti-parallel, 0 at 45 deg.

    Doubling the angle makes the measure correct for axial (mod-180) data.
    """
    d = np.radians(2.0 * (np.asarray(a_deg, dtype=np.float64) - b_deg))
    return np.abs(np.cos(d))


@dataclass
class Trace:
    trace_id: int
    n_px: int
    strike: float  # mod 180, degrees
    centroid_row: float
    centroid_col: float
    elongation: float
    endpoint_a: tuple[int, int]  # (row, col) extremes along the major axis
    endpoint_b: tuple[int, int]
    sense: str  # 'RL' | 'N' | 'LL' | 'unknown'


def extract_traces(cat_mask: np.ndarray) -> list[Trace]:
    """Connected components -> oriented traces with endpoints and a sense label."""
    lab, n = cc_label(cat_mask, structure=np.ones((3, 3), dtype=int))
    sizes = np.bincount(lab.ravel())
    traces: list[Trace] = []
    for i in range(1, n + 1):
        if sizes[i] < MIN_TRACE_PX:
            continue
        ys, xs = np.nonzero(lab == i)
        pts = np.c_[xs, ys].astype(np.float64)
        mean = pts.mean(0)
        X = pts - mean
        cov = X.T @ X
        w, v = np.linalg.eigh(cov)
        major = v[:, -1]
        strike = strike_mod180(float(major[0]), float(major[1]))
        elong = float(math.sqrt(max(w[-1], 1e-9) / max(w[0], 1e-9)))
        proj = X @ major
        a = pts[int(np.argmin(proj))]
        b = pts[int(np.argmax(proj))]
        traces.append(
            Trace(
                trace_id=int(i),
                n_px=int(sizes[i]),
                strike=float(strike),
                centroid_row=float(mean[1]),
                centroid_col=float(mean[0]),
                elongation=elong,
                endpoint_a=(int(round(a[1])), int(round(a[0]))),
                endpoint_b=(int(round(b[1])), int(round(b[0]))),
                sense="unknown",
            )
        )
    return traces


def classify_population(trace: Trace, nw_halfwidth: float = 35.0) -> str:
    """'A' = Walker Lane NW dextral population, 'B' = Basin-and-Range normal population.

    A trace joins population A when its slip sense is RL (right-lateral) or, absent an
    attribute, when its strike lies within `nw_halfwidth` degrees of the measured
    NW reference of 142 deg.  LL and unknown-sense traces that are not NW-striking are
    left out of both populations (they are the subordinate sinistral family).
    """
    if trace.sense == "RL":
        return "A"
    if trace.sense in ("N", "LL"):
        return "B" if trace.sense == "N" else "none"
    # no attribute: fall back to strike only
    d = min(abs(trace.strike - NW_REF_DEG), 180.0 - abs(trace.strike - NW_REF_DEG))
    if d <= nw_halfwidth:
        return "A"
    d2 = min(abs(trace.strike - NNE_REF_DEG), 180.0 - abs(trace.strike - NNE_REF_DEG))
    return "B" if d2 <= 45.0 else "none"


def attach_kinematics(traces: list[Trace], qfaults_csv: str, max_join_px: float = 15.0) -> dict:
    """Join QFaults `slip_sense` onto raster components by centroid proximity.

    Returns a small audit dict (counts joined per sense value) for the evidence file.
    """
    import csv

    rows = list(csv.DictReader(open(qfaults_csv, newline="", encoding="utf-8")))
    q = []
    for r in rows:
        try:
            if r.get("centroid_in_footprint") not in (None, "", "0"):
                q.append((float(r["centroid_row"]), float(r["centroid_col"]), r.get("slip_sense", "nan")))
        except (KeyError, ValueError):
            continue
    if not q:
        return {"joined": 0, "by_sense": {}}
    qr = np.array([x[0] for x in q])
    qc = np.array([x[1] for x in q])
    qs = [x[2] for x in q]
    counts: dict[str, int] = {}
    for t in traces:
        d = np.hypot(qr - t.centroid_row, qc - t.centroid_col)
        j = int(np.argmin(d))
        if d[j] <= max_join_px:
            t.sense = qs[j]
            counts[t.sense] = counts.get(t.sense, 0) + 1
        else:
            t.sense = "unknown"
            counts["unknown"] = counts.get("unknown", 0) + 1
    return {"joined": sum(counts.values()), "by_sense": counts, "max_join_px": max_join_px}


def population_masks(
    shape: tuple[int, int], traces: list[Trace], dilate: int = 1
) -> tuple[np.ndarray, np.ndarray, dict]:
    """Rasterise the two populations.  Returns (maskA, maskB, summary)."""
    from scipy.ndimage import binary_dilation

    lab_shape = shape
    # Re-rasterise by trace id requires the original label grid; instead we rebuild from
    # the trace endpoints via a thin line, which is what the geometry needs.
    def line_mask(t: Trace) -> np.ndarray:
        m = np.zeros(lab_shape, bool)
        r0, c0 = t.endpoint_a
        r1, c1 = t.endpoint_b
        n = int(max(abs(r1 - r0), abs(c1 - c0))) + 1
        rr = np.linspace(r0, r1, n).round().astype(int)
        cc = np.linspace(c0, c1, n).round().astype(int)
        ok = (rr >= 0) & (rr < lab_shape[0]) & (cc >= 0) & (cc < lab_shape[1])
        m[rr[ok], cc[ok]] = True
        return m

    A = np.zeros(lab_shape, bool)
    B = np.zeros(lab_shape, bool)
    summary = {"A": {"traces": 0, "px": 0}, "B": {"traces": 0, "px": 0}, "none": 0}
    for t in traces:
        pop = classify_population(t)
        if pop == "A":
            A |= line_mask(t)
            summary["A"]["traces"] += 1
        elif pop == "B":
            B |= line_mask(t)
            summary["B"]["traces"] += 1
        else:
            summary["none"] += 1
    if dilate:
        st = np.ones((3, 3), bool)
        A = binary_dilation(A, st, iterations=dilate)
        B = binary_dilation(B, st, iterations=dilate)
    summary["A"]["px"] = int(A.sum())
    summary["B"]["px"] = int(B.sum())
    return A, B, summary
