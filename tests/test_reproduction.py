import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import rasterio
from affine import Affine
from check_reproduction import compare


def test_float32_tolerance_is_bounded_and_support_drift_is_reported(tmp_path):
    profile=dict(driver='GTiff',width=3,height=3,count=1,dtype='float32',crs='EPSG:32611',transform=Affine(100,0,243350,0,-100,4508550))
    a=np.full((3,3),.5,dtype='float32');e=tmp_path/'e.tif';p=tmp_path/'p.tif'
    def write(path,array,**kwargs):
        with rasterio.open(path,'w',**profile,**kwargs) as s:s.write(array,1)
    write(e,a);write(p,a)
    assert compare(e,p)['exact_pixels']

    eps=np.finfo('float32').eps
    a[1,1]=np.float32(.5+64*eps);write(p,a)
    r=compare(e,p)
    assert not r['exact_pixels'] and r['numerically_reproducible']
    assert r['tolerance_float32_epsilons']==64
    assert r['nonzero_support_exact'] and r['nonzero_support_changed_pixels']==0

    a[1,1]=np.float32(.5+65*eps);write(p,a)
    assert not compare(e,p)['numerically_reproducible']

    a[1,1]=0;write(p,a)
    r=compare(e,p)
    assert not r['nonzero_support_exact']
    assert r['nonzero_support_changed_pixels']==1

    a[1,1]=.51;write(p,a)
    assert not compare(e,p)['numerically_reproducible']


def test_nan_outside_footprint_is_supported_and_preserved(tmp_path):
    profile=dict(
        driver='GTiff',width=3,height=3,count=1,dtype='float32',crs='EPSG:32611',
        transform=Affine(100,0,243350,0,-100,4508550),nodata=np.nan,
    )
    values=np.full((3,3),np.nan,dtype='float32')
    values[1:,1:]=0.25
    expected=tmp_path/'expected-nan.tif';actual=tmp_path/'actual-nan.tif'
    for path in (expected,actual):
        with rasterio.open(path,'w',**profile) as dataset:
            dataset.write(values,1)

    result=compare(expected,actual)
    assert result['exact_pixels']
    assert result['outside_values_exact']
    assert result['outside_expected_all_nan']
    assert result['outside_actual_all_nan']
    assert result['numerically_reproducible']
