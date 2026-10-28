import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from threading import Event
import time
import pytest
from PIL import Image
from PySide6 import QtCore as C, QtGui as G, QtWidgets as W, QtTest as T
from atp_studio.common import ROOT, Cancelled
from atp_studio.gui import MainWindow
from atp_studio.processing import ProcessingIndicator


def wait_until(condition, timeout=3000):
    end = time.monotonic() + timeout / 1000
    while not condition() and time.monotonic() < end:
        T.QTest.qWait(10)
    assert condition(), 'Timed out waiting for the background task / GUI'


@pytest.fixture
def window():
    app = W.QApplication.instance() or W.QApplication([])
    win = MainWindow()
    win.show()
    app.processEvents()
    yield win
    if win.worker and win.worker.isRunning():
        win.worker.job.cancel.set()
        assert win.worker.wait(5000)
    app.processEvents()
    win.close()


def test_gif_has_motion_loop_timing_and_transparent_background():
    with Image.open(ROOT / 'assets/professor/working.gif') as gif:
        assert gif.n_frames == 6 and gif.size == (192, 208)
        assert gif.info['loop'] == 0
        pixels, durations = set(), []
        for n in range(gif.n_frames):
            gif.seek(n)
            rgba = gif.convert('RGBA')
            assert rgba.getpixel((0, 0))[3] == 0
            pixels.add(rgba.tobytes())
            durations.append(gif.info['duration'])
        assert len(pixels) == 6
        assert durations == [120, 120, 120, 120, 120, 220]


def test_animation_and_clock_stay_live_during_work_and_stop_on_success(window):
    release = Event()
    results, frames = [], []
    window.processing.movie.frameChanged.connect(frames.append)
    assert window.processing.isHidden()
    window.run_job(lambda job: (release.wait(4), 'complete')[1], results.append)
    try:
        assert window.processing.isVisible()
        wait_until(lambda: len(set(frames)) >= 3)
        wait_until(lambda: '00:00' not in window.processing.elapsed_label.text())
        assert window.worker.isRunning()
        assert window.processing.movie.state() == G.QMovie.MovieState.Running
        assert window.cancel_btn.isEnabled()
    finally:
        release.set()
    wait_until(lambda: not window.cancel_btn.isEnabled())
    assert results == ['complete']
    assert window.processing.isHidden() and not window.processing.clock.isActive()
    assert window.processing.movie.state() == G.QMovie.MovieState.NotRunning
    # A second task must restart the animation and reset the elapsed clock.
    release.clear()
    window.run_job(lambda job: release.wait(4), lambda result: None)
    try:
        assert '00:00' in window.processing.elapsed_label.text()
        assert window.processing.movie.state() == G.QMovie.MovieState.Running
    finally:
        release.set()
    wait_until(lambda: not window.cancel_btn.isEnabled())


def test_cancel_keeps_animation_until_worker_acknowledges(window, monkeypatch):
    release, acknowledged = Event(), Event()
    monkeypatch.setattr(W.QMessageBox, 'exec', lambda box: 0)
    def work(job):
        if job.cancel.wait(4):
            acknowledged.set()
            release.wait(4)
            raise Cancelled('Cancelled / 中止')
    window.run_job(work, lambda result: pytest.fail('Cancellation must not succeed'))
    try:
        window.cancel()
        wait_until(acknowledged.is_set)
        assert window.processing.isVisible()
        assert window.processing.movie.state() == G.QMovie.MovieState.Running
        assert 'Stopping' in window.processing.state.text()
    finally:
        release.set()
    wait_until(lambda: not window.cancel_btn.isEnabled())
    assert window.processing.isHidden() and not window.processing.clock.isActive()


def test_failure_stops_animation_before_error_dialog(window, monkeypatch):
    seen = []
    def dialog(box):
        assert window.processing.isHidden()
        assert window.processing.movie.state() == G.QMovie.MovieState.NotRunning
        seen.append(box.text())
        return 0
    monkeypatch.setattr(W.QMessageBox, 'exec', dialog)
    def work(job):
        raise RuntimeError('Synthetic failure')
    window.run_job(work, lambda result: pytest.fail('Failure must not succeed'))
    wait_until(lambda: not window.cancel_btn.isEnabled())
    assert seen and 'Synthetic failure' in seen[0]


def test_missing_animation_keeps_text_feedback_available(tmp_path):
    app = W.QApplication.instance() or W.QApplication([])
    widget = ProcessingIndicator(animation_path=tmp_path / 'missing.gif')
    widget.start()
    app.processEvents()
    assert widget.isVisible() and widget.clock.isActive()
    assert widget.state.text() == 'Working / 処理中'
    widget.stop()
    assert widget.isHidden() and not widget.clock.isActive()
    widget.close()
