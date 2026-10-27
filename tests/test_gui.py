import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6 import QtWidgets as W
from atp_studio.gui import MainWindow

def test_metadata_autofill_and_manual_override():
    app=W.QApplication.instance() or W.QApplication([]);win=MainWindow()
    m={'series_count':1,'channels':2,'z_planes':1,'series':0,'channel':0,'z':0,'source_path':'example.oir','shape':[100,20,30],
       'interval_s':2,'pixel_x_um':.7,'pixel_y_um':.8,'dtype':'uint16'}
    win.on_metadata(m)
    assert win.dt.value()==2 and win.px.value()==.7 and win.py.value()==.8
    assert not win.override.isChecked()
    win.dt.setValue(3);assert win.override.isChecked()
    win.restore_metadata();assert win.dt.value()==2 and not win.override.isChecked()
    win.on_metadata({**m,'interval_s':None,'pixel_x_um':None,'pixel_y_um':None})
    assert win.dt.value()==0 and win.px.value()==0 and win.override.isChecked()
    win.close()

def test_optional_experiment_preserves_calibration_and_can_be_reenabled():
    app=W.QApplication.instance() or W.QApplication([]);win=MainWindow()
    win.dt.setValue(1);win.px.setValue(.7);win.py.setValue(.8)
    win.fields['animal_id'].setText('mouse123');win.fields['reviewer'].setText('reviewer')
    win.drug.setValue(60)
    win.experiment_group.setChecked(False)
    assert not win.fields['animal_id'].isEnabled() and not win.drug.isEnabled()
    settings=win.preparation_settings()
    assert settings['include_experiment'] is False
    assert settings['interval_s']==1 and settings['pixel_x_um']==.7
    assert not any(k in settings for k in ('animal_id','slice_id','recording_id','condition','reviewer','drug_s'))
    win.experiment_group.setChecked(True)
    assert win.fields['animal_id'].isEnabled()
    assert win.preparation_settings()['animal_id']=='mouse123'
    assert win.preparation_settings()['drug_s']==60
    win.close()
