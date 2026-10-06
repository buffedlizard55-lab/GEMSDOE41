"""H43 belief-field calibration: turning a classifier's output into an intensity the metric
can be optimised against.

Two corrections, both derivations rather than tunings:

1. `prior_shift` -- the classifier is trained on a subsampled negative set, so its prior is
   wrong by a known factor.  With sampled prior p_s and target prior p_t,
       odds_t = odds_s * [p_t/(1-p_t)] / [p_s/(1-p_s)]
   is exact for any model whose likelihood ratio is unchanged by subsampling.  Without it the
   low-probability body of the field is inflated by roughly the negative subsampling factor,
   and a coverage-maximising emitter then maximises coverage of that flat body.  Measured on
   fold 0 of the strand-blocked holdout, uncalibrated coverage-greedy scored DTI 0.00286
   against the position-blind uniform control's 0.00312 -- i.e. no better than scattering dots
   at random -- while score-ordered packing of the same field scored 0.06076.  After calibration
   the same emitter scores 0.01386.  THOSE THREE NUMBERS ARE LOWER BOUNDS: they were measured
   before the emission-domain defect described in `research/review-passes.md` (pass 2, item 1)
   was found.  On the corrected instrument, calibrated coverage-greedy reaches 0.48062 on the
   same fold at the same mass (`evidence/h43_holdout.json`).  The qualitative conclusion --
   weights destroy the coverage emitter, the analytic correction restores it -- is unchanged and
   is corroborated independently by sum(pi) landing at 0.75-0.88x the withheld truth count in
   all four folds.

2. `sharpen` -- pi is a PROBABILITY field; the hidden label set is a nearly deterministic set
   concentrated at the top of it.  The official index pays `max_x p(x) k(d(x,g))` per truth
   pixel, so what matters is coverage of where the truth actually is, not of the probability
   volume.  Raising pi to a power gamma and renormalising to the same total mass keeps
   sum(pi) -- and therefore the model's rho -- fixed while concentrating the coverage
   objective.  gamma is a single preregistered scalar (8), not a per-fold tuning parameter.
"""
from __future__ import annotations

import numpy as np

F32 = np.float32
GAMMA_PREREGISTERED = 8.0


def prior_shift(p: np.ndarray, p_sampled: float, p_true: float) -> np.ndarray:
    """Undo a known negative-subsampling prior shift exactly."""
    if not (0.0 < p_sampled < 1.0) or not (0.0 < p_true < 1.0):
        return np.asarray(p, F32)
    c = (p_true / (1.0 - p_true)) / (p_sampled / (1.0 - p_sampled))
    q = np.clip(np.asarray(p, np.float64), 1e-12, 1.0 - 1e-12)
    o = q / (1.0 - q) * c
    return (o / (1.0 + o)).astype(F32)


def prior_shift_factor(p_sampled: float, p_true: float) -> float:
    return (p_true / (1.0 - p_true)) / (p_sampled / (1.0 - p_sampled))


def sharpen(pi: np.ndarray, gamma: float = GAMMA_PREREGISTERED) -> np.ndarray:
    """pi**gamma renormalised to the same total mass, so sum(pi) and rho are unchanged."""
    pi = np.clip(np.asarray(pi, np.float64), 0.0, 1.0)
    tot = float(pi.sum())
    if tot <= 0.0:
        return pi.astype(F32)
    s = np.power(pi, float(gamma))
    st = float(s.sum())
    if st <= 0.0:
        return pi.astype(F32)
    return (s * (tot / st)).astype(F32)
