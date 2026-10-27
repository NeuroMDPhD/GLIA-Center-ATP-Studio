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
window=MainWindow()
window.destination.setText('C:\\ATP_ROA_Projects')
window.on_metadata({'series_count':1,'channels':2,'z_planes':1,'series':0,'channel':0,'z':0,
    'source_path':'example_ATP.oir','shape':[600,256,256],'interval_s':.5,
    'pixel_x_um':.5,'pixel_y_um':.5,'dtype':'uint16'})
window.experiment_group.setChecked(False)
window.status.setText('Illustrative example / 説明用（実データではありません）')
window.show();app.processEvents()
out=ROOT/'docs/screenshots';out.mkdir(exist_ok=True)
assert window.grab().save(str(out/'prepare.png'))
window.close()
print(out/'prepare.png')
