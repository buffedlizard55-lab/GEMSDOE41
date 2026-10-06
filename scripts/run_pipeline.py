"""Reproducible CPU-only H41-A build, blocked evaluation, audit, and GeoTIFF export."""
import csv
import gc
import hashlib
import json
from dataclasses import asdict
from pathlib import Path
import fiona
from fiona.transform import transform_geom
import numpy as np
import rasterio
from scipy.ndimage import distance_transform_edt, gaussian_filter
from shapely.geometry import shape, box, mapping, LineString
from shapely import union_all
from rasterio.features import shapes
from model import Config, classify, topo_orientation, geometry_field, predict, burn
from metric import dti
from validate_submission import validate

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'docs/downloads'


def load_inputs():
    with rasterio.open(ROOT/'data/sample_submission.tif') as s:
        footprint=np.isfinite(s.read(1)); profile=s.profile.copy(); transform=s.transform
    with rasterio.open(ROOT/'data/existing_faults.tif') as s:
        assert s.shape==footprint.shape and s.transform==transform
        labels=(s.read(1)==1)&footprint
    with rasterio.open(ROOT/'data/training_features.tif') as s:
        assert s.shape==footprint.shape and s.transform==transform
        assert s.descriptions[11].startswith('det_elev -')
        z=s.read(12); valid=np.isfinite(z)&(z!=s.nodata)&footprint
    return footprint,profile,labels,z,valid


def load_vectors(profile, footprint):
    archive=ROOT/'data/official/qfaults.zip'
    bbox=box(*rasterio.transform.array_bounds(*footprint.shape,profile['transform']))
    records=[]
    with fiona.open('zip://'+str(archive)) as src:
        for f in src:
            g=shape(transform_geom(src.crs,'EPSG:32611',f['geometry']))
            if not g.intersects(bbox): continue
            parts=list(g.geoms) if g.geom_type=='MultiLineString' else [g]
            for part_id,line in enumerate(parts):
                if line.geom_type!='LineString' or line.length==0: continue
                # Do not clip source geometry and manufacture terminations.
                t=np.linspace(0,line.length,max(2,int(np.ceil(line.length/50))+1))
                xy=np.array([(line.interpolate(v).x,line.interpolate(v).y) for v in t])
                cols=(xy[:,0]-profile['transform'].c)/profile['transform'].a; rows=(xy[:,1]-profile['transform'].f)/profile['transform'].e
                rr=np.floor(rows).astype(int); cc=np.floor(cols).astype(int)
                inside=(rr>=0)&(rr<footprint.shape[0])&(cc>=0)&(cc<footprint.shape[1])
                rr,cc=rr[inside],cc[inside]
                if not len(rr) or not footprint[rr,cc].any(): continue
                props=dict(f['properties'])
                records.append(dict(source_id=str(f['id']),part_id=part_id,geometry=line,
                                    sample_r=rr,sample_c=cc,source_properties=props,
                                    length_m=line.length,**classify(line)))
    with (OUT/'classified-traces.csv').open('w') as f:
        fields=['source_id','part_id','length_m','strike_deg','axial_concentration','family_name','angular_error_deg','eligible','source_properties']
        w=csv.DictWriter(f,fieldnames=fields,lineterminator="\n");w.writeheader()
        for rec in records:
            row={k:rec[k] for k in fields};row['source_properties']=json.dumps(row['source_properties'],sort_keys=True);w.writerow(row)
    return records


def drop_heldout_traces(records, forbidden, exclusion_geometry=None):
    if exclusion_geometry is None:
        excluded={r['source_id'] for r in records if forbidden[r['sample_r'],r['sample_c']].any()}
    else:
        # Exact intersection, not sampled vertices: narrow corner crossings count.
        excluded={r['source_id'] for r in records if r['geometry'].intersects(exclusion_geometry)}
    return [r for r in records if r['source_id'] not in excluded],len(excluded)


def evaluate(records, footprint, labels, transform, orientation, detected):
    rr,cc=np.indices(footprint.shape,sparse=True)
    # Deterministic 20 km blocks, four-color blocked CV. No random pixel split.
    fold_id=((rr//200)+2*(cc//200))%4
    with rasterio.open(ROOT/'data/comparison-h33.tif') as s: historical=s.read(1)
    folds=[]
    for fold in range(4):
        print('Evaluate spatial fold',fold,flush=True)
        held=(fold_id==fold)&footprint
        forbidden=distance_transform_edt(~held)<=3
        training=labels&~forbidden
        polygons=[shape(g) for g,v in shapes(held.astype('uint8'),mask=held,transform=transform) if v==1]
        exclusion_geometry=union_all(polygons).buffer(300,quad_segs=32)
        anchors,nremoved=drop_heldout_traces(records,forbidden,exclusion_geometry)
        # Interior scoring prevents kernel edge effects; Euclidean, not Manhattan,
        # distances match the published 300 m support.
        evaluation=held & (distance_transform_edt(held)>3)
        corridor,junction,distances,pairs=geometry_field(anchors,training,footprint,transform,forbidden=forbidden)
        candidate=predict(corridor,distances,orientation,detected)
        results={'candidate':dti(candidate,labels,evaluation),'geometry_only':dti(corridor,labels,evaluation)}
        d=distance_transform_edt(~training)*100
        density=gaussian_filter(training.astype('float32'),10)
        if density.max()>0: density/=density.max()
        density[~footprint | (d<=200)]=0
        # Match prediction mass within evaluation for the controls, without looking
        # at ground truth values; cap probabilities at one, report actual mass.
        mass=float(candidate[evaluation].sum(dtype='float64'))
        for name,a in [('catalogue_density',density),('topography_only',detected.astype('float32'))]:
            a[~footprint | (d<=200)]=0
            denom=float(a[evaluation].sum(dtype='float64'))
            a=np.clip(a*(mass/denom if denom else 0),0,1)
            results[name]=dti(a,labels,evaluation)
            results[name]['prediction_mass']=float(a[evaluation].sum(dtype='float64'))
        results['historical_h33_CONTAMINATED']=dti(historical,labels,evaluation)
        folds.append(dict(fold=fold,validation_cells=int(evaluation.sum()),training_label_pixels=int(training.sum()),
                          source_ids_removed=nremoved,anchor_parts=len(anchors),corridors=len(pairs),prediction_mass=mass,metrics=results))
        del corridor,junction,distances,candidate,density,d,evaluation,held,forbidden,training
        gc.collect()
    means={name:float(np.mean([f['metrics'][name]['dti'] for f in folds])) for name in folds[0]['metrics']}
    wins={name:sum(f['metrics']['candidate']['dti']>f['metrics'][name]['dti'] for f in folds) for name in means if name!='candidate'}
    return dict(design='20km four-color blocks; remove complete source traces touching heldout+300m; score 300m eroded interiors; fixed settings',
                fold_formula='(row//200 + 2*(col//200)) % 4',folds=folds,means=means,wins_of_four=wins,
                slot_eligible=False,clean_historical_best_available=False,
                gate_reason='No clean historical-best out-of-fold predictions available. Historical H33 uses the full catalogue and is not a valid clean comparator. Gate stays closed regardless of proxy results.',
                limitations='Visible-catalogue reconstruction is not expert hidden-fault ground truth. Whole-trace withholding may remove true transfer anchors and severely depress this geometry-only model.')


def correlation(a,b,mask):
    # Deterministic sparse sample reduces memory; this is diagnostic, not a score.
    x=a[::4,::4][mask[::4,::4]]; y=b[::4,::4][mask[::4,::4]]
    if not len(x) or x.std()==0 or y.std()==0: return None
    return float(np.corrcoef(x,y)[0,1])


def main():
    OUT.mkdir(parents=True,exist_ok=True)
    cfg=Config(); footprint,profile,labels,z,valid=load_inputs(); transform=profile['transform']
    print('Read official full vector geometry',flush=True)
    records=load_vectors(profile,footprint)
    orientation,detected=topo_orientation(z,valid);del z,valid
    print('Trace parts',len(records),'eligible',sum(r['eligible'] for r in records),flush=True)
    cv=evaluate(records,footprint,labels,transform,orientation,detected)
    (OUT/'holdout.json').write_text(json.dumps(cv,indent=2)+'\n')
    corridor,junction,distances,pairs=geometry_field(records,labels,footprint,transform)
    prediction=predict(corridor,distances,orientation,detected)
    assert prediction.max()>0, 'No supported junction candidate; do not export a fake submission'
    dcat=distance_transform_edt(~labels)*100
    density=gaussian_filter(labels.astype('float32'),10)
    eligible=footprint&(dcat>200)
    density[~eligible]=0
    total=float(prediction.sum(dtype='float64'))
    def mass_fraction(a,where): return float(a[where].sum(dtype='float64')/max(a.sum(dtype='float64'),1e-12))
    nonzero=prediction>0
    top=prediction>=np.quantile(prediction[nonzero],.95)
    vector_raster=burn([r['geometry'] for r in records],footprint.shape,transform)&footprint
    dv=distance_transform_edt(~vector_raster)*100
    audit=dict(config=asdict(cfg),trace_parts=len(records),source_ids=len({r['source_id'] for r in records}),
               classification_counts={str(i):sum(r['family']==i for r in records) for i in [0,1]},
               eligible_counts={str(i):sum(r['family']==i and r['eligible'] for r in records) for i in [0,1]},
               catalogue_pixels=int(labels.sum()),catalogue_pixels_within_300m_of_vectors=int((labels&(dv<=300)).sum()),
               vector_pixels=int(vector_raster.sum()),vector_pixels_within_300m_of_catalogue=int((vector_raster&(dcat<=300)).sum()),
               corridors=len(pairs),lineament_proxy_pixels=int(detected.sum()),
               positive_pixels=int(nonzero.sum()),prediction_mass=total,
               mass_within_200m_catalogue=mass_fraction(prediction,dcat<=200),
               junction_mass_fraction=mass_fraction(prediction,junction),
               junction_available_area_fraction=float(junction[eligible].mean()),
               density_control_junction_mass_fraction=mass_fraction(density,junction),
               top5percent_positive_at_junction_fraction=float(junction[top].mean()),
               density_correlation=correlation(prediction,density,footprint),
               junction_definition='within 750m of interior (10–90%) of accepted NW-tip to N/NNE corridor; >200m from catalogue',
               qualification='Concentration is a design diagnostic, not independent evidence of new faults. Full vector catalogue may not exactly match supplied raster; coverage is reported.')
    from collections import Counter
    audit['source_slip_sense_counts']={str(i):dict(Counter(str(r['source_properties'].get('SLIPSENSE')) for r in records if r['family']==i)) for i in [0,1]}
    audit['population_density_checks']={}
    for family in [0,1]:
        den=gaussian_filter(burn([r['geometry'] for r in records if r['family']==family],footprint.shape,transform).astype('float32'),10)
        den[~eligible]=0
        fraction=mass_fraction(den,junction)
        audit['population_density_checks'][str(family)]={'junction_mass_fraction':fraction,'candidate_enrichment':audit['junction_mass_fraction']/max(fraction,1e-12),'sampled_correlation':correlation(prediction,den,footprint)}
    audit['junction_enrichment_vs_density']=audit['junction_mass_fraction']/max(audit['density_control_junction_mass_fraction'],1e-12)
    audit['junction_check_passed']=bool(audit['junction_mass_fraction']>audit['density_control_junction_mass_fraction'] and audit['mass_within_200m_catalogue']==0 and audit['top5percent_positive_at_junction_fraction']>.5 and all(x['candidate_enrichment']>1 for x in audit['population_density_checks'].values()))
    assert audit['junction_check_passed'], 'Candidate fails structural concentration requirement'
    with rasterio.open(ROOT/'data/comparison-h33.tif') as s: historical=s.read(1)
    audit['comparison']={'h33_sha256':hashlib.sha256((ROOT/'data/comparison-h33.tif').read_bytes()).hexdigest(),
                         'different_pixel_count':int((prediction!=historical).sum()),
                         'equal_arrays':bool(np.array_equal(prediction,historical)),
                         'positive_support_jaccard':float(np.logical_and(nonzero,historical>0).sum()/max(np.logical_or(nonzero,historical>0).sum(),1)),
                         'note':'H33 was never an input to prediction construction; comparison only. Global uniqueness across unavailable submissions cannot be proven.'}
    assert not audit['comparison']['equal_arrays']
    digest=hashlib.sha256(prediction.astype('<f4').tobytes()).hexdigest()[:12]
    name=f'gems41-walker-transfer-v1-20261005-{digest}.tif'; path=OUT/name
    profile.update(driver='GTiff',dtype='float32',count=1,nodata=None,compress='deflate',predictor=3,tiled=True,blockxsize=256,blockysize=256)
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
        with rasterio.open(path,'w',**profile) as s:
            s.write(prediction,1);s.write_mask(footprint.astype('uint8')*255)
            s.set_band_description(1,'H41-A structural transfer confidence, not calibrated probability')
            s.update_tags(model='H41-A',status='RESEARCH_ONLY_HOLDOUT_GATE_CLOSED',input='official fault geometry + detrended elevation only')
    receipt=validate(path,ROOT/'data/sample_submission.tif',OUT/'format-receipt.json')
    (OUT/'structural-audit.json').write_text(json.dumps(audit,indent=2)+'\n')
    collection={'type':'FeatureCollection','name':'H41-A candidate transfer corridors EPSG:32611',
                'crs':{'type':'name','properties':{'name':'urn:ogc:def:crs:EPSG::32611'}},
                'features':[{'type':'Feature','geometry':mapping(LineString([(p['tip_x'],p['tip_y']),(p['receiver_x'],p['receiver_y'])])), 'properties':p} for p in pairs]}
    (OUT/'corridors-utm11.geojson').write_text(json.dumps(collection)+'\n')
    note=f'H41-A NW-tip to N/NNE transfer + topographic strike agreement; >200m off catalogue; fresh geometry-only field; holdout gate CLOSED; unscored.'
    manifest=dict(filename=name,submission_name=f'GEMS41-WalkerTransfer-{digest}',note=note,slot_eligible=False,format=receipt,holdout_means=cv['means'])
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    # Spatial review map, not a substitute for the full-resolution artifact.
    import matplotlib;matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig,ax=plt.subplots(figsize=(10,10));step=3
    ax.imshow(np.where(footprint[::step,::step],.92,np.nan),cmap='gray',vmin=0,vmax=1)
    r,c=np.nonzero(labels[::step,::step]);ax.scatter(c,r,s=.08,c='#63778a',alpha=.5)
    show=np.where(prediction[::step,::step]>0,prediction[::step,::step],np.nan)
    im=ax.imshow(show,cmap='magma',vmin=0,vmax=1)
    ax.set_title('H41-A • new transfer-corridor confidence\nGray: mapped faults | Color: new prediction (unscored)')
    ax.set_axis_off();fig.colorbar(im,ax=ax,shrink=.65,label='Structural confidence');fig.tight_layout()
    fig.savefig(ROOT/'docs/structural-map.png',dpi=160);plt.close(fig)
    print(json.dumps(manifest,indent=2));print(json.dumps(audit,indent=2))

if __name__=='__main__': main()
