"""Official published distance-weighted Tversky formula, not a calibrated surrogate."""
import numpy as np
from scipy.ndimage import distance_transform_edt


def dti(prediction, truth, evaluation=None, radius=3.0):
    p=np.asarray(prediction,dtype='float32')
    g=np.asarray(truth,dtype=bool)
    if p.shape!=g.shape or p.ndim!=2: raise ValueError('matching 2D arrays required')
    if not np.isfinite(p).all() or p.min()<0 or p.max()>1: raise ValueError('predictions must be finite in [0,1]')
    if radius<=0: raise ValueError('positive radius required')
    if evaluation is not None:
        p=np.where(evaluation,p,0); g=g & evaluation
    if not g.any():
        return {'dti':0.0,'tp':0.0,'fp':float(p.sum(dtype='float64')),'fn':0.0,'truth_pixels':0}
    r,c=np.nonzero(g); covered=np.zeros(len(r),dtype='float32')
    n=int(np.ceil(radius))
    for dr in range(-n,n+1):
        for dc in range(-n,n+1):
            weight=max(0,1-np.hypot(dr,dc)/radius)
            if weight<=0: continue
            rr,cc=r+dr,c+dc
            ok=(rr>=0)&(rr<p.shape[0])&(cc>=0)&(cc<p.shape[1])
            covered[ok]=np.maximum(covered[ok],p[rr[ok],cc[ok]]*weight)
    tp=float(covered.sum(dtype='float64')); fn=float(len(r)-tp)
    nearest=distance_transform_edt(~g)
    fp=float((p*np.minimum(nearest/radius,1)).sum(dtype='float64'))
    return {'dti':tp/(tp+.2*fp+.8*fn+1e-12),'tp':tp,'fp':fp,'fn':fn,'truth_pixels':len(r)}
