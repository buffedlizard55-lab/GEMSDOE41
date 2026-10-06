"""H41: the structural-position field.

The brief's two purely geometric criteria, plus one corroboration gate:

  (1) CORRIDOR    proximity to a plausible strain-transfer corridor between a mapped NW
                  fault's endpoint and the nearest mapped NNE fault (structure.py builds
                  tip-transfer, tip-extension and relay-ramp elements).
  (2) ORIENTATION whether the locally detected lineament's orientation (LiDAR band 11)
                  matches whichever population is geometrically closer to that pixel.
  (3) EVIDENCE    LiDAR scarp corroboration -- a gate, never a stand-alone detector.

CRITICAL DESIGN RULE FOR HONESTY: the ranker that is *measured* on the blocked holdout and
the ranker that is *shipped* are the same function (`combine_rankers`), fed by the same
component construction (`components_full` here, `validate.fold_contexts` per fold).  The
only difference is the catalogue the components are built from (full vs retained).
No separate shipping code path exists.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.ndimage import distance_transform_edt

from . import catalogue as C

F32 = np.float32

RANKER_NAMES = (
    "H41_corridor_x_orient_x_evidence",
    "H41_corridor_x_orient",
    "H41_corridor_only",
    "H41_orient_x_evidence",
    "baseline_lidar_evidence",
    "baseline_distance_to_retained",
    "baseline_random",
    "thrift_support_uniform",
    "thrift_support_kinematic_filter",
)


def _edt(mask: np.ndarray) -> np.ndarray:
    return distance_transform_edt(~mask).astype(F32)


def components_full(
    cat_mask: np.ndarray,
    pop_a: np.ndarray,
    pop_b: np.ndarray,
    elements: dict,
    lidar: dict,
    *,
    corridor_width_px: float = 2.0,
    exclusion_lo_px: float = 3.0,
    exclusion_hi_px: float = 5.0,
) -> dict:
    """Every component the rankers need, on the whole footprint."""
    d_cat = _edt(cat_mask)
    excl = np.clip(
        (d_cat - F32(exclusion_lo_px)) / F32(max(exclusion_hi_px - exclusion_lo_px, 1e-9)), 0.0, 1.0
    )
    excl = np.where(cat_mask, F32(0.0), excl).astype(F32)
    return dict(
        corridor=corridor_of(elements, corridor_width_px),
        orient=orient_of(pop_a, pop_b, lidar),
        evidence=lidar["evidence"],
        dist_to_catalogue=d_cat,
        exclusion=excl,
    )


def corridor_of(elements: dict, width_px: float = 2.0) -> np.ndarray:
    d = _edt(elements["corridor"])
    return np.clip(F32(1.0) - d / F32(width_px), 0.0, 1.0).astype(F32)


def orient_of(pop_a: np.ndarray, pop_b: np.ndarray, lidar: dict) -> np.ndarray:
    """Match the LOCALLY DETECTED lineament's strike to whichever population is nearer."""
    d_a = _edt(pop_a)
    d_b = _edt(pop_b)
    closer_is_a = d_a < d_b
    del d_a, d_b
    sim_a = C.angular_similarity(lidar["strike"], C.NW_REF_DEG).astype(F32)
    sim_b = C.angular_similarity(lidar["strike"], C.NNE_REF_DEG).astype(F32)
    out = np.where(closer_is_a, sim_a, sim_b)
    return np.where(lidar["valid"], out, F32(0.0)).astype(F32)


def combine_rankers(
    comp: dict,
    allowed: np.ndarray,
    rng: np.random.Generator,
    support: np.ndarray | None = None,
) -> dict[str, np.ndarray]:
    """The ONE ranker table: used by the holdout and by the shipped build alike.

    `support`, when given, is the incumbent's best-known live-scored emission support.
    Two rankers are added on it:
      thrift_support_uniform            -- the support as-is (control)
      thrift_support_kinematic_filter   -- the SAME support re-ranked by the bimodal
                                           criterion (local lineament orientation matched
                                           to whichever population is geometrically nearer)
    The pair is the test of this session's unique contribution: does the kinematic filter
    add credit at equal or lower mass on a support that already has live-scored evidence?
    """
    corr = comp["corridor"]
    orient = comp["orient"]
    ev = comp["evidence"]
    base = comp["dist_to_catalogue"]

    def w(x: np.ndarray) -> np.ndarray:
        return np.where(allowed, x, F32(0.0)).astype(F32)

    out = {
        "H41_corridor_x_orient_x_evidence": w(corr * orient * ev),
        "H41_corridor_x_orient": w(corr * orient),
        "H41_corridor_only": w(corr),
        "H41_orient_x_evidence": w(orient * ev),
        "baseline_lidar_evidence": w(ev),
        "baseline_distance_to_retained": w(F32(1.0) / (F32(1.0) + base)),
        "baseline_random": w(rng.random(comp["corridor"].shape).astype(F32)),
    }
    if support is not None:
        sup = np.asarray(support, bool) & allowed
        out["thrift_support_uniform"] = w(sup.astype(F32))
        out["thrift_support_kinematic_filter"] = w(sup.astype(F32) * (F32(0.05) + orient))
    return out


@dataclass
class FieldResult:
    score: np.ndarray
    components: dict
    meta: dict


def h41_field(
    cat_mask: np.ndarray,
    pop_a: np.ndarray,
    pop_b: np.ndarray,
    elements: dict,
    lidar: dict,
    *,
    variant: str = "corridor_x_orient",
    corridor_width_px: float = 2.0,
    exclusion_lo_px: float = 3.0,
    exclusion_hi_px: float = 5.0,
) -> FieldResult:
    comp = components_full(
        cat_mask, pop_a, pop_b, elements, lidar,
        corridor_width_px=corridor_width_px,
        exclusion_lo_px=exclusion_lo_px, exclusion_hi_px=exclusion_hi_px,
    )
    score = {
        "corridor_x_orient_x_evidence": comp["corridor"] * comp["orient"] * comp["evidence"],
        "corridor_x_orient": comp["corridor"] * comp["orient"],
        "corridor_only": comp["corridor"],
        "orient_x_evidence": comp["orient"] * comp["evidence"],
        "corridor_x_orient_x_evidence_soft": comp["corridor"]
        * (F32(0.5) + F32(0.5) * comp["orient"])
        * (F32(0.5) + F32(0.5) * comp["evidence"]),
    }[variant]
    score = np.where(cat_mask, F32(0.0), score).astype(F32)
    np.clip(score, 0.0, 1.0, out=score)
    return FieldResult(
        score=score,
        components=comp,
        meta=dict(variant=variant, corridor_width_px=corridor_width_px,
                  exclusion=(exclusion_lo_px, exclusion_hi_px),
                  candidate_px=int((score > 0).sum())),
    )


def junction_concentration(emission: np.ndarray, elements: dict, pop_a: np.ndarray, pop_b: np.ndarray) -> dict:
    """The brief's verification requirement: predicted pixels must concentrate at
    inter-population junctions, not inside either population's existing density."""
    d_corr = _edt(elements["corridor"])
    d_a = _edt(pop_a)
    d_b = _edt(pop_b)
    m = emission > 0
    n = int(m.sum())
    if n == 0:
        return dict(n=0)
    out = dict(
        n=n,
        frac_within_3px_of_corridor=round(float((d_corr[m] <= 3.0).mean()), 4),
        frac_inside_pop_a=round(float((d_a[m] < 1.0).mean()), 4),
        frac_inside_pop_b=round(float((d_b[m] < 1.0).mean()), 4),
        frac_in_neither_population=round(float(((d_a[m] >= 1.0) & (d_b[m] >= 1.0)).mean()), 4),
    )
    del d_corr, d_a, d_b
    return out
