from pathlib import Path
import csv
import numpy as np
import tifffile
from atp_studio.project import Project, _store_events, export_selected, resolve_times, detect
from atp_studio.project import applied_settings, EXPERIMENT_FIELDS
from atp_studio.common import Job, save_json, sha256
import pytest

@pytest.fixture
def project(tmp_path):
    p=Project(tmp_path);(tmp_path/'raw').mkdir();(tmp_path/'runs/test').mkdir(parents=True);(tmp_path/'exports').mkdir()
    t=np.arange(40,dtype=float);movie=np.ones((40,12,14),dtype=np.uint16)*100
    tifffile.imwrite(tmp_path/'raw/movie.ome.tif',movie,metadata={'axes':'TYX'});np.save(tmp_path/'raw/time_s.npy',t)
    p.manifest={'schema_version':1,'current_run':'runs/test','raw_tiff_sha256':sha256(tmp_path/'raw/movie.ome.tif'),'display_limits':[0,200],
        'acquisition':{'shape':[40,12,14],'pixel_x_um':2,'pixel_y_um':2,'interval_s':1,'animal_id':'mouse1','slice_id':'s1','recording_id':'r1','condition':'test','reviewer':'tester'}}
    p.save();run=p.run_dir();save_json(run/'settings.json',{'status':'complete','shape':[40,8,10],'offset_yx':[2,2]})
    y=np.maximum(0,1-abs(t-15)/8);v=np.array([[i,2,3] for i in range(8,23)])
    _store_events(p,run,[dict(event_id=7,voxels=v,dff=y,dff_isolated=y,range=[0,39],favorite_hint=True)],(40,8,10),(2,2),'synthetic',Job())
    return p

def test_favorite_is_not_automatic_acceptance(project):
    assert project.events()[0]['favorite_hint']
    assert project.review()['7']['status']=='pending'

def test_review_persistence_and_export_coordinates(project):
    project.review_event(7,'accepted','checked','QA')
    again=Project(project.path);assert again.review()['7']['note']=='checked'
    out=Path(export_selected(again,False));rows=list(csv.DictReader(open(out/'selected_events.csv',encoding='utf-8-sig')))
    assert len(rows)==1 and rows[0]['event_id']=='7' and rows[0]['animal_id']=='mouse1'
    assert float(rows[0]['centroid_x_source_px'])==5 and float(rows[0]['centroid_y_source_px'])==4
    mask=tifffile.imread(out/'selected_ROA_masks.tif');assert mask.sum()==1 and mask.squeeze()[4,5]==1
    assert 'before' in (project.run_dir()/'review_history.jsonl').read_text()

def test_zero_selection_exports_header_and_summary(project):
    out=Path(export_selected(project,False));assert len(list(csv.DictReader(open(out/'selected_events.csv',encoding='utf-8-sig'))))==0
    assert (out/'recording_summary.csv').exists()

def test_manual_and_original_timing():
    m={'shape':[3,4,4],'plane_times_s':[2,4,7]}
    t,src=resolve_times(m,1,False);assert t.tolist()==[0,2,5]
    t,src=resolve_times(m,.5,True);assert t.tolist()==[0,.5,1]

def test_unequal_pixel_calibration_is_rejected(project):
    project.manifest['acquisition']['pixel_y_um']=3;project.save()
    with pytest.raises(ValueError,match='Square pixels'):detect(project,{})

def test_invalid_review_state_rejected(project):
    with pytest.raises(ValueError):project.review_event(7,'bogus')
    with pytest.raises(ValueError):project.review_event(999,'accepted')

def test_modified_prepared_movie_blocks_export(project):
    movie=tifffile.memmap(project.path/'raw/movie.ome.tif',mode='r+')
    movie[0,0,0]+=1;movie.flush();del movie
    with pytest.raises(ValueError,match='TIFF has changed'):export_selected(project,False)

def test_experiment_opt_out_is_persisted_and_omitted_from_exports(project):
    project.manifest['acquisition']=applied_settings({**project.manifest['acquisition'],'include_experiment':False})
    project.save();p=Project(project.path)
    assert p.manifest['acquisition']['include_experiment'] is False
    assert not any(k in p.manifest['acquisition'] for k in EXPERIMENT_FIELDS)
    p.review_event(7,'accepted','chosen','should not be recorded')
    assert 'reviewer' not in p.review()['7']
    out=Path(export_selected(p,False))
    for name in ('selected_events.csv','review_all_events.csv','recording_summary.csv'):
        with (out/name).open(encoding='utf-8-sig') as f:rows=list(csv.DictReader(f))
        assert rows
        assert not any(k in rows[0] for k in EXPERIMENT_FIELDS)
    assert 'should not be recorded' not in (out/'manifest.json').read_text()
