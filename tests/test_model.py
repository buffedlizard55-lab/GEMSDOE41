import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import numpy as np
import pytest
from affine import Affine
from shapely.geometry import LineString
from model import axial_delta,trace_strike,classify,topo_orientation,geometry_field,predict
from metric import dti


def brute(p,g):
    gp=np.argwhere(g); pp=np.argwhere(p>0)
    tp=sum(max([p[tuple(x)]*max(0,1-np.linalg.norm(x-t)/3) for x in pp]+[0]) for t in gp)
    fp=sum(p[tuple(x)]*(1-max([max(0,1-np.linalg.norm(x-t)/3) for t in gp]+[0])) for x in pp)
    fn=len(gp)-tp
    return tp/(tp+.2*fp+.8*fn+1e-12)


def test_axial_wrap_and_reverse():
    assert axial_delta(179,1)==2
    line=LineString([(0,0),(-100,100)])
    assert trace_strike(line)[0]==pytest.approx(135)
    assert trace_strike(LineString(list(line.coords)[::-1]))[0]==pytest.approx(135)
    assert classify(LineString([(0,0),(100,1000)]))['family']==1
    assert not classify(LineString([(0,0),(1000,0)]))['eligible']


@pytest.mark.parametrize('seed',range(6))
def test_metric_matches_brute_force(seed):
    rng=np.random.default_rng(seed);p=rng.random((7,8)).astype('float32');p[p<.6]=0
    g=rng.random((7,8))>.8
    assert dti(p,g)['dti']==pytest.approx(brute(p,g),abs=1e-7)


def test_metric_edges():
    p=np.zeros((7,7),dtype='float32');g=p.astype(bool);g[3,3]=True
    p[3,3]=1; assert dti(p,g)['dti']==pytest.approx(1)
    p[3,3]=0;p[3,4]=1;assert dti(p,g)['tp']==pytest.approx(2/3)
    p[:]=0;p[0,3]=1;assert dti(p,g)['tp']==0
    assert dti(p,np.zeros_like(g))['dti']==0
    with pytest.raises(ValueError): dti(p*2,g)
    with pytest.raises(ValueError): dti(np.full_like(p,np.nan),g)


def test_topographic_strike_coordinate_convention():
    y,x=np.mgrid[:100,:100]
    # Elevation varies east-west => north-striking contour / tangent.
    a,ok=topo_orientation(x.astype('float32'),np.ones(x.shape,bool))
    assert ok[50,50] and axial_delta(a[50,50],0)<1e-4
    a,ok=topo_orientation(y.astype('float32'),np.ones(x.shape,bool))
    assert ok[50,50] and axial_delta(a[50,50],90)<1e-4
    _,ok=topo_orientation(np.zeros_like(x,dtype='float32'),np.ones(x.shape,bool))
    assert not ok.any()


def test_bimodal_corridor_nonzero_off_catalogue():
    transform=Affine(100,0,0,0,-100,10000);foot=np.ones((100,100),bool)
    nw=LineString([(7000,3000),(4500,5500)])
    normal=LineString([(3000,5000),(3000,8500)])
    records=[dict(geometry=g,**classify(g)) for g in [nw,normal]]
    from model import burn
    labels=burn([nw,normal],foot.shape,transform)
    c,j,d,pairs=geometry_field(records,labels,foot,transform)
    assert pairs and c.max()>0 and j.any()
    assert not c[labels].any()
    orientation=np.where(d[0]<d[1],135,10)
    p=predict(c,d,orientation,np.ones_like(foot))
    assert np.isfinite(p).all() and 0<p.max()<=1
    assert np.allclose(p,c)


def test_absent_population_has_no_corridor():
    foot=np.ones((20,20),bool);g=LineString([(0,0),(1000,1000)])
    c,j,_,pairs=geometry_field([dict(geometry=g,**classify(g))],np.zeros_like(foot),foot,Affine(100,0,0,0,-100,2000))
    assert not c.any() and not j.any() and not pairs


def test_complete_source_removal():
    from run_pipeline import drop_heldout_traces
    records=[dict(source_id='one',sample_r=np.array([4]),sample_c=np.array([4])),
             dict(source_id='one',sample_r=np.array([1]),sample_c=np.array([1])),
             dict(source_id='two',sample_r=np.array([0]),sample_c=np.array([0]))]
    mask=np.zeros((5,5),bool);mask[4,4]=True
    kept,n=drop_heldout_traces(records,mask)
    assert n==1 and [r['source_id'] for r in kept]==['two']
