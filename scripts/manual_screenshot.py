"""Illustrative GUI screenshot. Reads no OIR, project or experimental data."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from PySide6 import QtWidgets as W
from atp_studio.gui import MainWindow

app=W.QApplication([])
from atp_studio.theme import install_fonts
install_fonts(app)
window=MainWindow()
window.destination.setText('C:\\Recordings')
window.source.setText('C:\\Recordings\\example_ATP.oir')
window.on_metadata({'series_count':1,'channels':2,'z_planes':1,'series':0,'channel':0,'z':0,
    'source_path':'example_ATP.oir','shape':[600,256,256],'interval_s':.5,
    'pixel_x_um':.5,'pixel_y_um':.5,'dtype':'uint16'})
window.experiment_group.setChecked(False)
window.status.setText('Illustrative example / 説明用（実データではありません）')
window.show();app.processEvents()
out=ROOT/'docs/screenshots';out.mkdir(exist_ok=True)
assert window.grab().save(str(out/'prepare.png'))
# The worker waits only for this illustration; no data or analysis is used.
from threading import Event
from PySide6 import QtTest as T
release=Event();window.go(1)
window.run_job(lambda job:release.wait(5),lambda result:None)
window.status.setText('Illustrative processing state / 処理中表示の説明例（実データではありません）')
T.QTest.qWait(350)
assert window.grab().save(str(out/'processing.png'))
release.set();window.worker.wait(5000);app.processEvents()
window.close()
print(out/'prepare.png')
print(out/'processing.png')

# Reproducible illustrative review screen: synthetic movie and events only.
import tempfile
import numpy as np
import tifffile
from atp_studio.project import Project, _store_events
from atp_studio.common import save_json, sha256, Job
from atp_studio.suggestions import build_suggestions
from PySide6 import QtTest as T
with tempfile.TemporaryDirectory(prefix='glia-manual-') as tmp:
    path=Path(tmp);p=Project(path)
    for d in ('raw','runs/example','exports'):(path/d).mkdir(parents=True)
    rng=np.random.default_rng(7);n,h,w=100,96,128;t=np.arange(n,dtype=float)*.5
    yy,xx=np.mgrid[:h,:w];background=np.full((h,w),90.)
    for cy,cx in rng.uniform([0,0],[h,w],(80,2)):background+=rng.uniform(3,20)*np.exp(-((yy-cy)**2+(xx-cx)**2)/rng.uniform(1,12))
    movie=background[None]+rng.normal(0,1.5,(n,h,w));records=[]
    for eid,(cy,cx,peak) in enumerate([(34,44,45),(70,90,70),(15,105,25),(55,15,85)],1):
        footprint=((yy-cy)/6)**2+((xx-cx)/9)**2<1
        pulse=np.maximum(0,1-np.abs(np.arange(n)-peak)/7)
        movie+=pulse[:,None,None]*footprint[None]*30
        trace=rng.normal(0,.012,n)+pulse*.32
        vox=np.column_stack(np.where((pulse[:,None,None]>.1)&footprint[None]))
        records.append(dict(event_id=eid,voxels=vox,dff=trace,dff_isolated=trace,range=[0,n-1]))
    tifffile.imwrite(path/'raw/movie.ome.tif',movie.astype(np.uint16),metadata={'axes':'TYX'});np.save(path/'raw/time_s.npy',t)
    for name in ('preview.mp4','mean_projection.png','max_projection.png','fov_trace.csv','fov_trace.png'):(path/'raw'/name).touch()
    p.manifest={'schema_version':1,'status':'review','current_run':'runs/example','raw_tiff_sha256':sha256(path/'raw/movie.ome.tif'),'display_limits':[86,126],
      'source':{'source_path':'synthetic_example.oir','shape':[n,h,w],'series_count':1,'channels':1,'z_planes':1,'series':0,'channel':0,'z':0,'interval_s':.5,'pixel_x_um':1,'pixel_y_um':1},
      'acquisition':{'shape':[n,h,w],'interval_s':.5,'pixel_x_um':1,'pixel_y_um':1,'include_experiment':False,'drug_s':None}}
    p.save();save_json(p.run_dir()/'settings.json',{'status':'complete','shape':[n,h,w],'offset_yx':[0,0]})
    _store_events(p,p.run_dir(),records,(n,h,w),(0,0),'synthetic illustration',Job());build_suggestions(p)
    window=MainWindow(path);window.go(2);window.resize(1760,1080);window.show();T.QTest.qWait(200)
    window.status.setText('Synthetic illustration / 合成データによる説明画面（実験結果ではありません）');app.processEvents()
    assert window.grab().save(str(out/'review.png'));window.close()
print(out/'review.png')
