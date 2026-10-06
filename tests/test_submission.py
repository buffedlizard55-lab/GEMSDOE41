import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import rasterio
from rasterio.transform import from_origin
import pytest
from validate_submission import validate


def test_roundtrip_and_range_rejection(tmp_path):
    profile=dict(driver='GTiff',width=10,height=10,count=1,dtype='float32',crs='EPSG:32611',transform=from_origin(100,2000,100,100))
    template=tmp_path/'template.tif';p=tmp_path/'p.tif'
    a=np.zeros((10,10),dtype='float32');a[0]=np.nan
    with rasterio.open(template,'w',nodata=np.nan,**profile) as s:s.write(a,1)
    a=np.nan_to_num(a);a[3,4]=.7
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(p,'w',**profile) as s:
            s.write(a,1);m=np.ones((10,10),dtype='uint8')*255;m[0]=0;s.write_mask(m)
    assert validate(p,template)['all_checks_passed']
    with rasterio.open(p,'r+') as s:a[3,4]=1.1;s.write(a,1)
    with pytest.raises(AssertionError,match='range'):validate(p,template)


def test_published_artifact_when_available():
    """The published primary must be scoreable by a naive `[0, 1]` range test.

    H42 ships two declared encodings: an ALL-FINITE primary (zeros outside the footprint, no NaN to
    trip a range check) and a NaN-outside twin matching the task's null convention.  This test
    pins the primary's guarantees and checks that the twin differs from it only outside the
    footprint.
    """
    import json, hashlib
    root=Path(__file__).resolve().parents[1]
    manifest=root/'docs/downloads/manifest.json'
    if not manifest.exists():pytest.skip('pipeline not run yet')
    m=json.loads(manifest.read_text());path=root/'docs/downloads'/m['filename']
    with rasterio.open(path) as s:
        a=s.read(1)
        assert s.count==1 and s.dtypes==('float32',) and s.shape==(3730,3292)
        assert s.crs.to_epsg()==32611
        assert s.nodata in (None,0.0)
        assert np.isfinite(a).all() and 0<=a.min()<a.max()<=1
        assert not a[s.dataset_mask()==0].any()
    assert hashlib.sha256(path.read_bytes()).hexdigest()==m['format']['sha256']
    twin_name=m.get('also_downloadable',{}).get('nan_outside_variant')
    if twin_name:
        # the manifest stores the site-relative form ("downloads/<name>") for the Pages links
        twin=(root/'docs'/twin_name) if twin_name.startswith('downloads/') else (root/twin_name)
        assert twin.exists(), twin
        with rasterio.open(twin) as ts:
            b=ts.read(1)
            assert ts.count==1 and ts.shape==(3730,3292) and ts.crs.to_epsg()==32611
            foot=np.isfinite(b)
            assert foot.any() and (~foot).any(), "the twin must be a genuine null-outside file"
            # same predictions inside the footprint ...
            assert np.array_equal(b[foot], a[foot])
            # ... the primary carries zeros exactly where the twin carries NaN ...
            assert (a[~foot]==0).all()
            # ... and the primary itself has no NaN at all.
            assert np.isfinite(a).all()
