"""Check restored inputs without copying label values into any prediction."""
import json
from pathlib import Path
import numpy as np
import rasterio
from download_data import sha256,ROOT

def main():
    rows=[]
    with rasterio.open(ROOT/'data/sample_submission.tif') as ref:
        foot=np.isfinite(ref.read(1));grid=(ref.shape,ref.crs,ref.transform)
        for name in ['training_features.tif','existing_faults.tif','sample_submission.tif']:
            p=ROOT/'data'/name
            with rasterio.open(p) as s:
                assert (s.shape,s.crs,s.transform)==grid
                rows.append(dict(name=name,sha256=sha256(p),shape=list(s.shape),bands=s.count,crs=str(s.crs)))
        with rasterio.open(ROOT/'data/existing_faults.tif') as s:
            labels=s.read(1)==1
        assert not labels[~foot].any()
        report=dict(files=rows,footprint_cells=int(foot.sum()),label_pixels=int(labels.sum()),
                    warning='Template contains 60,988 ones coincident with labels. Only grid and finite mask are used, never its positive values.')
    (ROOT/'research/prepared-data.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':main()
