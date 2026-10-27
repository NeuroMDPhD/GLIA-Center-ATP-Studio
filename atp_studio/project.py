from __future__ import annotations
import csv, json, os, re, shutil, struct
from pathlib import Path
import h5py
import numpy as np
import tifffile
from PIL import Image
from .common import *
from .metrics import quantify
from .media import limits, grayscale, movie_mp4, trace_png

EXPERIMENT_FIELDS=('animal_id','slice_id','recording_id','condition','reviewer','drug_s')

def applied_settings(settings):
    settings=dict(settings)
    if not settings.get('include_experiment',True):
        for key in EXPERIMENT_FIELDS: settings.pop(key,None)
    return settings

def inspect_oir(path, series=0, channel=0, z=0, job=None):
    job=job or Job(); path=Path(path).resolve()
    if path.suffix.lower()!='.oir' or not path.is_file(): raise ValueError('Select an existing OIR file. / OIRファイルを選択してください。')
    if re.search(r'_\d{5}$',path.stem):
        master=path.with_name(re.sub(r'_\d{5}$','',path.stem)+'.oir')
        if master.exists(): raise ValueError(f'Select the master OIR, not a fragment / マスターOIRを選択: {master.name}')
    result=job.run(java_command('OirBridge',2)+['inspect',str(path),str(series),str(channel),str(z)])
    lines=[s[9:] for s in result.splitlines() if s.startswith('ATP_META ')]
    if not lines: raise ValueError('Could not read OIR metadata. / OIR情報を読み込めません。')
    m=json.loads(lines[-1]);m['source_path']=str(path)
    times=m['plane_times_s']
    if all(v is not None for v in times) and len(times)>1:
        dif=np.diff(times)
        if np.all(dif>0): m['interval_s']=float(np.median(dif))
    return m

def resolve_times(meta,interval,override=False):
    if not np.isfinite(interval) or interval<=0: raise ValueError('Frame interval must be positive. / 時間間隔は正の値が必要です。')
    n=meta['shape'][0]; raw=meta.get('plane_times_s',[])
    if not override and len(raw)==n and all(x is not None for x in raw):
        t=np.asarray(raw,dtype=float);t-=t[0]
        if np.any(np.diff(t)<=0): raise ValueError('Non-increasing source timestamps. / 原本の時刻順を確認してください。')
        return t,'Bio-Formats Plane DeltaT'
    return np.arange(n)*interval,'user interval' if override else 'Bio-Formats interval'

def create_project(meta,parent,settings,job=None):
    settings=applied_settings(settings)
    job=job or Job(); n,h,w=meta['shape']
    if n<10: raise ValueError('At least 10 time frames are required. / 10フレーム以上の時系列が必要です。')
    px=float(settings['pixel_x_um']);py=float(settings['pixel_y_um']);dt=float(settings['interval_s'])
    if not all(np.isfinite(v) and v>0 for v in (px,py,dt)): raise ValueError('Check temporal/spatial calibration. / 時間・画素サイズを確認してください。')
    times,time_source=resolve_times(meta,dt,settings.get('override_time',False))
    source=Path(meta['source_path']); directory=new_directory(parent,source.stem+'_ATP')
    for sub in ('raw','runs','exports','logs'): (directory/sub).mkdir()
    p=Project(directory)
    p.manifest=dict(schema_version=1,app_version='0.1.0',created_at=stamp(),status='converting',
        source=meta,acquisition={**settings,'time_source':time_source,'shape':[n,h,w]},
        current_run=None,source_files=[])
    p.save()
    try:
        for f in meta['used_files']:
            job.log('Hashing source / 原本の識別: '+Path(f).name)
            p.manifest['source_files'].append(dict(path=f,size=Path(f).stat().st_size,sha256=sha256(f)))
        p.save();raw=directory/'raw/pixels.partial'
        job.log('OIR → source-resolution TIFF / 原解像度TIFF変換')
        job.run(java_command('OirBridge',4)+['convert',source,meta['series'],meta['channel'],meta['z'],raw],directory/'logs/conversion.log')
        dtype={'uint8':'u1','uint16':'u2','int16':'i2','uint32':'u4','int32':'i4','float':'f4','double':'f8'}[meta['dtype']]
        dtype=np.dtype(('<' if meta['little_endian'] else '>')+dtype)
        if raw.stat().st_size!=n*h*w*dtype.itemsize: raise ValueError('OIR pixel count mismatch. / OIR画素数が一致しません。')
        a=np.memmap(raw,mode='r',dtype=dtype,shape=(n,h,w))
        job.check()
        tifffile.imwrite(directory/'raw/movie.ome.tif',a,bigtiff=a.nbytes>3_500_000_000,
                         photometric='minisblack',metadata={'axes':'TYX','PhysicalSizeX':px,'PhysicalSizeXUnit':'µm',
                         'PhysicalSizeY':py,'PhysicalSizeYUnit':'µm','TimeIncrement':float(np.median(np.diff(times))),
                         'TimeIncrementUnit':'s','Plane':{'DeltaT':times.tolist(),'DeltaTUnit':['s']*n}})
        del a;raw.unlink();np.save(directory/'raw/time_s.npy',times)
        movie=p.movie();lo,hi=limits(movie)
        mean=np.mean(movie,axis=0,dtype=np.float64);mx=np.max(movie,axis=0)
        Image.fromarray(grayscale(mean,lo,hi)).save(directory/'raw/mean_projection.png')
        Image.fromarray(grayscale(mx,lo,hi)).save(directory/'raw/max_projection.png')
        signal=np.asarray([np.mean(frame,dtype=np.float64) for frame in movie])
        write_csv(directory/'raw/fov_trace.csv',({'frame_1based':i+1,'time_s':t,'mean_intensity':v} for i,(t,v) in enumerate(zip(times,signal))))
        trace_png(directory/'raw/fov_trace.png',times,[signal],['FOV mean'],'Whole-field fluorescence',settings.get('drug_s'))
        movie_mp4(movie,directory/'raw/preview.mp4',times,px,job)
        p.manifest.update(status='prepared',display_limits=[lo,hi],raw_tiff_sha256=sha256(directory/'raw/movie.ome.tif'))
        p.save();job.log('Prepared / 準備完了: MP4 · PNG · TIFF · CSV');return str(directory)
    except Exception as e:
        p.manifest.update(status='cancelled' if isinstance(e,Cancelled) else 'failed',error=str(e));p.save();raise

class Project:
    def __init__(self,directory):
        self.path=Path(directory).resolve(); f=self.path/'project.json'
        self.manifest=read_json(f) if f.exists() else {}
    def save(self): save_json(self.path/'project.json',self.manifest)
    def movie(self): return tifffile.memmap(self.path/'raw/movie.ome.tif',mode='r')
    def times(self): return np.load(self.path/'raw/time_s.npy',allow_pickle=False)
    def run_dir(self):
        r=self.manifest.get('current_run')
        return self.path/r if r else None
    def events(self):
        run=self.run_dir();return read_json(run/'events.json') if run else []
    def review(self):
        run=self.run_dir();return read_json(run/'review.json') if run else {}
    def event_data(self,event_id):
        with h5py.File(self.run_dir()/'events.h5','r') as f:
            g=f[str(event_id)];return {k:g[k][()] for k in g}
    def review_event(self,event_id,status,note='',reviewer=''):
        if status not in ('pending','accepted','rejected','hold'): raise ValueError('Invalid review state')
        if event_id not in [e['event_id'] for e in self.events()]: raise ValueError('Unknown event ID')
        run=self.run_dir();r=self.review();before=r.get(str(event_id),{})
        after=dict(status=status,note=note,updated_at=stamp())
        if self.manifest['acquisition'].get('include_experiment',True):after['reviewer']=reviewer
        r[str(event_id)]=after;save_json(run/'review.json',r)
        with open(run/'review_history.jsonl','a',encoding='utf-8') as f:
            f.write(json.dumps(dict(event_id=event_id,before=before,after=after),ensure_ascii=False)+'\n')

def _store_events(p,run,records,shape,offset,engine,job):
    times=p.times();a=p.manifest['acquisition'];rows=[];reviews={}
    with h5py.File(run/'events.h5','w') as f:
        f.attrs['axes']='TYX';f.attrs['offset_yx']=offset
        for rec in records:
            job.check(); eid=rec['event_id'];vox=np.asarray(rec['voxels'],dtype=np.int32)
            if len(vox)!=len(np.unique(vox,axis=0)): raise ValueError('Duplicate event voxels. / イベント座標が重複しています。')
            metrics=quantify(rec['dff'],vox,times,shape,a['pixel_x_um'],a['pixel_y_um'],rec['range'],a.get('drug_s'))
            g=f.create_group(str(eid))
            for k in ('voxels','dff','dff_isolated'):
                g.create_dataset(k,data=rec[k],compression='gzip')
            g.create_dataset('range',data=rec['range'])
            row=dict(event_id=eid,engine=engine,favorite_hint=rec.get('favorite_hint',False),**metrics,**rec.get('aqua_features',{}))
            rows.append(row);reviews[str(eid)]=dict(status='pending',note='',reviewer='',updated_at=None)
    save_json(run/'events.json',rows);save_json(run/'review.json',reviews)
    write_csv(run/'all_detected_events.csv',rows,fields=None if rows else ['event_id','engine','peak_dff','area_um2','qc_flags'])
    return rows

DEFAULT_DETECTION=dict(thrARScl=3.0,minSize=20,minDur=5,sigThr=3.5,smoXY=.5,
    movAvgWin=25,cut=200,sourceSensitivity=8,sourceSzRatio=.01,regMaskGap=5,memory_gb=12,median_radius=1)

def detect(p,settings,job=None):
    job=job or Job();p=Project(p) if not isinstance(p,Project) else p
    if sha256(p.path/'raw/movie.ome.tif')!=p.manifest['raw_tiff_sha256']:
        raise ValueError('Prepared TIFF has changed. Create a new project. / TIFFが変更されています。新規プロジェクトを作成してください。')
    a=p.manifest['acquisition'];times=p.times();diff=np.diff(times)
    if not np.allclose(diff,np.median(diff),rtol=.01,atol=.001):
        raise ValueError('Irregular timestamps: AQuA2 requires uniform intervals. / 不等間隔時系列には未対応です。')
    if not np.isclose(a['pixel_x_um'],a['pixel_y_um'],rtol=.01):
        raise ValueError('Square pixels are required. Check X/Y calibration. / 正方画素が必要です。X/Yを確認してください。')
    cfg={**DEFAULT_DETECTION,**settings};movie=p.movie();n,h,w=movie.shape;gap=int(cfg['regMaskGap'])
    if gap<0 or gap*2>=min(h,w)-4: raise ValueError('Edge crop is too large. / 周辺除外幅が大きすぎます。')
    if cfg['movAvgWin']>n or cfg['minDur']>n: raise ValueError('Window exceeds recording length. / 時間窓が記録より長いです。')
    run=new_directory(p.path/'runs','aqua2');settings_path=run/'settings.json'
    runmeta=dict(status='running',started_at=stamp(),engine='AQuA2-Fiji',engine_commit=ENGINE_COMMIT,
                 input_sha256=p.manifest['raw_tiff_sha256'],settings=cfg,offset_yx=[gap,gap],shape=[n,h-2*gap,w-2*gap])
    save_json(settings_path,runmeta)
    try:
        crop=movie[:,gap:h-gap if gap else h,gap:w-gap if gap else w]
        job.log('Preparing AQuA2 input / 入力準備');binary=run/'input_f32be.bin'
        with open(binary,'wb') as f:
            from scipy.ndimage import median_filter
            radius=int(cfg['median_radius'])
            for frame in crop:
                job.check()
                processed=median_filter(frame,size=2*radius+1,mode='reflect') if radius else frame
                np.asarray(processed,dtype='>f4').tofile(f)
        props={k:v for k,v in cfg.items() if k!='memory_gb'}
        props.update(H=crop.shape[1],W=crop.shape[2],T=n,frameRate=float(np.median(diff)),spatialRes=a['pixel_x_um'])
        (run/'request.properties').write_text('\n'.join(f'{k}={v}' for k,v in props.items()),encoding='ascii')
        job.log('Running AQuA2; large movies may take several minutes. / AQuA2解析中。大きな記録には時間がかかります。')
        job.run(java_command('va.vt.cbilAQuA2.run.StudioBridge',cfg['memory_gb'])+[run/'request.properties',binary,run],run/'engine.log')
        features={}
        with open(run/'aqua_features.csv') as f:
            for r in csv.DictReader(f):
                eid=int(r.pop('event_id'));features[eid]={k:float(v) for k,v in r.items()}
        def records():
            with open(run/'events.bin','rb') as f:
                def integers(count):
                    b=f.read(count*4)
                    if len(b)!=count*4: raise ValueError('Truncated AQuA2 output. / AQuA2出力が不完全です。')
                    return np.frombuffer(b,dtype='>i4').astype(np.int32)
                magic,count,nt,hh,ww=integers(5)
                if magic!=0x41545031 or [nt,hh,ww]!=runmeta['shape']: raise ValueError('AQuA2 shape mismatch / 出力サイズ不一致')
                for _ in range(count):
                    eid,nvox=integers(2);v=integers(int(nvox)*3).reshape(-1,3);rg=integers(2)
                    dff=np.frombuffer(f.read(nt*4),dtype='>f4').astype(np.float32)
                    isolated=np.frombuffer(f.read(nt*4),dtype='>f4').astype(np.float32)
                    yield dict(event_id=int(eid),voxels=v,dff=dff,dff_isolated=isolated,range=rg,aqua_features=features[int(eid)])
                if f.read(1): raise ValueError('Unexpected AQuA2 trailing data')
        rows=_store_events(p,run,records(),runmeta['shape'],[gap,gap],'AQuA2-Fiji',job)
        runmeta.update(status='complete',finished_at=stamp(),event_count=len(rows));save_json(settings_path,runmeta)
        p.manifest.update(current_run=str(run.relative_to(p.path)),status='review');p.save()
        # Reproducible temporary arrays are large. Completed event masks and source TIFF are retained.
        for f in ('input_f32be.bin','dF.ser','events.bin'): (run/f).unlink(missing_ok=True)
        job.log(f'AQuA2 complete / 完了: {len(rows)} ROAs');return str(run)
    except Exception as e:
        runmeta.update(status='cancelled' if isinstance(e,Cancelled) else 'failed',error=str(e),finished_at=stamp())
        save_json(settings_path,runmeta);raise

def import_mat(p,mat_path,channel=1,job=None):
    """Import v7.3 projects without MATLAB; original favorites are suggestions, never new approvals."""
    job=job or Job();p=Project(p) if not isinstance(p,Project) else p;mat_path=Path(mat_path)
    if not h5py.is_hdf5(mat_path): raise ValueError('Only AQuA2 MATLAB v7.3 MAT files are supported. / MATLAB v7.3形式のAQuA2 MATのみ対応します。')
    if sha256(p.path/'raw/movie.ome.tif')!=p.manifest['raw_tiff_sha256']:
        raise ValueError('Prepared TIFF has changed. / TIFFが変更されています。')
    movie=p.movie();n,h,w=movie.shape;ch=str(channel);a=p.manifest['acquisition']
    run=new_directory(p.path/'runs','import_mat');runmeta=dict(status='running',source_mat=str(mat_path),source_sha256=sha256(mat_path),engine='AQuA2-MATLAB import',channel=channel)
    save_json(run/'settings.json',runmeta)
    try:
        with h5py.File(mat_path,'r') as f:
            r=f['res'];o=r['opts'];data=r['datOrg'+ch];nt,z,ww,hh=data.shape
            if nt!=n or z!=1: raise ValueError('Source/MAT time or Z mismatch. / 原本とMATの時間・Zが不一致です。')
            gap=int(o['regMaskGap'][()].ravel()[0]) if 'regMaskGap' in o else -1
            if gap<0 or (hh,ww)!=(h-2*gap,w-2*gap): raise ValueError('Source/MAT crop mismatch. / 原本とMATの切り出し座標が不一致です。')
            aqua_dt=float(o['frameRate'][()].ravel()[0]);aqua_px=float(o['spatialRes'][()].ravel()[0])
            if not np.isclose(aqua_dt,np.median(np.diff(p.times())),rtol=.01): raise ValueError('Source/MAT interval mismatch. / 原本とMATの時間間隔が不一致です。')
            if not np.isclose(aqua_px,a['pixel_x_um'],rtol=.01) or not np.isclose(aqua_px,a['pixel_y_um'],rtol=.01):
                raise ValueError('Source/MAT pixel size mismatch. / 原本とMATの画素サイズが不一致です。')
            # Validate content, not filenames. Allow uniform intensity scaling from MATLAB preprocessing.
            corrs=[];residuals=[]
            med=int(o['medSmo'][()].ravel()[0]) if 'medSmo' in o else 0
            registration=int(o['registrateCorrect'][()].ravel()[0]) if 'registrateCorrect' in o else 1
            if registration!=1: raise ValueError('Registered MAT movies require a verified coordinate transform. / 位置補正済みMATには座標変換の検証が必要です。')
            from scipy.ndimage import median_filter
            for frame in np.unique(np.linspace(0,n-1,7,dtype=int)):
                x=np.asarray(movie[frame,gap:h-gap if gap else h,gap:w-gap if gap else w],float)
                if med: x=median_filter(x,size=2*med+1,mode='constant')
                y=np.asarray(data[frame,0,:,:].T,float)
                margin=max(med,1);x=x[margin:-margin:4,margin:-margin:4].ravel();y=y[margin:-margin:4,margin:-margin:4].ravel()
                if x.std()==0 or y.std()==0: raise ValueError('Insufficient spatial detail for source verification. / 原本照合に必要な空間情報がありません。')
                slope,intercept=np.polyfit(x,y,1);corr=float(np.corrcoef(x,y)[0,1]);corrs.append(corr)
                residuals.append(float(np.sqrt(np.mean((y-(slope*x+intercept))**2))/y.std()))
                if corr<.995 or slope<=0: raise ValueError('Source pixels do not match the MAT; verify recording identity. / 原本とMATの内容が不一致です。記録を確認してください。')
            runmeta.update(offset_yx=[gap,gap],shape=[n,hh,ww],source_validation={'sampled_frames':7,'correlations':corrs,'relative_rmse':residuals,'declared_median_radius':med,'registration':registration,'method':'spatial affine intensity match after declared median filter; interior pixels'})
            refs=r['evt'+ch];count=refs.size;favorites=set()
            if 'evtFavList'+ch in r:
                ds=r['evtFavList'+ch]
                if not ds.attrs.get('MATLAB_empty',False): favorites=set(np.asarray(ds[()]).ravel().astype(int))
            dff=r['dffMat'+ch];fts=r['fts'+ch]
            def records():
                for i,ref in enumerate(refs[()].ravel()):
                    job.check();eid=i+1;idx=f[ref][()].ravel().astype(np.int64)-1
                    v=np.column_stack((idx//(hh*ww),idx%hh,(idx//hh)%ww)).astype(np.int32)
                    rg=fts['curve/rgt1'][:,i].astype(int)-1
                    af={}
                    for name,target in [('dffMax','aqua_peak_dff'),('width55','aqua_fwhm_s'),('rise19','aqua_rise_10_90_s'),('fall91','aqua_fall_90_10_s'),('decayTau','aqua_decay_tau_s'),('dffAUC','aqua_auc_dff_frames')]:
                        if name in fts['curve']: af[target]=float(fts['curve/'+name][()].ravel()[i])
                    yield dict(event_id=eid,voxels=v,dff=dff[0,:,i],dff_isolated=dff[1,:,i],range=rg,
                               favorite_hint=eid in favorites,aqua_features=af)
            rows=_store_events(p,run,records(),[n,hh,ww],[gap,gap],'AQuA2-MATLAB import',job)
        runmeta.update(status='complete',finished_at=stamp(),event_count=len(rows));save_json(run/'settings.json',runmeta)
        p.manifest.update(current_run=str(run.relative_to(p.path)),status='review');p.save();return str(run)
    except Exception as e:
        runmeta.update(status='failed',error=str(e));save_json(run/'settings.json',runmeta);raise

def export_selected(p,with_movie=True,job=None):
    job=job or Job();p=Project(p) if not isinstance(p,Project) else p
    if sha256(p.path/'raw/movie.ome.tif')!=p.manifest['raw_tiff_sha256']:
        raise ValueError('Prepared TIFF has changed; export stopped. / TIFFが変更されたため出力を中止しました。')
    events=p.events();reviews=p.review();run=p.run_dir()
    if run is None: raise ValueError('Detect events or import MAT first. / 先に検出またはMAT読み込みを完了してください。')
    selected=[e for e in events if reviews.get(str(e['event_id']),{}).get('status')=='accepted']
    out=new_directory(p.path/'exports','selected');acq=p.manifest['acquisition'];times=p.times()
    setting=read_json(run/'settings.json');offset=np.asarray(setting['offset_yx']);n,h,w=acq['shape']
    exportmeta=dict(status='running',created_at=stamp(),run=str(run.relative_to(p.path)),selected_ids=[r['event_id'] for r in selected],
                    project=p.manifest,review=reviews,engine_settings=setting)
    save_json(out/'manifest.json',exportmeta)
    try:
        include_experiment=acq.get('include_experiment',True)
        metadata={k:acq.get(k,'') for k in EXPERIMENT_FIELDS if k!='drug_s'} if include_experiment else {}
        all_rows=[]
        for e in events:
            row={**metadata,**e,**reviews.get(str(e['event_id']),{})}
            if not include_experiment:
                row.pop('reviewer',None);row.pop('onset_from_drug_s',None)
            row['centroid_x_analysis_px']=row.pop('centroid_x_px')
            row['centroid_y_analysis_px']=row.pop('centroid_y_px')
            row['centroid_x_source_px']=row['centroid_x_analysis_px']+int(offset[1])
            row['centroid_y_source_px']=row['centroid_y_analysis_px']+int(offset[0])
            row['coordinate_origin']='zero-based; source=original image, analysis=cropped image'
            all_rows.append(row)
        fields=list(dict.fromkeys(k for r in all_rows for k in r)) or ['event_id','status','peak_dff','area_um2','qc_flags']
        write_csv(out/'review_all_events.csv',all_rows,fields)
        write_csv(out/'selected_events.csv',[r for r in all_rows if r.get('status')=='accepted'],fields)
        traces=[];label_names=[];voxels={};roamasks=[]
        with open(out/'selected_traces.csv','w',newline='',encoding='utf-8-sig') as fcsv, h5py.File(out/'selected_events.h5','w') as fh:
            writer=csv.writer(fcsv);writer.writerow(['event_id','frame_1based','time_s','dff_original_footprint','dff_other_events_imputed','active_at_frame'])
            fh.attrs['axes']='TYX';fh.attrs['coordinates']='original source frame, zero based';fh.create_dataset('time_s',data=times)
            for row in selected:
                job.check();eid=row['event_id'];d=p.event_data(eid);v=d['voxels'].copy();v[:,1:]+=offset;voxels[eid]=v
                active=set(v[:,0]);writer.writerows((eid,i+1,t,float(d['dff'][i]),float(d['dff_isolated'][i]),i in active) for i,t in enumerate(times))
                g=fh.create_group(str(eid));g.create_dataset('voxels_tyx',data=v,compression='gzip');g.create_dataset('dff',data=d['dff'])
                mask=np.zeros((h,w),dtype=np.uint8);mask[v[:,1],v[:,2]]=1;roamasks.append(mask)
                traces.append(d['dff']);label_names.append(f'ROA {eid}')
                trace_png(out/f'ROA_{eid:04d}.png',times,[d['dff']],['AQuA2 dF/F'],f'ROA {eid}',acq.get('drug_s'),[row['onset_s'],row['end_s']])
        if roamasks:
            # One page per accepted ROA prevents loss where spatial footprints overlap.
            tifffile.imwrite(out/'selected_ROA_masks.tif',np.stack(roamasks),photometric='minisblack',metadata={'axes':'QYX','event_ids':exportmeta['selected_ids']})
            write_csv(out/'mask_page_index.csv',({'page_1based':i+1,'event_id':eid} for i,eid in enumerate(exportmeta['selected_ids'])))
        movie=p.movie();lo,hi=p.manifest['display_limits'];background=grayscale(np.mean(movie,axis=0),lo,hi)
        rgb=np.repeat(background[...,None],3,axis=2)
        from scipy.ndimage import binary_erosion
        from PIL import ImageDraw
        for mask in roamasks:
            edge=mask.astype(bool)&~binary_erosion(mask);rgb[edge]=[20,213,170]
        im=Image.fromarray(rgb);draw=ImageDraw.Draw(im)
        for eid,v in voxels.items(): draw.text((int(v[:,2].mean()),int(v[:,1].mean())),str(eid),fill='yellow')
        im.save(out/'selected_ROA_overlay.png')
        if traces: trace_png(out/'selected_traces.png',times,traces,label_names,'Accepted ATP ROA traces',acq.get('drug_s'))
        if with_movie and selected: movie_mp4(movie,out/'selected_ROA_overlay.mp4',times,acq['pixel_x_um'],job,voxels)
        counts={s:sum(v.get('status')==s for v in reviews.values()) for s in ('accepted','rejected','pending','hold')}
        duration=float(times[-1]-times[0]);summary={**metadata,**counts,'detected_events':len(events),'observation_start_s':times[0],
            'observation_end_s':times[-1],'observation_duration_s':duration,'accepted_onset_rate_per_min':sum(not e['starts_at_recording_start'] for e in selected)/duration*60,
            'rate_scope':'accepted onsets over first-to-last sample; events present at first sample excluded; review may be incomplete',
            'review_complete':counts['pending']==0 and counts['hold']==0,'unit_of_observation':'recording (events nested within recording)',
            'biological_n':'not computed; animal_id must be retained when pooling'}
        write_csv(out/'recording_summary.csv',[summary]);
        from html import escape
        (out/'RESULTS.html').write_text('<!doctype html><meta charset="utf-8"><title>ATP ROA results</title><style>body{font:16px system-ui;max-width:960px;margin:40px auto;line-height:1.65}img{max-width:100%}code{background:#eee}</style>'
            +f'<h1>ATP ROA results / 解析結果</h1><p>Kept / 採用 {len(selected)} / Detected / 検出 {len(events)} · Hold / 保留 {counts["hold"]} · Pending / 未確認 {counts["pending"]}</p>'
            +'<p>ROAs are spatiotemporal events, not individual cells or animal replicates.<br>ROAは時空間活動イベントです。細胞数・動物数とは異なります。</p>'
            +'<img src="selected_ROA_overlay.png"><p><a href="selected_events.csv">Features / 定量値</a> · <a href="selected_traces.csv">Traces / 時系列</a> · <a href="review_all_events.csv">Review / 確認履歴</a> · <a href="manifest.json">Settings / 設定</a></p>'
            +'<p>FWHM and rise/fall use linearly interpolated threshold crossings relative to zero-baseline AQuA2 ΔF/F. Unobserved crossings remain blank. AUC uses trapezoidal integration between detected onset and end. Decay τ fits A exp(-t/τ)+C and requires R²≥0.8.<br>FWHM・上昇下降時間はゼロ基準のΔF/F閾値交差を線形補間します。交差が観察されない場合は空欄です。AUCは検出開始から終了までの台形積分、減衰τはR²≥0.8の指数適合値です。</p>'
            +'<p>duration_span_s = last minus first detected time; active_sample_duration_s = active frame count × interval. The aqua_ columns retain native AQuA2 definitions, which may differ.<br>duration_span_sは検出時刻の差、active_sample_duration_sは活動フレーム数×時間間隔です。aqua_列はAQuA2独自の定義を保持します。</p>'
            +'<p>Selection-dependent rates do not estimate total ATP frequency without selection bias. Check review_complete.<br>採用条件に依存する頻度には選択バイアスがあります。review_completeで確認完了状態を確認してください。</p>',encoding='utf-8')
        exportmeta.update(status='complete',finished_at=stamp(),files={f.name:sha256(f) for f in out.iterdir() if f.is_file() and f.name!='manifest.json'})
        save_json(out/'manifest.json',exportmeta);job.log(f'Export complete / 出力完了: {len(selected)} ROAs');return str(out)
    except Exception as e:
        exportmeta.update(status='cancelled' if isinstance(e,Cancelled) else 'failed',error=str(e));save_json(out/'manifest.json',exportmeta);raise
