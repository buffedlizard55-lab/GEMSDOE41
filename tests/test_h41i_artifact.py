"""Release gates run in CI without downloading the large feature rasters."""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import rasterio

ROOT = Path(__file__).resolve().parents[1]


def test_h41i_actual_bytes_grid_mask_range_and_identity():
    m = json.loads((ROOT / 'docs/evidence/h41i/manifest.json').read_text())
    path = ROOT / 'docs/downloads' / m['filename']
    assert hashlib.sha256(path.read_bytes()).hexdigest() == m['format']['sha256']
    old = json.loads((ROOT / 'docs/downloads/manifest.json').read_text())
    with rasterio.open(path) as src, rasterio.open(ROOT / 'docs/downloads' / old['filename']) as ref:
        a, b = src.read(1), ref.read(1)
        assert src.count == 1 and src.dtypes == ('float32',)
        assert src.shape == (3730, 3292) and src.crs.to_epsg() == 32611
        assert (src.shape, src.transform, src.crs) == (ref.shape, ref.transform, ref.crs)
        assert src.nodata is None and len(src.files) == 1
        assert np.isfinite(a).all() and 0 <= a.min() < a.max() <= 1
        assert np.array_equal(src.dataset_mask(), ref.dataset_mask())
        assert not a[src.dataset_mask() == 0].any()
        assert not np.array_equal(a, b)
        # Local orientation changes confidence, NOT the geographic support.
        assert np.array_equal(a > 0, b > 0)
        assert hashlib.sha256(a.astype('<f4').tobytes()).hexdigest() == m['format']['array_sha256']
    assert not m['slot_eligible'] and len(m['note']) <= 200
    assert m['concentration']['passed'] and m['novelty']['passed']
    assert all(not c['equal_arrays'] for c in m['novelty']['comparisons'])
    for name, digest in m['code'].items():
        assert hashlib.sha256((ROOT / name).read_bytes()).hexdigest() == digest, name


def test_conditional_fold_aggregation_and_closed_gate():
    j = json.loads((ROOT / 'docs/evidence/h41i/conditional-holdout.json').read_text())
    assert len(j['folds']) == 4 and not j['slot_eligible']
    assert not j['proxy_gate_passed'] and not j['clean_historical_best_oof_available']
    for name, summary in j['summary'].items():
        values = [f['models'][name] for f in j['folds']]
        tp, fp, fn = (sum(v[k] for v in values) for k in ('tp', 'fp', 'fn'))
        assert np.isclose(summary['pooled_dti'], tp / (tp + .2 * fp + .8 * fn))
        assert np.isclose(summary['mean_dti'], np.mean([v['dti'] for v in values]))
    seen = set()
    for f in j['folds']:
        ids = set(f['withheld_source_ids'])
        assert not ids.intersection(seen)
        seen.update(ids)
        assert all(j['targets'][i]['fold'] == f['fold'] for i in ids)
        for name in ('H41-A_matched', 'geometry_only_matched', 'catalogue_density', 'topography_only'):
            assert f['models'][name]['mass_matched']
    assert seen == set(j['targets'])


def test_new_download_first_and_gate_visible():
    m = json.loads((ROOT / 'docs/evidence/h41i/manifest.json').read_text())
    for page in ('index.html', 'executive-summary.html', 'h41i-executive-summary.html'):
        s = (ROOT / 'docs' / page).read_text()
        assert m['filename'] in s and 'holdout gate CLOSED' in s
        assert s.index(m['filename']) < s.index('</main>')
    s = (ROOT / 'docs/h41i-executive-summary.html').read_text()
    assert m['note'].replace('>', '&gt;') in s
    assert m['format']['sha256'] in s and 'same nonzero support' in s


def test_format_guards_survive_python_optimization():
    script = "from validate_submission import require; require(False, 'range guard active')"
    run = subprocess.run([sys.executable, '-O', '-c', script], cwd=ROOT / 'scripts', capture_output=True, text=True)
    assert run.returncode != 0 and 'range guard active' in run.stderr
