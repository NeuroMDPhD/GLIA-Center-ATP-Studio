"""Professor activity indicator driven by the background worker's lifecycle."""
from PySide6 import QtCore as C, QtGui as G, QtWidgets as W
from .common import ROOT


class ProcessingIndicator(W.QFrame):
    def __init__(self, parent=None, animation_path=None):
        super().__init__(parent)
        self.setObjectName('processingIndicator')
        self.setAccessibleName('Task progress / 処理状況')
        self.setToolTip('Processing. Please wait. / 処理中です。しばらくお待ちください。')
        layout = W.QVBoxLayout(self)
        layout.setContentsMargins(4, 8, 4, 8)
        layout.setSpacing(3)
        self.image = W.QLabel()
        self.image.setFixedSize(128, 139)
        self.image.setAlignment(C.Qt.AlignmentFlag.AlignCenter)
        self.image.setAccessibleName('Professor')
        layout.addWidget(self.image, 0, C.Qt.AlignmentFlag.AlignHCenter)
        self.state = W.QLabel()
        self.state.setAlignment(C.Qt.AlignmentFlag.AlignCenter)
        self.state.setWordWrap(True)
        self.elapsed_label = W.QLabel()
        self.elapsed_label.setObjectName('muted')
        self.elapsed_label.setAlignment(C.Qt.AlignmentFlag.AlignCenter)
        self.elapsed_label.setWordWrap(True)
        layout.addWidget(self.state)
        layout.addWidget(self.elapsed_label)
        path = animation_path if animation_path is not None else ROOT / 'assets/professor/working.gif'
        self.movie = G.QMovie(str(path), parent=self)
        self.movie.setCacheMode(G.QMovie.CacheMode.CacheAll)
        self.movie.setScaledSize(C.QSize(128, 139))
        if self.movie.isValid():
            self.image.setMovie(self.movie)
        else:
            # An asset problem must not prevent analysis or hide its status.
            self.image.setText('…')
        self.elapsed = C.QElapsedTimer()
        self.clock = C.QTimer(self)
        self.clock.setInterval(1000)
        self.clock.timeout.connect(self.update_elapsed)
        self.hide()

    def start(self):
        self.state.setText('Working / 処理中')
        self.elapsed.start()
        self.update_elapsed()
        self.show()
        self.clock.start()
        if self.movie.isValid():
            self.movie.start()

    def request_stop(self):
        self.state.setText('Stopping… / 中止処理中…')

    def stop(self):
        self.movie.stop()
        self.clock.stop()
        self.hide()

    def update_elapsed(self):
        seconds = max(0, self.elapsed.elapsed() // 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        value = f'{hours:02}:{minutes:02}:{seconds:02}' if hours else f'{minutes:02}:{seconds:02}'
        self.elapsed_label.setText(f'Elapsed / 経過 {value}')
