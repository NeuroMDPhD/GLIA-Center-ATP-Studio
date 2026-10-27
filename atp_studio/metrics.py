"""Explicit, censored event measurements; never treat events as animal replicates."""
import warnings
import numpy as np
from scipy.optimize import curve_fit, OptimizeWarning

def crossings(y, t, peak_index, level):
    left=right=None
    # Nearest crossing on each side of this event's peak. No extrapolation.
    for i in range(peak_index-1,-1,-1):
        if y[i] < level <= y[i+1]:
            left=t[i]+(level-y[i])/(y[i+1]-y[i])*(t[i+1]-t[i]); break
    for i in range(peak_index,len(y)-1):
        if y[i] >= level > y[i+1]:
            right=t[i]+(level-y[i])/(y[i+1]-y[i])*(t[i+1]-t[i]); break
    return left,right

def quantify(dff, voxels, time_s, shape, px, py, analysis_range=None, drug_s=None):
    dff=np.asarray(dff,dtype=float); t=np.asarray(time_s,dtype=float); v=np.asarray(voxels)
    if v.ndim!=2 or v.shape[1]!=3 or len(v)==0: raise ValueError('Invalid event voxels')
    n,h,w=shape
    if np.any(v<0) or np.any(v>=np.array(shape)): raise ValueError('Event voxels outside movie')
    if len(dff)!=n or len(t)!=n or np.any(np.diff(t)<=0): raise ValueError('Invalid event time axis')
    start,end=int(v[:,0].min()),int(v[:,0].max())
    lo,hi=analysis_range if analysis_range is not None else (start,end)
    if not (0<=lo<=start<=end<=hi<n): raise ValueError('Invalid extended event range')
    dt=float(np.median(np.diff(t))); area=len(np.unique(v[:,1]*w+v[:,2]))
    out=dict(onset_s=t[start],end_s=t[end],duration_span_s=t[end]-t[start],
        active_sample_duration_s=len(np.unique(v[:,0]))*dt,area_px=area,area_um2=area*px*py,
        centroid_x_px=float(np.mean(np.unique(v[:,1:3],axis=0)[:,1])),
        centroid_y_px=float(np.mean(np.unique(v[:,1:3],axis=0)[:,0])),
        peak_dff=None,peak_time_s=None,auc_signed_dff_s=None,auc_positive_dff_s=None,
        fwhm_s=None,rise_10_90_s=None,fall_90_10_s=None,decay_tau_s=None,decay_fit_r2=None,
        starts_at_recording_start=start==0,ends_at_recording_end=end==n-1,
        touches_analysis_edge=bool(np.any((v[:,1]==0)|(v[:,1]==h-1)|(v[:,2]==0)|(v[:,2]==w-1))),
        analysis_start_s=t[lo],analysis_end_s=t[hi],onset_from_drug_s=None if drug_s is None else t[start]-drug_s)
    flags=[]
    if not np.all(np.isfinite(dff[lo:hi+1])):
        flags.append('nonfinite_trace'); out['qc_flags']=';'.join(flags); return out
    ip=start+int(np.argmax(dff[start:end+1])); peak=float(dff[ip]); out.update(peak_dff=peak,peak_time_s=t[ip])
    z=dff[start:end+1]; tz=t[start:end+1]
    out['auc_signed_dff_s']=float(np.trapezoid(z,tz));out['auc_positive_dff_s']=float(np.trapezoid(np.maximum(z,0),tz))
    if peak<=0: flags.append('nonpositive_peak')
    else:
        yy=dff[lo:hi+1]; tt=t[lo:hi+1]; pp=ip-lo
        l50,r50=crossings(yy,tt,pp,peak*.5)
        l10,r10=crossings(yy,tt,pp,peak*.1); l90,r90=crossings(yy,tt,pp,peak*.9)
        if l50 is not None and r50 is not None: out['fwhm_s']=r50-l50
        else: flags.append('fwhm_censored')
        if l10 is not None and l90 is not None: out['rise_10_90_s']=l90-l10
        else: flags.append('rise_censored')
        if r10 is not None and r90 is not None: out['fall_90_10_s']=r10-r90
        else: flags.append('fall_censored')
        fit_end=hi if r10 is None else min(hi,int(np.searchsorted(t,r10))+1)
        tx=t[ip:fit_end+1]-t[ip]; y=dff[ip:fit_end+1]
        if len(tx)>=6 and r50 is not None:
            try:
                def model(x,a,tau,c): return a*np.exp(-x/tau)+c
                upper=max(tx[-1]*10,dt)
                with warnings.catch_warnings():
                    warnings.simplefilter('error',OptimizeWarning)
                    p,_=curve_fit(model,tx,y,p0=(peak,max(dt,tx[-1]/3),0),
                                  bounds=([0,dt/10,-peak],[peak*3,upper,peak]),maxfev=10000)
                residual=np.sum((y-model(tx,*p))**2); total=np.sum((y-y.mean())**2)
                r2=1-residual/total if total>0 else -1; out['decay_fit_r2']=float(r2)
                if r2>=.8 and p[1]<upper*.99 and p[1]>dt/10*1.01: out['decay_tau_s']=float(p[1])
                else: flags.append('decay_fit_unreliable')
            except (RuntimeError,ValueError,OptimizeWarning): flags.append('decay_fit_failed')
        else: flags.append('decay_insufficient')
    for key in ('starts_at_recording_start','ends_at_recording_end','touches_analysis_edge'):
        if out[key]: flags.append(key)
    out['qc_flags']=';'.join(flags); return out
