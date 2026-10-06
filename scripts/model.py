"""H41-A: structural position and independent topographic tangent agreement.

Metres throughout geometry; strikes are axial degrees clockwise from north.
Population labels are geometry proxies, NOT measured kinematics.
"""
from dataclasses import dataclass
import numpy as np
from scipy.ndimage import gaussian_filter, distance_transform_edt, binary_erosion
from shapely.geometry import Point, LineString
from shapely.strtree import STRtree
from rasterio.features import rasterize

@dataclass(frozen=True)
class Config:
    nw_strike: float = 135.0
    normal_strike: float = 10.0
    strike_tolerance: float = 30.0
    max_gap_m: float = 5000.0
    corridor_sigma_m: float = 500.0
    catalogue_exclusion_m: float = 200.0
    min_trace_m: float = 600.0
    coherence_min: float = 0.4


def axial_delta(a, b):
    return np.abs((np.asarray(a)-b+90) % 180-90)


def trace_strike(line):
    """Length-weighted axial mean of segment strikes; concentration diagnoses bends."""
    d = np.diff(np.asarray(line.coords), axis=0)
    length = np.linalg.norm(d, axis=1)
    if length.sum() == 0: return float('nan'), 0.0
    a = np.arctan2(d[:,0], d[:,1])
    z = np.sum(length*np.exp(2j*a))/length.sum()
    return float(np.degrees(np.angle(z)/2) % 180), float(abs(z))


def classify(line, cfg=Config()):
    strike, concentration = trace_strike(line)
    errors = [float(axial_delta(strike,cfg.nw_strike)),float(axial_delta(strike,cfg.normal_strike))]
    family = int(np.argmin(errors))
    eligible = bool(np.isfinite(strike) and min(errors)<=cfg.strike_tolerance and concentration>=0.4 and line.length>=cfg.min_trace_m)
    return dict(strike_deg=strike, axial_concentration=concentration, family=family,
                family_name=['NW_dextral_proxy','N_NNE_normal_proxy'][family],
                angular_error_deg=errors[family], eligible=eligible)


def burn(lines, shape, transform):
    if not lines: return np.zeros(shape,dtype=bool)
    return rasterize([(g,1) for g in lines],out_shape=shape,transform=transform,dtype='uint8').astype(bool)


def topo_orientation(elevation, valid, cfg=Config()):
    """Existing topography only; no magnetic/gravity transform or label input."""
    z = np.where(valid,elevation,0).astype('float32')
    support = gaussian_filter(valid.astype('float32'),1)
    z = gaussian_filter(z,1)/np.maximum(support,1e-6)
    gy,gx = np.gradient(z); gy = -gy  # north-positive
    a = gaussian_filter(gx*gx,2); b = gaussian_filter(gx*gy,2); c = gaussian_filter(gy*gy,2)
    coherence = np.sqrt((a-c)**2+4*b*b)/(a+c+1e-8)
    theta_normal_xy = 0.5*np.arctan2(2*b,a-c)
    strike = np.mod(-np.degrees(theta_normal_xy),180).astype('float32')
    detected = binary_erosion(valid,iterations=8) & (coherence>=cfg.coherence_min) & ((a+c)>1e-6)
    return strike, detected


def geometry_field(records, catalogue, footprint, transform, cfg=Config(), forbidden=None):
    """Construct bipartite endpoint-to-nearest-normal corridors from visible anchors.

    forbidden excludes a validation block plus halo. Entire traces touching it are
    removed by the caller. No clipping-induced endpoint is ever constructed.
    """
    shape=footprint.shape
    groups=[[r['geometry'] for r in records if r['family']==i and r['eligible']] for i in range(2)]
    # All classified mapped geometry determines which population is closer;
    # anchor-quality filters must not silently change this Voronoi assignment.
    masks=[burn([r['geometry'] for r in records if r['family']==i],shape,transform)&footprint for i in range(2)]
    distances=[distance_transform_edt(~m).astype('float32')*abs(transform.a) if m.any() else np.full(shape,np.inf,dtype='float32') for m in masks]
    corridor=np.zeros(shape,dtype='float32'); junction=np.zeros(shape,dtype=bool)
    pairs=[]
    if not groups[0] or not groups[1]: return corridor,junction,distances,pairs
    normal_tree=STRtree(groups[1])
    # Even short/ambiguous fragments can prove that an apparent endpoint is not
    # a termination. Anchor eligibility must not erase that geometric evidence.
    all_nw=[r['geometry'] for r in records if r['family']==0]
    nw_tree=STRtree(all_nw)
    boundary_distance=distance_transform_edt(footprint)*abs(transform.a)
    for i,line in enumerate(groups[0]):
        for end in [0,1]:
            tip=Point(line.coords[0 if end==0 else -1])
            col,row=(~transform)*(tip.x,tip.y); row,col=int(np.floor(row)),int(np.floor(col))
            if not (0<=row<shape[0] and 0<=col<shape[1]) or boundary_distance[row,col]<=300: continue
            # Same-family connected fragments must not be interpreted as terminations.
            neighbors=nw_tree.query(tip.buffer(200))
            if any(all_nw[j] is not line and tip.distance(all_nw[j])<=200 for j in neighbors): continue
            if forbidden is not None and forbidden[row,col]: continue
            j=int(normal_tree.nearest(tip)); receiver=groups[1][j]
            q=receiver.interpolate(receiver.project(tip)); gap=tip.distance(q)
            if not 1<=gap<=cfg.max_gap_m: continue
            inner=line.interpolate(min(500,line.length/2) if end==0 else max(0,line.length-500))
            outward=np.array([tip.x-inner.x,tip.y-inner.y]); target=np.array([q.x-tip.x,q.y-tip.y])
            facing=float(np.dot(outward,target)/(np.linalg.norm(outward)*gap+1e-10))
            if gap>200 and facing<0.5: continue
            connector=LineString([tip,q])
            # At fold edges, only original endpoints survive; corridor itself may
            # enter a held-out area, representing extrapolation from visible anchors.
            margin=3*cfg.corridor_sigma_m
            minx,miny,maxx,maxy=connector.bounds
            c0,r1=(~transform)*(minx-margin,miny-margin); c1,r0=(~transform)*(maxx+margin,maxy+margin)
            r0=max(0,int(np.floor(r0))); r1=min(shape[0],int(np.ceil(r1)))
            c0=max(0,int(np.floor(c0))); c1=min(shape[1],int(np.ceil(c1)))
            if r0>=r1 or c0>=c1: continue
            yy,xx=np.mgrid[r0:r1,c0:c1]
            x=transform.c+(xx+.5)*transform.a; y=transform.f+(yy+.5)*transform.e
            u=np.clip(((x-tip.x)*target[0]+(y-tip.y)*target[1])/gap**2,0,1)
            d=np.hypot(x-tip.x-u*target[0],y-tip.y-u*target[1])
            v=np.exp(-.5*(d/cfg.corridor_sigma_m)**2)*np.exp(-gap/cfg.max_gap_m)*(.35+.65*np.sin(np.pi*u))
            v[d>margin]=0
            corridor[r0:r1,c0:c1]=np.maximum(corridor[r0:r1,c0:c1],v)
            junction[r0:r1,c0:c1] |= (d<=750)&(u>.1)&(u<.9)
            pairs.append(dict(nw_index=i,normal_index=j,tip_x=tip.x,tip_y=tip.y,receiver_x=q.x,receiver_y=q.y,gap_m=gap,outward_cosine=facing))
    dcat=distance_transform_edt(~catalogue)*abs(transform.a) if catalogue.any() else np.full(shape,np.inf)
    corridor[~footprint | (dcat<=cfg.catalogue_exclusion_m)]=0
    junction &= footprint & (dcat>cfg.catalogue_exclusion_m)
    return corridor,junction,distances,pairs


def predict(corridor, distances, orientation, detected, cfg=Config()):
    closest=np.where(distances[0]<distances[1],cfg.nw_strike,cfg.normal_strike)
    match=np.cos(np.radians(axial_delta(orientation,closest)))**8
    # Fixed bounded normalization, no fold-specific min/max or holdout tuning.
    return np.clip(corridor*match*detected,0,1).astype('float32')
