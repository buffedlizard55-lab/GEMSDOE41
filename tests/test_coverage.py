"""H43 coverage emitter and belief calibration: identities, not vibes.

Every test here is a property that must hold exactly if the emission operator is really
optimising the official index, checked against `gems41.metric.dti` (which is itself checked
against a brute-force transcription in `tests/test_metric.py`).
"""
from __future__ import annotations

import os
import sys

import numpy as np
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from gems41 import belief as B
from gems41 import coverage as CV
from gems41 import metric as M


def test_kernel_offsets_match_the_official_metric_exactly():
    mine = {(dy, dx): round(k, 12) for dy, dx, k in CV.OFFS}
    theirs = {(dy, dx): round(k, 12) for dy, dx, k in M._OFFSETS if k > 0}
    assert mine == theirs
    assert abs(CV.KERNEL_SUM - sum(k for _, _, k in M._OFFSETS)) < 1e-12
    assert abs(CV.KERNEL_SUM - 9.380297810508184) < 1e-12


def test_coverage_field_of_a_single_dot_is_the_kernel():
    m = np.zeros((11, 11), bool)
    m[5, 5] = True
    K = CV.coverage_field(m)
    for dy, dx, k in CV.OFFS:
        assert K[5 + dy, 5 + dx] == pytest.approx(k, abs=1e-6)
    assert K.sum() == pytest.approx(CV.KERNEL_SUM, abs=1e-4)
    # cells at exactly R = 3 px carry zero weight, so they are never touched
    assert K[5, 8] == 0.0 and K[8, 5] == 0.0


def test_coverage_is_a_max_and_coverage_sum_is_additive():
    m = np.zeros((21, 21), bool)
    m[5, 5] = True
    m[5, 16] = True  # 11 px apart: disjoint kernels
    K, S = CV.coverage_field(m), CV.coverage_sum_field(m)
    assert K.sum() == pytest.approx(2 * CV.KERNEL_SUM, abs=1e-3)
    assert S.sum() == pytest.approx(2 * CV.KERNEL_SUM, abs=1e-3)
    m2 = np.zeros((21, 21), bool)
    m2[5, 5] = True
    m2[5, 6] = True  # 1 px apart: overlapping kernels
    K2, S2 = CV.coverage_field(m2), CV.coverage_sum_field(m2)
    assert S2.sum() == pytest.approx(2 * CV.KERNEL_SUM, abs=1e-3)
    assert K2.sum() < S2.sum()  # the max is strictly smaller once kernels overlap


def test_expected_coverage_equals_the_official_tp_for_a_deterministic_field():
    """With pi an indicator, sum(pi * K_E) IS TP_w of the official index."""
    rng = np.random.default_rng(7)
    truth = rng.random((40, 50)) < 0.02
    mask = np.zeros((40, 50), bool)
    ys, xs = np.nonzero(~truth)
    sel = rng.choice(ys.size, 25, replace=False)
    mask[ys[sel], xs[sel]] = True
    tp = M.dti(mask.astype(np.float32), truth)["tp"]
    # coverage_field accumulates in float32 (it runs over 12.28 M cells on a 3 GB host),
    # so the identity holds to float32 precision, not to float64.
    assert CV.expected_coverage(truth.astype(np.float64), mask) == pytest.approx(tp, rel=1e-6)


def test_model_dti_reproduces_the_official_index_for_a_deterministic_field():
    rng = np.random.default_rng(11)
    truth = rng.random((40, 50)) < 0.03
    mask = np.zeros((40, 50), bool)
    ys, xs = np.nonzero(truth)
    mask[ys[:12], xs[:12]] = True  # emit on 12 of the truth pixels: FP_w = 0 exactly
    got = CV.model_dti(truth.astype(np.float64), mask, rho=float(truth.sum()), exact_fp=False)
    ref = M.dti(mask.astype(np.float32), truth)
    assert got["expected_tp"] == pytest.approx(ref["tp"], rel=1e-6)
    assert got["M"] == ref["mass"]
    # first-order FP is an upper bound on the exact FP; with emission on truth it is 0 either way
    assert ref["fp"] == pytest.approx(0.0, abs=1e-9)
    assert got["dti"] == pytest.approx(ref["dti"], rel=1e-4)


def test_greedy_gains_are_non_increasing_and_respect_the_domain():
    rng = np.random.default_rng(3)
    pi = np.zeros((60, 70), np.float64)
    for _ in range(6):
        y, x = rng.integers(6, 54), rng.integers(6, 64)
        pi[y - 2:y + 3, x - 2:x + 3] += rng.random() * 2 + 0.5
    allowed = np.zeros(pi.shape, bool)
    allowed[3:-3, 3:-3] = True
    out = CV.max_cover_greedy(pi, allowed, budget=40)
    g = np.array(out["gains"])
    assert g.size == 40
    assert np.all(np.diff(g) <= 1e-9), "submodular greedy gains must be non-increasing"
    assert np.all(allowed[out["mask"]])
    assert int(out["mask"].sum()) == 40


def test_greedy_never_emits_outside_allowed_and_stops_at_zero_gain():
    pi = np.zeros((30, 30), np.float64)
    pi[10, 10] = 1.0
    allowed = np.ones(pi.shape, bool)
    out = CV.max_cover_greedy(pi, allowed, budget=500)
    # a single belief pixel is exhausted after a handful of dots: gain hits 0 and it stops
    assert 0 < int(out["mask"].sum()) < 40
    assert out["mask"][10, 10]


def test_coverage_greedy_beats_fixed_separation_packing_on_a_redundant_peak():
    """The property H43-A exists for.

    A solid belief block next to a long thin ridge: score-ordered packing fills the block with
    dots 2.83 px apart, but the block is only ~3 px across, so every dot after the first two
    covers belief that is already covered and earns nothing extra.  Coverage greedy sees that
    and moves on to the ridge.  Same budget, same domain -- strictly more expected TP_w.
    """
    from gems41 import emission as E

    pi = np.zeros((40, 120), np.float64)
    pi[16:25, 16:25] = 1.0          # the peak: a 9x9 solid block
    pi[20, 40:115] = 0.9            # the ridge: long, thin, slightly weaker
    allowed = np.ones(pi.shape, bool)
    budget = 20
    cov = CV.max_cover_greedy(pi, allowed, budget=budget)["mask"]
    pack = E.greedy_pack(pi + 1e-9 * np.random.default_rng(0).random(pi.shape), allowed,
                         min_sep_px=2.83, budget=budget)
    a_cov = CV.expected_coverage(pi, cov)
    a_pack = CV.expected_coverage(pi, pack)
    assert int(cov.sum()) == budget and int(pack.sum()) == budget
    assert a_cov > a_pack * 1.05, (a_cov, a_pack)
    in_block_cov = int(cov[16:25, 16:25].sum())
    in_block_pack = int(pack[16:25, 16:25].sum())
    assert in_block_pack > in_block_cov, "packing should over-fill the redundant peak"
    assert int(cov[20, 40:115].sum()) > int(pack[20, 40:115].sum())


def test_prior_shift_is_exact_for_a_known_subsample():
    rng = np.random.default_rng(5)
    n = 40_000
    y = (rng.random(n) < 0.01).astype(np.int8)          # true prior 1 %
    keep = (y == 1) | (rng.random(n) < 0.1)              # subsample negatives to 10 %
    p_s, p_t = float(y[keep].mean()), float(y.mean())
    p_hat = np.full(1000, float(y[keep].mean()))
    got = B.prior_shift(p_hat, p_s, p_t)
    assert float(got[0]) == pytest.approx(p_t, rel=0.02)


def test_prior_shift_is_the_identity_when_priors_match():
    p = np.linspace(0.01, 0.99, 50)
    assert np.allclose(B.prior_shift(p, 0.2, 0.2), p, atol=1e-6)


def test_sharpen_preserves_total_mass_and_concentrates_it():
    pi = np.array([0.5, 0.25, 0.15, 0.1], dtype=np.float64)
    s = B.sharpen(pi, 8.0)
    assert float(s.sum()) == pytest.approx(float(pi.sum()), rel=1e-5)
    assert float(s[0]) / float(s.sum()) > float(pi[0]) / float(pi.sum())
    assert np.all(np.diff(s) < 0)


def test_sharpen_handles_empty_and_saturated_fields():
    z = np.zeros((5, 5), np.float32)
    assert float(B.sharpen(z).sum()) == 0.0
    one = np.ones((5, 5), np.float32)
    assert np.allclose(B.sharpen(one, 8.0), one)


def test_marginal_bar_is_the_metric_own_stopping_rule():
    # one more dot pays iff its coverage gain exceeds 0.2 * DTI / rho (belief units)
    assert CV.marginal_bar(0.2778, 36_000.0) == pytest.approx(0.2 * 0.2778 / 36_000.0)
    assert CV.marginal_bar(0.5, 100.0) > CV.marginal_bar(0.25, 100.0)
