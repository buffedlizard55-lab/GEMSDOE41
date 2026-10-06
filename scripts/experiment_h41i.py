"""Preregistered H41-I audits, fresh full-region build, and independent export check.

Run from any cwd: .venv/bin/python scripts/experiment_h41i.py
No competition access. Historical predictions are opened only after construction.
"""
import gc
import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np
import rasterio
from rasterio.features import shapes
from scipy.ndimage import distance_transform_edt, gaussian_filter
from shapely import union_all
from shapely.geometry import Point, shape
from shapely.strtree import STRtree

from local_strike import local_prediction
from metric import dti
from model import burn, geometry_field, predict, topo_orientation
from run_pipeline import ROOT, drop_heldout_traces, load_inputs, load_vectors
from validate_submission import validate

OUT = ROOT / 'docs/evidence/h41i'


def sha(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False) + '\n')


def match_mass(field, evaluation, mass):
    """Bounded scalar calibration to a prediction-only budget, never truth values."""
    a = np.where(evaluation, field, 0).astype(np.float32)
    values = a[evaluation]
    capacity = int((values > 0).sum())
    target = min(float(mass), capacity)
    if target <= 0:
        return np.zeros_like(a)
    lo, hi = 0., 1.
    while np.minimum(values * hi, 1).sum(dtype=np.float64) < target and hi < 1e30:
        hi *= 2
    for _ in range(55):
        middle = (lo + hi) / 2
        if np.minimum(values * middle, 1).sum(dtype=np.float64) < target:
            lo = middle
        else:
            hi = middle
    return np.clip(a * hi, 0, 1).astype(np.float32)


def conditional_targets(records, transform, grid_shape):
    """Source-level selection; called only by validation, never prediction.

    Short sources near both other-source families. Selection is label-conditioned
    and explicitly not an unbiased test population.
    """
    grouped = defaultdict(list)
    for rec in records:
        grouped[rec['source_id']].append(rec)
    families = [[r for r in records if r['eligible'] and r['family'] == family] for family in (0, 1)]
    trees = [STRtree([r['geometry'] for r in group]) for group in families]
    targets = {}
    for source, parts in grouped.items():
        length = sum(r['geometry'].length for r in parts)
        if length > 10000:
            continue
        x = sum(r['geometry'].centroid.x * r['geometry'].length for r in parts) / length
        y = sum(r['geometry'].centroid.y * r['geometry'].length for r in parts) / length
        point = Point(x, y)
        available = []
        for group, tree in zip(families, trees):
            available.append(any(group[j]['source_id'] != source and point.distance(group[j]['geometry']) <= 5000
                                 for j in tree.query(point.buffer(5000))))
        if not all(available):
            continue
        col, row = (~transform) @ (x, y)
        fold = int(row >= grid_shape[0] / 2) * 2 + int(col >= grid_shape[1] / 2)
        targets[source] = {'fold': fold, 'length_m': length, 'centroid_x': x, 'centroid_y': y}
    return targets


def summarize(folds):
    models = list(folds[0]['models'])
    summary = {}
    for name in models:
        values = [f['models'][name] for f in folds if f['models'][name]['truth_pixels'] > 0]
        tp, fp, fn = (sum(v[key] for v in values) for key in ('tp', 'fp', 'fn'))
        summary[name] = {'mean_dti': float(np.mean([v['dti'] for v in values])) if values else None,
                         'pooled_dti': tp / (tp + .2 * fp + .8 * fn) if tp + fp + fn else None,
                         'evaluable_folds': len(values)}
    return summary


def evaluate(records, footprint, labels, transform, orientation, detected, protocol):
    rr, cc = np.indices(footprint.shape, sparse=True)
    fold_map = ((rr // 200) + 2 * (cc // 200)) % 4 if protocol == 'strict' else (
        (rr >= footprint.shape[0] / 2).astype(int) * 2 + (cc >= footprint.shape[1] / 2).astype(int))
    targets = conditional_targets(records, transform, footprint.shape) if protocol == 'conditional' else {}
    folds = []
    for fold in range(4):
        print(protocol, 'fold', fold, flush=True)
        held = (fold_map == fold) & footprint
        evaluation = held & (distance_transform_edt(held) > 3)
        extra = {}
        forbidden = None
        if protocol == 'strict':
            forbidden = distance_transform_edt(~held) <= 3
            polygons = [shape(g) for g, v in shapes(held.astype('uint8'), mask=held, transform=transform) if v == 1]
            anchors, removed = drop_heldout_traces(records, forbidden, union_all(polygons).buffer(300, quad_segs=32))
            training = labels & ~forbidden
            truth = labels
        else:
            withheld = {k for k, v in targets.items() if v['fold'] == fold}
            anchors = [r for r in records if r['source_id'] not in withheld]
            assert not withheld.intersection(r['source_id'] for r in anchors)
            removed = len(withheld)
            # Reconstruct ONLY from visible source geometry, no full-catalogue mask.
            training = burn([r['geometry'] for r in anchors], footprint.shape, transform) & footprint
            truth = burn([r['geometry'] for r in records if r['source_id'] in withheld], footprint.shape, transform) & footprint
            dtrain = distance_transform_edt(~training) * 100 if training.any() else np.full(footprint.shape, np.inf)
            before = truth & evaluation
            extra = {'withheld_source_ids': sorted(withheld),
                     'truth_before_training_exclusion': int(before.sum()),
                     'truth_within_300m_of_training': int((before & (dtrain <= 300)).sum())}
            evaluation &= dtrain > 200
            del before, dtrain
        corridor, junction, distances, pairs = geometry_field(anchors, training, footprint, transform, forbidden=forbidden)
        candidate, stats = local_prediction(anchors, corridor, distances, orientation, detected, transform)
        baseline = predict(corridor, distances, orientation, detected)
        mass = float(candidate[evaluation].sum(dtype=np.float64))
        models = {}
        for name, field in [('H41-I', candidate), ('H41-A', baseline), ('geometry_only', corridor)]:
            models[name] = {**dti(field, truth, evaluation), 'prediction_mass': float(field[evaluation].sum(dtype=np.float64)),
                            'positive_pixels': int((field[evaluation] > 0).sum())}
        for name, field in [('H41-A_matched', baseline), ('geometry_only_matched', corridor)]:
            matched = match_mass(field, evaluation, mass)
            actual = float(matched[evaluation].sum(dtype=np.float64))
            models[name] = {**dti(matched, truth, evaluation), 'prediction_mass': actual,
                            'positive_pixels': int((matched[evaluation] > 0).sum()),
                            'mass_matched': abs(actual - mass) <= max(1e-7, mass * 1e-6)}
        del baseline, candidate, corridor, junction, distances, matched
        dtrain = distance_transform_edt(~training) * 100 if training.any() else np.full(footprint.shape, np.inf)
        control_domain = evaluation & (dtrain > 200)
        del dtrain
        density = gaussian_filter(training.astype(np.float32), 10)
        for name, field in [('catalogue_density', density), ('topography_only', detected.astype(np.float32))]:
            field = match_mass(field, control_domain, mass)
            actual = float(field[evaluation].sum(dtype=np.float64))
            models[name] = {**dti(field, truth, evaluation), 'prediction_mass': actual,
                            'positive_pixels': int((field[evaluation] > 0).sum()),
                            'mass_matched': abs(actual - mass) <= max(1e-7, mass * 1e-6)}
        folds.append({'fold': fold, 'removed_sources': removed, 'visible_parts': len(anchors),
                      'evaluation_pixels': int(evaluation.sum()), 'corridors': len(pairs),
                      'tangent_audit': stats, 'models': models, **extra})
        del density, training, truth, field, held, evaluation, control_domain, forbidden
        gc.collect()
    controls = ('H41-A_matched', 'catalogue_density', 'topography_only')
    passed = all(f['models']['H41-I']['truth_pixels'] > 0 and f['models']['H41-I']['prediction_mass'] > 0
                 and all(f['models']['H41-I']['dti'] > f['models'][control]['dti']
                         and f['models'][control]['prediction_mass'] > 0 for control in controls)
                 and all(f['models'][control]['mass_matched'] for control in controls) for f in folds)
    return {'protocol': protocol, 'folds': folds, 'summary': summarize(folds), 'targets': targets,
            'proxy_gate_passed': passed, 'clean_historical_best_oof_available': False, 'slot_eligible': False,
            'limitations': 'Catalogue reconstruction only. Strict folds reused as negative audit. Conditional audit selects short known sources near both families and retains observed context inside test quadrants; not independent geographic extrapolation or hidden-fault validation.'}


def concentration_audit(prediction, junction, records, catalogue, footprint, transform):
    dcat = distance_transform_edt(~catalogue) * 100
    eligible = footprint & (dcat > 200)
    total = float(prediction.sum(dtype=np.float64))
    if total <= 0:
        raise ValueError('No full-region prediction mass; do not publish empty candidate')
    fraction = float(prediction[junction].sum(dtype=np.float64) / total)
    positive = prediction > 0
    top = positive & (prediction >= np.quantile(prediction[positive], .95))
    controls = {}
    for family in (0, 1):
        den = gaussian_filter(burn([r['geometry'] for r in records if r['family'] == family], footprint.shape, transform).astype(np.float32), 10)
        den[~eligible] = 0
        denominator = float(den.sum(dtype=np.float64))
        frac = float(den[junction].sum(dtype=np.float64) / denominator) if denominator else 0.
        controls[str(family)] = {'junction_mass_fraction': frac,
                                'enrichment': fraction / frac if frac else None}
    inside = int((positive & (dcat <= 200)).sum())
    top_fraction = float(junction[top].mean())
    passed = inside == 0 and top_fraction > .5 and all(fraction > v['junction_mass_fraction'] for v in controls.values())
    return {'junction_mass_fraction': fraction, 'top5percent_positive_at_junction_fraction': top_fraction,
            'positive_pixels_within_200m_catalogue': inside, 'family_density_controls': controls,
            'junction_area_fraction_off_catalogue': float(junction[eligible].mean()),
            'passed': passed, 'meaning': 'Construction diagnostic, not independent fault or geothermal truth.'}


def novelty(prediction, footprint, profile):
    comparisons = []
    paths = sorted((ROOT / 'docs/downloads').glob('*.tif')) + [ROOT / 'data/comparison-h33.tif']
    for path in paths:
        # Ignore only earlier reproducible exports of this SAME candidate on reruns.
        if path.name.startswith('gems41-h41i-local-strike-'):
            continue
        with rasterio.open(path) as src:
            if src.shape != prediction.shape or src.crs != profile['crs'] or src.transform != profile['transform']:
                raise ValueError(f'Comparison grid mismatch: {path}')
            reference = src.read(1)
        different = int(np.count_nonzero(prediction[footprint] != reference[footprint]))
        p = (prediction > 0) & footprint
        q = (reference > 0) & footprint
        union = int((p | q).sum())
        comparisons.append({'file': str(path.relative_to(ROOT)), 'sha256': sha(path),
                            'different_valid_pixels': different, 'equal_arrays': different == 0,
                            'support_jaccard': float((p & q).sum() / union) if union else 1.})
    if any(c['equal_arrays'] for c in comparisons):
        raise ValueError('Candidate duplicates an available prior field')
    return {'comparisons': comparisons, 'passed': True,
            'scope': 'Every other checked-in download TIFF plus pinned H33. Predictions were compared only after fresh construction. Not global proof against unavailable files.'}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    footprint, profile, labels, elevation, valid = load_inputs()
    records = load_vectors(profile, footprint)
    orientation, detected = topo_orientation(elevation, valid)
    del elevation, valid
    for protocol in ('strict', 'conditional'):
        result = evaluate(records, footprint, labels, profile['transform'], orientation, detected, protocol)
        write_json(OUT / f'{protocol}-holdout.json', result)
        print(protocol, result['summary'], 'gate:', result['proxy_gate_passed'], flush=True)
    corridor, junction, distances, pairs = geometry_field(records, labels, footprint, profile['transform'])
    prediction, tangent = local_prediction(records, corridor, distances, orientation, detected, profile['transform'])
    del corridor, distances, orientation, detected
    audit = concentration_audit(prediction, junction, records, labels, footprint, profile['transform'])
    if not audit['passed']:
        write_json(OUT / 'failed-concentration.json', audit)
        raise ValueError('Failed concentration gate; no download published')
    comparison = novelty(prediction, footprint, profile)
    digest = hashlib.sha256(prediction.astype('<f4').tobytes()).hexdigest()[:12]
    filename = f'gems41-h41i-local-strike-20261006-{digest}.tif'
    dest = ROOT / 'docs/downloads' / filename
    profile.update(driver='GTiff', dtype='float32', count=1, nodata=None, compress='deflate', predictor=3,
                   tiled=True, blockxsize=256, blockysize=256)
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(dest, 'w', **profile) as src:
            src.write(prediction, 1)
            src.write_mask(footprint.astype('uint8') * 255)
            src.set_band_description(1, 'H41-I local-strike transfer confidence; uncalibrated; research only')
            src.update_tags(model='H41-I', status='RESEARCH_ONLY_GATE_CLOSED', prior_prediction_input='none')
    receipt = validate(dest, ROOT / 'data/sample_submission.tif')
    receipt['file'] = str(dest.relative_to(ROOT))
    with rasterio.open(dest) as src:
        if len(src.files) != 1:
            raise ValueError('Submission must be self-contained (no mask sidecar)')
    result = {'hypothesis_id': 'H41-I', 'filename': filename, 'submission_name': f'GEMS41-H41I-LocalStrike-{digest}',
              'note': 'H41-I local-strike transfer; raw mapped NW endpoints to N/NNE receivers; det_elev tangent; >200m off catalogue. Research only; holdout gate closed; unscored.',
              'slot_eligible': False, 'format': receipt, 'concentration': audit, 'novelty': comparison,
              'tangent': tangent, 'corridors': len(pairs), 'trace_parts': len(records),
              'inputs': {str(p.relative_to(ROOT)): sha(p) for p in [ROOT/'data/official/qfaults.zip', ROOT/'data/training_features.tif', ROOT/'data/existing_faults.tif', ROOT/'data/sample_submission.tif']},
              'code': {str(p.relative_to(ROOT)): sha(p) for p in [Path(__file__), ROOT/'scripts/local_strike.py', ROOT/'scripts/model.py', ROOT/'scripts/metric.py', ROOT/'scripts/run_pipeline.py', ROOT/'scripts/validate_submission.py', ROOT/'research/hypotheses-20261006.md']}}
    write_json(OUT / 'manifest.json', result)
    print(json.dumps({'filename': filename, 'format': receipt, 'concentration': audit}, indent=2), flush=True)


if __name__ == '__main__':
    main()
