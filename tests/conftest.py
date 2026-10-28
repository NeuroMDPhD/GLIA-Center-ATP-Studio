"""Keep Qt alive until every test window has been disposed on its GUI thread."""
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import pytest
from PySide6 import QtCore as C, QtWidgets as W


@pytest.fixture(scope='session', autouse=True)
def qapp():
    app = W.QApplication.instance() or W.QApplication([])
    yield app
    C.QCoreApplication.sendPostedEvents(None, C.QEvent.Type.DeferredDelete)


@pytest.fixture(autouse=True)
def dispose_test_windows(qapp):
    yield
    for widget in qapp.topLevelWidgets():
        worker = getattr(widget, 'worker', None)
        if worker is not None and worker.isRunning():
            worker.job.cancel.set()
            assert worker.wait(5000), 'Worker must stop before window disposal'
        widget.close()
        widget.deleteLater()
    C.QCoreApplication.sendPostedEvents(None, C.QEvent.Type.DeferredDelete)
    qapp.processEvents()
