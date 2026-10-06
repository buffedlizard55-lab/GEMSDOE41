"""H42: bimodal structural priors and the metric-optimal dot lattice.

ONE code path (`h42_components` + `h42_arms` + `pack_arms`) is used by BOTH the H42-HO
holdout validation and the shipped builds — the ranker that is measured is the ranker
that ships, the honesty rule inherited from `gems41.field`.  The arms are fixed and
preregistered in research/hypotheses-h42.md; nothing here may be tuned after results
are seen.

Arms (all on a 100 m grid, metres == 100 * pixels):

  h42d_state_prior      orientation match to the nearer strike population (criterion 2)
                        x scarp evidence, supported by retained state-map residual
                        geometry pruned >=200 m from the published catalogue.
  h42b_junction_prior   the brief's criterion 1 (proximity to NW-tip -> NNE receiver
                        transfer/extension/relay corridors) x the same soft gates.
  control_density       1/(1+distance to retained catalogue pixels).
  control_evidence      LiDAR scarp evidence only.
  control_random        deterministic uniform field.
  control_residual      residual-geometry proximity only (no gates) — isolates what the
                        orientation/evidence gates add.

Soft-gate floors (0.5 + 0.5*x) are the preregistered repair of H41-A's measured failure
mode: hard multiplication by a sparse detection mask zeroed the emission in every fold.
"""

from __future__ import annotations

import numpy as np
from scipy.ndimage import binary_dilation, distance_transform_edt

F32 = np.float32

ARMS = (
    "h42d_state_prior",
    "h42b_junction_prior",
    "control_density",
    "control_evidence",
    "control_random",
    "control_residual",
)

CATALOGUE_PRUNE_PX = 2.0   # 200 m off the published catalogue (H33's measured prune)
PACK_SEP_PX = 2.83         # minimum dot separation (evidence/thin_sweep.json)
BUDGETS_PX = (2_500, 5_000, 10_000, 20_000)   # fixed ladder for H42-HO
LIVE_MASS_PX = 37_654      # the family's best reported live mass; caps the shipped emission
EVAL_GUARD_PX = 3.0        # 300 m metric tolerance: truth must be isolated from retained geometry


def h42_components(
    cat_mask: np.ndarray,
    residual: np.ndarray,
    pop_a: np.ndarray,
    pop_b: np.ndarray,
    corridor: np.ndarray,
    lidar_strike: np.ndarray,
    lidar_valid: np.ndarray,
    evidence: np.ndarray,
    *,
    corridor_width_px: float = 2.0,
    nw_ref_deg: float = 142.0,
    nne_ref_deg: float = 8.6,
) -> dict:
    """Every field the arms and the shipped build need, from already-audited inputs.

    `residual` is the state-map fault mask pruned >=200 m from `cat_mask` OUTSIDE this
    function (the caller owns the prune so folds share one definition).
    """
    from .catalogue import angular_similarity

    d_cat = distance_transform_edt(~cat_mask).astype(F32)
    d_corr = distance_transform_edt(~corridor).astype(F32)
    corridor_soft = np.clip(1.0 - d_corr / F32(corridor_width_px), 0.0, 1.0)

    # criterion 2: locally detected lineament strike vs the geometrically closer family
    d_a = distance_transform_edt(~pop_a).astype(F32)
    d_b = distance_transform_edt(~pop_b).astype(F32)
    closer_is_a = d_a < d_b
    sim_a = angular_similarity(lidar_strike, nw_ref_deg).astype(F32)
    sim_b = angular_similarity(lidar_strike, nne_ref_deg).astype(F32)
    orient = np.where(lidar_valid, np.where(closer_is_a, sim_a, sim_b), F32(0.0))

    orient_soft = F32(0.5) + F32(0.5) * orient
    evidence_soft = F32(0.5) + F32(0.5) * np.clip(evidence, 0.0, 1.0)
    return dict(
        d_cat=d_cat,
        corridor=corridor,
        corridor_soft=corridor_soft.astype(F32),
        orient=orient.astype(F32),
        orient_soft=orient_soft.astype(F32),
        evidence=np.clip(evidence, 0.0, 1.0).astype(F32),
        evidence_soft=evidence_soft.astype(F32),
        residual=residual,
    )


def h42_arms(comp: dict, allowed: np.ndarray, rng: np.random.Generator) -> dict:
    """The preregistered arm table. Identical function on full map and inside each fold.

    Protocol amendment A1 (documented in research/hypotheses-h42.md before re-running): all
    line-anchored arms use the SAME 2 px proximity kernel as the corridor component
    (1 - d/2, clipped). The original 1 px state field was zero over the entire scored domain
    (the fold guard excludes all pixels within 3 px of retained geometry), which made the
    arm-vs-control comparison vacuous rather than negative.
    """
    d_sup = distance_transform_edt(~comp["residual"]).astype(F32)
    state = np.clip(1.0 - d_sup / F32(2.0), 0.0, 1.0) * comp["orient_soft"] * comp["evidence_soft"]
    out = {
        "h42d_state_prior": state,
        "h42b_junction_prior": comp["corridor_soft"] * comp["orient_soft"] * comp["evidence_soft"],
        "control_density": (F32(1.0) / (F32(1.0) + comp["d_cat"])).astype(F32),
        "control_evidence": comp["evidence"].copy(),
        "control_random": rng.random(comp["d_cat"].shape).astype(F32),
        "control_residual": np.clip(1.0 - d_sup / F32(2.0), 0.0, 1.0).astype(F32),
    }
    return {k: np.where(allowed, v, F32(0.0)).astype(F32) for k, v in out.items()}


def pack_arms(arms: dict, allowed: np.ndarray, *, sep_px: float, budget: int) -> dict:
    from .emission import greedy_pack

    return {
        k: greedy_pack(v, allowed, min_sep_px=sep_px, budget=budget, candidate_cap=400_000)
        for k, v in arms.items()
    }
