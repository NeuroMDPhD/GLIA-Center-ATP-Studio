import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import numpy as np
import pytest
import tifffile
from PySide6 import QtCore as C, QtWidgets as W, QtTest as T, QtGui as G
from atp_studio.project import Project, _store_events
from atp_studio.common import save_json, sha256, Job
from atp_studio.suggestions import assess_event, build_suggestions, cached_suggestions, validate_config
from atp_studio.gui import MainWindow
from atp_studio.theme import install_fonts

@pytest.fixture
def review_project(tmp_path):
    p=Project(tmp_path)
    for d in ('raw','runs/test','exports'): (tmp_path/d).mkdir(parents=True)
    rng=np.random.default_rng(42);n=80;movie=rng.integers(95,106,(n,32,40),dtype=np.uint16)
    t=np.arange(n,dtype=float);records=[]
    for eid in range(1,6):
        y=rng.normal(0,.02,n);y[32:38]+=.5
        vox=np.array([[i,j,k] for i in range(32,38) for j in range(4+eid,7+eid) for k in range(8,11)])
        movie[32:38,6+eid:9+eid,10:13]+=30
        records.append(dict(event_id=eid,voxels=vox,dff=y,dff_isolated=y,range=[0,n-1]))
    tifffile.imwrite(tmp_path/'raw/movie.ome.tif',movie,metadata={'axes':'TYX'});np.save(tmp_path/'raw/time_s.npy',t)
    for name in ('preview.mp4','mean_projection.png','max_projection.png','fov_trace.csv','fov_trace.png'):(tmp_path/'raw'/name).touch()
    p.manifest={'schema_version':1,'status':'review','current_run':'runs/test','raw_tiff_sha256':sha256(tmp_path/'raw/movie.ome.tif'),'display_limits':[90,140],
      'source':{'source_path':'synthetic.oir','shape':[n,32,40],'series_count':1,'channels':1,'z_planes':1,'series':0,'channel':0,'z':0,'interval_s':1,'pixel_x_um':1,'pixel_y_um':1},
      'acquisition':{'shape':[n,32,40],'interval_s':1,'pixel_x_um':1,'pixel_y_um':1,'include_experiment':True,'drug_s':None}}
    p.save();save_json(p.run_dir()/'settings.json',{'status':'complete','shape':[n,28,36],'offset_yx':[2,2]})
    _store_events(p,p.run_dir(),records,(n,28,36),(2,2),'synthetic',Job())
    return p

def test_suggestions_signal_and_caution(review_project):
    p=review_project;before=(p.run_dir()/'review.json').read_bytes();doc=build_suggestions(p)
    assert {r['category'] for r in doc['events'].values()}=={'signal'}
    assert all(r['pixel_support']==1 for r in doc['events'].values())
    assert (p.run_dir()/'review.json').read_bytes()==before
    assert cached_suggestions(p)==doc
    d=p.event_data(1);event=p.events()[0];args=(d['dff'],d['voxels'],[80,28,36])
    caution=assess_event(*args,{**event,'touches_analysis_edge':True},movie=p.movie(),offset=(2,2))
    assert caution['category']=='review' and 'edge' in caution['reason_codes']
    weak=d['dff'].copy();weak[32:38]=.001
    assert assess_event(weak,args[1],args[2],event)['category']=='noise'
    brief=d['dff'].copy();brief[32:38]=0;brief[34]=.5
    result=assess_event(brief,args[1],args[2],event,movie=p.movie(),offset=(2,2))
    assert result['category']=='review' and 'brief_peak' in result['reason_codes']
    broken=d['dff'].copy();broken[0]=np.nan
    assert assess_event(broken,args[1],args[2],event)['reason_codes']==['nonfinite']
    assert assess_event(np.zeros(80),args[1],args[2],event)['reason_codes']==['noise_undefined']
    longvox=np.array([[i,5,8] for i in range(2,78)])
    assert assess_event(d['dff'],longvox,args[2],event)['reason_codes']==['baseline_short']

def test_suggestion_cache_and_thresholds(review_project):
    import h5py
    p=review_project;build_suggestions(p)
    with h5py.File(p.run_dir()/'events.h5','r+') as f:f['1/dff'][0]=.123
    assert cached_suggestions(p) is None
    build_suggestions(p,{'signal_snr':100});assert cached_suggestions(p)['config']['signal_snr']==100
    with pytest.raises(ValueError):validate_config({'signal_snr':float('inf')})
    with pytest.raises(ValueError):validate_config({'noise_snr':6})

def test_batch_review_validation_notes_and_undo(review_project):
    p=review_project;p.review_event(1,'hold','note one');p.review_event(2,'pending','note two')
    original=p.review();snapshot=p.review_events([1,2],'accepted')
    assert p.review()['1']['note']=='note one' and p.review()['2']['note']=='note two'
    assert p.review()['3']==original['3']
    p.restore_reviews(snapshot)
    for eid in ('1','2'):
        assert p.review()[eid]['status']==original[eid]['status']
        assert p.review()[eid]['note']==original[eid]['note']
    before=p.review()
    with pytest.raises(ValueError):p.review_events([1,999],'rejected')
    assert before==p.review()
    entries=[json.loads(x) for x in (p.run_dir()/'review_history.jsonl').read_text().splitlines()]
    assert entries[-1]['action']=='undo' and entries[-1]['batch_size']==2

@pytest.fixture
def review_window(review_project):
    app=W.QApplication.instance() or W.QApplication([]);install_fonts(app);build_suggestions(review_project)
    win=MainWindow(review_project.path);win.go(2);win.show();win.activateWindow();win.table.setFocus();T.QTest.qWait(100)
    yield win,app
    win.close();app.processEvents()

def test_shift_selection_keyboard_and_note_guard(review_window):
    win,app=review_window
    def click(row,mod=C.Qt.KeyboardModifier.NoModifier):
        pos=win.table.visualItemRect(win.table.item(row,0)).center()
        T.QTest.mouseClick(win.table.viewport(),C.Qt.MouseButton.LeftButton,mod,pos);app.processEvents()
    click(0);click(2,C.Qt.KeyboardModifier.ShiftModifier)
    assert win.selected_event_ids()==[1,2,3]
    T.QTest.keyClick(win.table,C.Qt.Key.Key_A);app.processEvents()
    assert all(win.project.review()[str(i)]['status']=='accepted' for i in [1,2,3])
    assert win.project.review()['4']['status']=='pending'
    T.QTest.keySequence(win.table,G.QKeySequence(G.QKeySequence.StandardKey.Undo));app.processEvents();assert all(win.project.review()[str(i)]['status']=='pending' for i in [1,2,3])
    win.note.setFocus();app.processEvents();T.QTest.keyClicks(win.note,'a rh u');app.processEvents()
    assert win.note.text()=='a rh u' and win.project.review()['1']['status']=='pending'
    win.table.setFocus();click(0);T.QTest.keyClick(win.table,C.Qt.Key.Key_Return);app.processEvents()
    assert win.project.review()['1']['status']=='accepted' and win.selected_id==2
    T.QTest.keyClick(win.table,C.Qt.Key.Key_R);app.processEvents();assert win.project.review()['2']['status']=='rejected'
    T.QTest.keyClick(win.table,C.Qt.Key.Key_H);app.processEvents();assert win.project.review()['3']['status']=='hold'
    win.filter.setCurrentIndex(1);click(0);T.QTest.keyClick(win.table,C.Qt.Key.Key_A);app.processEvents()
    assert win.selected_id==5

def test_dual_view_coordinates_and_playback_position(review_window):
    win,app=review_window
    assert win.playback.mapTo(win,C.QPoint()).y()>=win.plot.mapTo(win,C.QPoint()).y()+win.plot.height()
    win.slider.setValue(35);app.processEvents()
    assert np.array_equal(win.image.image,win.zoom_image.image)
    assert np.array_equal(win.overlay.image,win.zoom_overlay.image)
    full=win.view.viewRange();zoom=win.zoom_view.viewRange()
    assert full[0][0]<=0 and full[0][1]>=40 and full[1][0]<=0 and full[1][1]>=32
    assert zoom[0][1]-zoom[0][0]<full[0][1]-full[0][0]
    assert win.zoom_box.rect().contains(C.QPointF(10,7))
    assert 'IBM Plex Sans' in G.QFontDatabase.families() and 'IBM Plex Sans JP' in G.QFontDatabase.families()


def test_suggestions_exported_without_changing_decisions(review_project):
    import csv
    from pathlib import Path
    from atp_studio.project import export_selected
    p=review_project;p.review_events([1,2],'accepted');before=p.review()
    out=Path(export_selected(p,False));doc=json.loads((out/'review_suggestions.json').read_text())
    with (out/'selected_events.csv').open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
    assert [r['event_id'] for r in rows]==['1','2']
    assert rows[0]['suggestion']=='signal' and rows[0]['suggestion_rule_version']==doc['rule_version']
    assert p.review()==before

def test_small_window_scrolls_without_covering_controls(review_window):
    win,app=review_window;win.resize(1280,900);T.QTest.qWait(100)
    page=win.stack.widget(2)
    assert page.verticalScrollBar().maximum()==0
    assert win.plot.mapTo(win,C.QPoint()).y()>=win.canvas.mapTo(win,C.QPoint()).y()+win.canvas.height()-1
    win.resize(1000,700);T.QTest.qWait(100)
    assert page.verticalScrollBar().maximum()>0
    page.verticalScrollBar().setValue(page.verticalScrollBar().maximum());app.processEvents()
    assert win.undo_btn.mapTo(win,C.QPoint()).y()+win.undo_btn.height()<win.height()
