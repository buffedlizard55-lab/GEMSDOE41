"""Independent disk re-read; reject out-of-range data rather than silently repair it."""
import argparse
import hashlib
import json
import numpy as np
import rasterio


def validate(path, template, output=None):
    with rasterio.open(template) as ref, rasterio.open(path) as src:
        assert src.count==1, 'single band required'
        assert src.dtypes==('float32',), 'float32 required'
        assert src.crs==ref.crs and src.crs.to_epsg()==32611, 'CRS mismatch'
        assert src.shape==ref.shape, 'shape mismatch'
        assert src.transform==ref.transform and src.bounds==ref.bounds, 'grid mismatch'
        a=src.read(1); valid=np.isfinite(ref.read(1))
        assert np.isfinite(a).all(), 'non-finite pixel'
        assert 0<=a.min()<=a.max()<=1, 'Predicted values must be in range [0, 1]'
        assert src.nodata is None, 'no sentinel nodata tag allowed in finite export'
        assert np.all(a[~valid]==0), 'outside-footprint cells must be zero'
        # Internal dataset mask supplies null outside the template footprint while
        # underlying numeric values remain finite, avoiding sentinel range errors.
        assert np.array_equal(src.dataset_mask()>0,valid), 'footprint mask mismatch'
        result=dict(file=str(path),sha256=hashlib.sha256(open(path,'rb').read()).hexdigest(),
                    array_sha256=hashlib.sha256(a.astype('<f4').tobytes()).hexdigest(),
                    shape=list(src.shape),crs=str(src.crs),transform=list(src.transform),
                    bands=src.count,dtype=src.dtypes[0],min=float(a.min()),max=float(a.max()),
                    positive_pixels=int((a>0).sum()),prediction_mass=float(a.sum(dtype='float64')),
                    finite_cells=int(np.isfinite(a).sum()),footprint_cells=int(valid.sum()),
                    nodata=src.nodata,internal_mask=True,all_checks_passed=True)
    if output:
        with open(output,'w') as f: json.dump(result,f,indent=2); f.write('\n')
    return result

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('path');p.add_argument('--template',default='data/sample_submission.tif');p.add_argument('--output')
    args=p.parse_args();print(json.dumps(validate(args.path,args.template,args.output),indent=2))
