"""Explainable review aids. These rules are not a validated ATP classifier."""
from pathlib import Path
import hashlib
import json
import h5py
import numpy as np
from scipy.ndimage import label as connected_components
from .common import Job, read_json, save_json, sha256, stamp

RULE_VERSION='review-rules-1'
DEFAULTS=dict(signal_snr=5.0,noise_snr=2.0,min_support_frames=3,min_pixel_support=.35)
LABELS={'signal':'Signal candidate / 信号候補','review':'Check / 要確認','noise':'Noise-like / ノイズ疑い'}
REASONS={
    'strong_trace':'Clear rise above trace noise / 波形ノイズを上回る上昇',
    'weak_trace':'Small rise relative to trace noise / ノイズに対する上昇が小さい',
    'moderate_trace':'Intermediate trace signal-to-noise / 波形の信号対雑音比が中程度',
    'brief_peak':'Only a brief peak is supported / ピークを支える連続フレームが少ない',
    'pixel_support':'Rise is supported by raw-image pixels / 原画像の画素でも上昇を確認',
    'low_pixel_support':'Limited support in raw-image pixels / 原画像で上昇する画素が少ない',
    'raw_unavailable':'Raw-image support could not be measured / 原画像の支持率を測定できない',
    'fragmented':'Spatial footprint is fragmented / 空間領域が分断されている',
    'intermittent':'Activity is intermittent within its span / 活動区間内に空白が多い',
    'edge':'Touches the analysis boundary / 解析領域の境界に接する',
    'truncated':'Event touches the start or end of recording / 記録の開始・終了で打ち切られる',
    'baseline_short':'Too few non-event frames for noise estimation / ノイズ推定用の区間が不足',
    'noise_undefined':'Noise cannot be estimated reliably / ノイズを安定して推定できない',
    'nonfinite':'Trace contains missing or nonfinite samples / 波形に欠損・非有限値がある',
}

def validate_config(config):
    c={**DEFAULTS,**(config or {})}
    if set(c)!=set(DEFAULTS):raise ValueError('Unknown suggestion setting')
    if not all(np.isfinite(float(v)) for v in c.values()):raise ValueError('Suggestion settings must be finite')
    if not 0<float(c['noise_snr'])<float(c['signal_snr']):raise ValueError('Signal SNR must exceed noise SNR. / 信号SNRはノイズSNRより大きくしてください。')
    if not 1<=int(c['min_support_frames'])<=100 or int(c['min_support_frames'])!=c['min_support_frames']:raise ValueError('Invalid frame threshold')
    if not 0<float(c['min_pixel_support'])<=1:raise ValueError('Invalid pixel support threshold')
    return c

def reason_text(result):
    return '; '.join(REASONS.get(k,k) for k in result.get('reason_codes',[]))

def robust_sd(values,axis=None):
    median=np.median(values,axis=axis,keepdims=True)
    return 1.4826*np.median(np.abs(values-median),axis=axis)

def raw_pixel_support(movie,voxels,peak,baseline_frames,offset):
    active=voxels[np.abs(voxels[:,0]-peak)<=1]
    if not len(active):return None
    pixels=np.unique(active[:,1:3],axis=0)+np.asarray(offset)
    pixels=pixels[np.linspace(0,len(pixels)-1,min(256,len(pixels)),dtype=int)]
    if np.any(pixels<0) or np.any(pixels>=np.asarray(movie.shape[1:])):raise ValueError('Suggestion pixels outside source image')
    frames=baseline_frames[np.linspace(0,len(baseline_frames)-1,min(40,len(baseline_frames)),dtype=int)]
    base=np.asarray(movie[frames[:,None],pixels[None,:,0],pixels[None,:,1]],dtype=float)
    signal_frames=np.unique(active[:,0])
    signal=np.asarray(movie[signal_frames[:,None],pixels[None,:,0],pixels[None,:,1]],dtype=float)
    if not np.all(np.isfinite(base)) or not np.all(np.isfinite(signal)):return None
    noise=robust_sd(base,axis=0)
    floor=1.0 if np.issubdtype(movie.dtype,np.integer) else max(1e-9,float(np.max(np.abs(base)))*1e-7)
    noise=np.maximum(noise,floor)
    return float(np.mean(np.mean(signal,axis=0)-np.median(base,axis=0)>2*noise))

def assess_event(trace,voxels,shape,event,config=None,movie=None,offset=(0,0)):
    c=validate_config(config);y=np.asarray(trace,dtype=float);v=np.asarray(voxels,dtype=int)
    result=dict(event_id=int(event['event_id']),category='review',reason_codes=[],trace_snr=None,
                baseline_dff=None,noise_dff=None,support_frames=0,pixel_support=None,
                largest_component_fraction=None,temporal_occupancy=None,rule_version=RULE_VERSION)
    reasons=result['reason_codes']
    if len(y)!=shape[0] or v.ndim!=2 or v.shape[1]!=3 or not len(v) or np.any(v<0) or np.any(v>=np.asarray(shape)):
        raise ValueError('Invalid event data for suggestions')
    if not np.all(np.isfinite(y)):reasons.append('nonfinite');return result
    start,end=int(v[:,0].min()),int(v[:,0].max())
    baseline=np.ones(len(y),dtype=bool);baseline[max(0,start-2):min(len(y),end+3)]=False
    off=np.flatnonzero(baseline)
    if len(off)<12:reasons.append('baseline_short');return result
    center=float(np.median(y[off]));noise=float(robust_sd(y[off]));result.update(baseline_dff=center,noise_dff=noise)
    if noise<=max(1e-10,float(np.max(np.abs(y)))*1e-8):reasons.append('noise_undefined');return result
    peak=start+int(np.argmax(y[start:end+1]));snr=float((y[peak]-center)/noise);result['trace_snr']=snr
    support=y>center+2*noise;left=right=peak
    while left>start and support[left-1]:left-=1
    while right<end and support[right+1]:right+=1
    result['support_frames']=int(right-left+1) if support[peak] else 0
    pixels=np.unique(v[:,1:3],axis=0);lo=pixels.min(axis=0);hi=pixels.max(axis=0)
    mask=np.zeros(hi-lo+1,dtype=bool);mask[tuple((pixels-lo).T)]=True
    labels,_=connected_components(mask,structure=np.ones((3,3)))
    result['largest_component_fraction']=float(np.bincount(labels.ravel())[1:].max()/len(pixels))
    result['temporal_occupancy']=float(len(np.unique(v[:,0]))/(end-start+1))
    if movie is not None:result['pixel_support']=raw_pixel_support(movie,v,peak,off,offset)
    reasons.append('strong_trace' if snr>=c['signal_snr'] else ('weak_trace' if snr<c['noise_snr'] else 'moderate_trace'))
    if result['support_frames']<c['min_support_frames']:reasons.append('brief_peak')
    if result['pixel_support'] is None:reasons.append('raw_unavailable')
    else:reasons.append('pixel_support' if result['pixel_support']>=c['min_pixel_support'] else 'low_pixel_support')
    if result['largest_component_fraction']<.5:reasons.append('fragmented')
    if result['temporal_occupancy']<.7:reasons.append('intermittent')
    if event.get('touches_analysis_edge'):reasons.append('edge')
    if event.get('starts_at_recording_start') or event.get('ends_at_recording_end'):reasons.append('truncated')
    caution={'brief_peak','raw_unavailable','low_pixel_support','fragmented','intermittent','edge','truncated'}
    if snr<c['noise_snr']:result['category']='noise'
    elif snr>=c['signal_snr'] and not caution.intersection(reasons):result['category']='signal'
    return result

def _context(project,config=None):
    run=project.run_dir()
    if run is None:return None
    settings_file=run/'suggestion_settings.json'
    c=validate_config(config if config is not None else (read_json(settings_file) if settings_file.exists() else DEFAULTS))
    raw=project.path/'raw/movie.ome.tif';stat=raw.stat()
    inputs={'raw_expected_sha256':project.manifest['raw_tiff_sha256'],'raw_size':stat.st_size,'raw_mtime_ns':stat.st_mtime_ns,
            'events_sha256':sha256(run/'events.json'),'masks_traces_sha256':sha256(run/'events.h5'),
            'settings_sha256':sha256(run/'settings.json'),'time_sha256':sha256(project.path/'raw/time_s.npy')}
    identity=json.dumps({'inputs':inputs,'config':c,'rules':RULE_VERSION},sort_keys=True).encode()
    key=hashlib.sha256(identity).hexdigest()
    return run,c,inputs,run/'suggestions'/f'{key}.json'

def cached_suggestions(project):
    context=_context(project)
    if context is None:return None
    path=context[3]
    if path.exists():
        data=read_json(path)
        if data.get('rule_version')==RULE_VERSION and set(data.get('events',{}))=={str(e['event_id']) for e in project.events()}:return data
    return None

def build_suggestions(project,config=None,force=False,job=None):
    job=job or Job();context=_context(project,config)
    if context is None:return None
    run,c,inputs,path=context
    if path.exists() and not force:
        if config is not None:save_json(run/'suggestion_settings.json',c)
        return read_json(path)
    if sha256(project.path/'raw/movie.ome.tif')!=inputs['raw_expected_sha256']:
        raise ValueError('Prepared TIFF has changed; suggestions stopped. / TIFFが変更されたため提案を中止しました。')
    events=project.events();settings=read_json(run/'settings.json');movie=project.movie();results={}
    with h5py.File(run/'events.h5','r') as f:
        for i,event in enumerate(events):
            job.check();g=f[str(event['event_id'])]
            results[str(event['event_id'])]=assess_event(g['dff'][()],g['voxels'][()],settings['shape'],event,c,movie,settings['offset_yx'])
            if i%10==0:job.log(f'Review suggestions / 確認の提案: {i+1}/{len(events)}')
    data={'rule_version':RULE_VERSION,'created_at':stamp(),'config':c,'inputs':inputs,
          'interpretation':'Unvalidated review aids; not ATP identity or a probability. Human review is retained.', 'events':results}
    job.check();save_json(path,data)
    if config is not None:save_json(run/'suggestion_settings.json',c)
    return data

def export_columns(result):
    if not result:return {}
    return {'suggestion':result['category'],'suggestion_reasons':reason_text(result),'suggestion_rule_version':result['rule_version'],
            **{'suggestion_'+k:result.get(k) for k in ('trace_snr','support_frames','pixel_support','largest_component_fraction','temporal_occupancy')}}
