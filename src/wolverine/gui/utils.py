"""Shared GUI utilities."""

from PyQt6.QtCore import QRunnable, QObject, QThreadPool, pyqtSignal


class _Signals(QObject):
    done = pyqtSignal(object)
    error = pyqtSignal(str)


class _Task(QRunnable):
    def __init__(self, fn):
        super().__init__()
        self.signals = _Signals()
        self._fn = fn

    def run(self):
        try:
            self.signals.done.emit(self._fn())
        except Exception as e:
            self.signals.error.emit(str(e))


def run_task(fn, done_cb, error_cb=None):
    t = _Task(fn)
    t.signals.done.connect(done_cb)
    if error_cb:
        t.signals.error.connect(error_cb)
    QThreadPool.globalInstance().start(t)
