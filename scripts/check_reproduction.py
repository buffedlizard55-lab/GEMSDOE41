"""Audit cross-run raster reproducibility, including float32 CPU-dispatch drift.

Artifact SHA-256 is always exact for a specific file. Scientific cross-run
comparison additionally permits <= 8 float32 epsilons absolute error, but no
change to grid, footprint, finite-value status, or valid [0,1] range.
"""
import json
from pathlib import Path
import numpy as np
import rasterio
from download_data import sha256


def compare(expected_path, actual_path):
    with rasterio.open(expected_path) as e, rasterio.open(actual_path) as a:
        assert e.shape==a.shape and e.crs==a.crs and e.transform==a.transform
        assert np.array_equal(e.dataset_mask(),a.dataset_mask())
        x=e.read(1); y=a.read(1)
        assert np.isfinite(y).all() and 0<=y.min()<=y.max()<=1
        delta=np.abs(x.astype('float64')-y.astype('float64'))
        tolerance=8*np.finfo('float32').eps
        result={'expected_sha256':sha256(expected_path),'actual_sha256':sha256(actual_path),
                'exact_pixels':bool(np.array_equal(x,y)), 'different_pixels':int((x!=y).sum()),
                'max_absolute_error':float(delta.max()),'sum_absolute_error':float(delta.sum()),
                'absolute_tolerance':float(tolerance),'numerically_reproducible':bool(delta.max()<=tolerance)}
    print('::notice title=Cross-run raster comparison::'+json.dumps(result))
    return result

if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('expected');p.add_argument('actual');p.add_argument('--output',required=True)
    args=p.parse_args();r=compare(args.expected,args.actual)
    Path(args.output).write_text(json.dumps(r,indent=2)+'\n')
    if not r['numerically_reproducible']:raise SystemExit('Rebuilt field differs beyond fixed float32 tolerance')
