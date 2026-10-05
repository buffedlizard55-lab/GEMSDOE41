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
    import json
    root=Path(__file__).resolve().parents[1]
    manifest=root/'docs/downloads/manifest.json'
    if not manifest.exists():pytest.skip('pipeline not run yet')
    m=json.loads(manifest.read_text());path=root/'docs/downloads'/m['filename']
    with rasterio.open(path) as s:
        a=s.read(1)
        assert s.count==1 and s.dtypes==('float32',) and s.shape==(3730,3292)
        assert s.crs.to_epsg()==32611 and s.nodata is None
        assert np.isfinite(a).all() and 0<=a.min()<a.max()<=1
        assert not a[s.dataset_mask()==0].any()
    import hashlib
    assert hashlib.sha256(path.read_bytes()).hexdigest()==m['format']['sha256']
    assert hashlib.sha256(a.astype('<f4').tobytes()).hexdigest()==m['format']['array_sha256']
