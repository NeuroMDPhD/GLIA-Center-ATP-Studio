"""Check interpreter exit too: in-process assertions cannot catch shutdown crashes."""
import os
from pathlib import Path
import subprocess
import sys
import pytest


@pytest.mark.parametrize('mode', ['idle', 'adjustment', 'cancel'])
def test_gui_entrypoint_exits_cleanly(mode):
    script = r'''
import sys
from PySide6 import QtCore as C, QtWidgets as W
from atp_studio import gui

mode = sys.argv.pop()
BaseWindow = gui.MainWindow
class SmokeWindow(BaseWindow):
    def __init__(self, *args):
        super().__init__(*args)
        C.QTimer.singleShot(30, self.exercise)
    def exercise(self):
        if mode == 'adjustment':
            self.go(1)
            panel = self.detection_panel
            panel.setCurrentIndex(1)
            panel.issue.setCurrentIndex(panel.issue.findData('noise'))
            panel.apply_proposal()
            panel.undo()
        elif mode == 'cancel':
            self.run_job(lambda job: job.cancel.wait(4), lambda result: None)
            self.worker.finished.connect(self.close)
            self.close()
            assert self.isVisible(), 'Close must wait for the worker'
            return
        self.close()
gui.MainWindow = SmokeWindow
gui.main()
'''
    env = {**os.environ, 'QT_QPA_PLATFORM': 'offscreen'}
    result = subprocess.run([sys.executable, '-c', script, mode], env=env,
                            cwd=Path(__file__).resolve().parents[1],
                            capture_output=True, text=True, timeout=20)
    assert result.returncode == 0, result.stdout + result.stderr
    for error in ('Segmentation fault', 'shared QObject', 'Traceback', 'QThread: Destroyed'):
        assert error not in result.stderr, result.stderr
