import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import json
import numpy as np
import pytest
import tifffile
from PySide6 import QtWidgets as W
from atp_studio.detection_guidance import (DEFAULT_DETECTION, LEGACY_DETECTION, PARAMETERS,
    bounds, validate_settings, recommend, match_issues, calibrated_value)
from atp_studio.detection_panel import DetectionPanel
from atp_studio.project import Project, detect
from atp_studio.common import Job, sha256

CONTEXT = dict(shape=[180, 384, 512], interval_s=2, pixel_x_um=1.125, pixel_y_um=1.125)


def test_stricter_defaults_preserve_segmentation_and_previous_preset():
    changed = {key for key in DEFAULT_DETECTION if DEFAULT_DETECTION[key] != LEGACY_DETECTION[key]}
    assert changed == {'thrARScl', 'minSize', 'minDur', 'sigThr'}
    assert [DEFAULT_DETECTION[k] for k in ('thrARScl', 'minSize', 'minDur', 'sigThr')] == [3.5, 30, 6, 4.0]
    assert validate_settings(DEFAULT_DETECTION, CONTEXT) == DEFAULT_DETECTION
    assert LEGACY_DETECTION['thrARScl'] == 3.0 and LEGACY_DETECTION['minDur'] == 5


@pytest.mark.parametrize('issue,key,value', [
    ('noise', 'thrARScl', 4.0), ('weak', 'thrARScl', 3.0), ('small_noise', 'minSize', 38),
    ('brief_noise', 'minDur', 7), ('short_missed', 'minDur', 5),
    ('spatial_merged', 'sourceSensitivity', 9), ('spatial_split', 'sourceSensitivity', 7),
    ('temporal_merged', 'maxDelay', .5), ('temporal_split', 'maxDelay', .7), ('edge', 'regMaskGap', 6),
])
def test_guidance_changes_one_relevant_parameter_without_mutating_input(issue, key, value):
    settings = dict(DEFAULT_DETECTION)
    result = recommend(issue, settings, CONTEXT)
    assert settings == DEFAULT_DETECTION
    assert result['after'] == {**settings, key: value}
    assert result['changes'][0]['effect'] and result['changes'][0]['caution']
    assert len(result['changes']) == 1


def test_limits_rounding_and_recording_specific_units():
    assert recommend('noise', {**DEFAULT_DETECTION, 'thrARScl': 20}, CONTEXT)['changes'] == []
    assert recommend('spatial_merged', {**DEFAULT_DETECTION, 'sourceSensitivity': 10}, CONTEXT)['changes'] == []
    assert recommend('temporal_merged', {**DEFAULT_DETECTION, 'maxDelay': .05}, CONTEXT)['after']['maxDelay'] == 0
    assert bounds('minDur', CONTEXT) == (1, 180)
    assert bounds('movAvgWin', CONTEXT) == (2, 180)
    assert bounds('regMaskGap', {'shape':[60,20,20]}) == (0, 7)
    assert '37.9688' in calibrated_value('minSize', 30, CONTEXT)
    assert '12 s' in calibrated_value('minDur', 6, CONTEXT)
    assert '180 frames' in calibrated_value('cut', 200, CONTEXT)
    assert '360 s' in calibrated_value('cut', 200, CONTEXT)


@pytest.mark.parametrize('key,value', [('sourceSensitivity',11),('sourceSensitivity',0),
    ('sourceSzRatio',1.1),('sigThr',float('nan')),('thrARScl',float('inf')),
    ('minDur',1.5),('minDur',181),('movAvgWin',1001),('cut',10000),('memory_gb',True),('regMaskGap',-1)])
def test_invalid_ranges_fail_before_detection(key,value):
    with pytest.raises(ValueError):
        validate_settings({**DEFAULT_DETECTION,key:value},CONTEXT)


def test_no_numeric_fix_for_uninterpretable_problems_and_ambiguous_text():
    for key in ('drift','motion','memory'):
        result=recommend(key,DEFAULT_DETECTION,CONTEXT)
        assert result['changes']==[] and result['after']==DEFAULT_DETECTION
    assert match_issues('the colors look strange')==[]
    assert match_issues('ノイズ')==['noise']
    assert {'noise','spatial_merged'} <= set(match_issues('too many events are merged'))


@pytest.fixture
def panel():
    app=W.QApplication.instance() or W.QApplication([])
    panel=DetectionPanel(lambda:CONTEXT)
    panel.resize(1300,520);panel.show();app.processEvents()
    yield panel
    panel.close();app.processEvents()


def choose(panel, key):
    panel.issue.setCurrentIndex(panel.issue.findData(key))


def test_preview_apply_undo_and_stale_preview(panel):
    choose(panel,'noise')
    assert panel.settings()==DEFAULT_DETECTION and panel.apply_btn.isEnabled()
    assert panel.preview_table.minimumHeight() >= 100
    panel.apply_proposal()
    assert panel.params['thrARScl'].value()==4.0 and panel.undo_btn.isEnabled()
    assert not panel.apply_btn.isEnabled()
    panel.apply_proposal()
    assert panel.params['thrARScl'].value()==4.0
    assert panel.guidance_for_run()['after']==panel.settings()
    panel.undo()
    assert panel.settings()==DEFAULT_DETECTION and panel.guidance_for_run() is None
    panel.preview();panel.params['minSize'].setValue(31)
    assert not panel.apply_btn.isEnabled()
    panel.apply_proposal()
    assert panel.params['thrARScl'].value()==3.5


def test_manual_changes_protect_undo_and_project_changes_clear_advice(panel):
    choose(panel,'spatial_merged');panel.apply_proposal()
    panel.params['minSize'].setValue(32)
    assert not panel.undo_btn.isEnabled() and panel.guidance_for_run() is None
    panel.undo();assert panel.params['minSize'].value()==32
    panel.refresh_context(previous=LEGACY_DETECTION,reset=True)
    assert panel.previous_btn.isEnabled() and panel.proposal is None
    panel.load_previous();assert panel.settings()==LEGACY_DETECTION
    panel.apply_preset(DEFAULT_DETECTION,'strict_defaults');assert panel.settings()==DEFAULT_DETECTION


def test_search_asks_for_disambiguation_and_never_applies(panel):
    panel.description.setText('too many events are merged');panel.search_issues()
    assert panel.issue.currentData() is None and not panel.apply_btn.isEnabled()
    panel.description.setText('ノイズ');panel.search_issues()
    assert panel.issue.currentData()=='noise' and panel.settings()==DEFAULT_DETECTION
    panel.description.setText('something else');panel.search_issues()
    assert panel.issue.currentData() is None and not panel.apply_btn.isEnabled()


def test_parameter_values_and_guidance_reach_saved_run_and_java_request(tmp_path, monkeypatch):
    p=Project(tmp_path);(tmp_path/'raw').mkdir();(tmp_path/'runs').mkdir()
    pixels=np.ones((60,24,24),dtype=np.uint16)*100
    tifffile.imwrite(tmp_path/'raw/movie.ome.tif',pixels,metadata={'axes':'TYX'})
    np.save(tmp_path/'raw/time_s.npy',np.arange(60,dtype=float))
    p.manifest={'raw_tiff_sha256':sha256(tmp_path/'raw/movie.ome.tif'),
                'acquisition':dict(shape=[60,24,24],interval_s=1,pixel_x_um=1,pixel_y_um=1)}
    p.save()
    monkeypatch.setattr('atp_studio.project.java_command',lambda *args:['java'])
    class StopBeforeEngine(Job):
        def run(self,*args):raise RuntimeError('Stopped before engine')
    advice=recommend('spatial_merged',DEFAULT_DETECTION,p.manifest['acquisition'])
    with pytest.raises(RuntimeError,match='Stopped before engine'):
        detect(p,advice['after'],StopBeforeEngine(),guidance=advice)
    run=next((tmp_path/'runs').iterdir())
    saved=json.loads((run/'settings.json').read_text())
    assert saved['parameter_guidance']==advice and saved['settings']==advice['after']
    props=dict(line.split('=',1) for line in (run/'request.properties').read_text().splitlines())
    assert props['sourceSensitivity']=='9' and props['maxDelay']=='0.6'
    assert props['thrARScl']=='3.5' and props['minSize']=='30' and props['minDur']=='6' and props['sigThr']=='4.0'
    assert 'parameter_guidance' not in props
    count=len(list((tmp_path/'runs').iterdir()))
    with pytest.raises(ValueError):detect(p,{**DEFAULT_DETECTION,'cut':10000},StopBeforeEngine())
    assert len(list((tmp_path/'runs').iterdir()))==count
