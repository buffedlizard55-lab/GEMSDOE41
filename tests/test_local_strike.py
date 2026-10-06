import sys
from pathlib import Path

import numpy as np
import pytest
from affine import Affine
from shapely.geometry import LineString

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from local_strike import nearest_local_strikes, local_prediction
from experiment_h41i import conditional_targets, match_mass, summarize


def test_local_tangent_not_whole_trace_axis():
    bent = LineString([(0, 0), (0, 1000), (1000, 1000)])
    angles = nearest_local_strikes([bent], [[10, 300], [700, 1010]])
    np.testing.assert_allclose(angles, [0, 90])
    np.testing.assert_allclose(angles, nearest_local_strikes([LineString(list(bent.coords)[::-1])], [[10, 300], [700, 1010]]))


def test_empty_missing_tie_and_endpoint():
    n = LineString([(0, 0), (0, 1000)])
    e = LineString([(0, 0), (1000, 0)])
    assert nearest_local_strikes([n, e], [[0, 0]])[0] == 0
    assert nearest_local_strikes([e, n], [[0, 0]])[0] == 90
    assert nearest_local_strikes([], [[1, 2]]).shape == (1,)
    assert np.isnan(nearest_local_strikes([], [[1, 2]])[0])
    assert nearest_local_strikes([n], []).size == 0
    assert nearest_local_strikes([e], [[1200, 0]])[0] == 90
    with pytest.raises(ValueError):
        nearest_local_strikes([n], [[0, 0]], half_window_m=0)


def test_degenerate_hairpin_no_fabricated_strike():
    hairpin = LineString([(0, 0), (250, 0), (0, 0)])
    assert np.isnan(nearest_local_strikes([hairpin], [[250, 0]])[0])


def test_family_tie_normal_and_non_detection_zero():
    a = np.ones((2, 2), dtype=np.float32)
    recs = [{'geometry': LineString([(0, 0), (0, 1000)]), 'family': 0},
            {'geometry': LineString([(0, 0), (1000, 0)]), 'family': 1}]
    detected = np.array([[True, False], [True, True]])
    p, stats = local_prediction(recs, a, [a, a], a * 90, detected, Affine(100, 0, 0, 0, -100, 1000))
    np.testing.assert_array_equal(p, detected.astype(float))
    assert stats['family_pixels']['1'] == 3


def test_mass_matching_capped_and_zero():
    field = np.array([[.01, 1, .5], [0, 0, 0]], dtype=np.float32)
    mask = np.ones_like(field, dtype=bool)
    p = match_mass(field, mask, 2.5)
    assert p.sum() == pytest.approx(2.5, abs=1e-6)
    assert p.max() <= 1
    assert match_mass(field, mask, 10).sum() == 3
    assert match_mass(field, mask, 0).sum() == 0
    assert match_mass(np.zeros_like(field), mask, 2).sum() == 0


def test_target_selection_never_uses_same_source_as_both_neighbors():
    transform = Affine(100, 0, -1000, 0, -100, 3000)
    target = {'source_id': 'target', 'geometry': LineString([(0, 0), (500, 500)]), 'family': 0, 'eligible': True}
    receiver = {'source_id': 'normal', 'geometry': LineString([(1000, 0), (1000, 11000)]), 'family': 1, 'eligible': True}
    assert 'target' not in conditional_targets([target, receiver], transform, (200, 200))
    donor = {'source_id': 'NW', 'geometry': LineString([(100, 0), (10100, 10000)]), 'family': 0, 'eligible': True}
    result = conditional_targets([target, receiver, donor], transform, (200, 200))
    assert set(result) == {'target'}


def test_empty_truth_not_reported_as_scored_fold():
    folds = [{'models': {'candidate': {'truth_pixels': 0, 'dti': 0, 'tp': 0, 'fp': 10, 'fn': 0}}}]
    assert summarize(folds)['candidate']['mean_dti'] is None
