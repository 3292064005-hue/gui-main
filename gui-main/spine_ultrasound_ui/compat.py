from __future__ import annotations

import base64
import importlib.util
import os
import sys
import threading
import types
from pathlib import Path

_MINIMAL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Zz7kAAAAASUVORK5CYII="
)


def enable_runtime_compat() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    os.environ.setdefault("PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION", "python")
    if "PySide6" in sys.modules:
        return
    try:
        spec = importlib.util.find_spec("PySide6")
    except (ImportError, ValueError):
        spec = None
    if spec is None:
        _install_pyside6_stub()


def _install_pyside6_stub() -> None:
    png_bytes = base64.b64decode(_MINIMAL_PNG_BASE64)

    class _BoundSignal:
        def __init__(self) -> None:
            self._slots: list = []

        def connect(self, slot):
            self._slots.append(slot)

        def emit(self, *args, **kwargs):
            for slot in list(self._slots):
                slot(*args, **kwargs)

    class Signal:
        def __init__(self, *args, **kwargs):
            self._storage_name = ""

        def __set_name__(self, owner, name):
            self._storage_name = f"__signal_{name}"

        def __get__(self, instance, owner):
            if instance is None:
                return self
            bound = instance.__dict__.get(self._storage_name)
            if bound is None:
                bound = _BoundSignal()
                instance.__dict__[self._storage_name] = bound
            return bound

    def Slot(*args, **kwargs):
        def decorator(func):
            return func

        return decorator

    class QObject:
        def __init__(self, *args, **kwargs) -> None:
            super().__init__()

    class QByteArray(bytearray):
        pass

    class QIODevice:
        WriteOnly = 1

    class QBuffer:
        def __init__(self, byte_array: QByteArray | None = None):
            self.byte_array = byte_array if byte_array is not None else QByteArray()

        def open(self, mode):
            return True

        def write(self, payload: bytes) -> int:
            self.byte_array.extend(payload)
            return len(payload)

    class _BaseApplication:
        _instance = None

        def __init__(self, args=None):
            type(self)._instance = self
            self.args = list(args or [])

        @classmethod
        def instance(cls):
            return cls._instance

        def exec(self):
            return 0

        def processEvents(self):
            return None

    class QGuiApplication(_BaseApplication):
        pass

    class QApplication(_BaseApplication):
        pass

    class QMessageBox:
        Ok = 0
        Warning = 1
        Critical = 2

        def setIcon(self, *args, **kwargs):
            return None

        def setWindowTitle(self, *args, **kwargs):
            return None

        def setText(self, *args, **kwargs):
            return None

        def setInformativeText(self, *args, **kwargs):
            return None

        def setStandardButtons(self, *args, **kwargs):
            return None

        def exec(self):
            return self.Ok

    class QColor:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class QPixmap:
        def __init__(self, width: int = 1, height: int = 1):
            self.width = int(width)
            self.height = int(height)
            self._png = png_bytes

        def isNull(self) -> bool:
            return self.width <= 0 or self.height <= 0

        def fill(self, color=None) -> None:
            return None

        def save(self, target, fmt: str | None = None) -> bool:
            if isinstance(target, (str, os.PathLike)):
                Path(target).write_bytes(self._png)
                return True
            if hasattr(target, "write"):
                target.write(self._png)
                return True
            return False

    class QPainter:
        Antialiasing = 1

        def __init__(self, pixmap=None):
            self.pixmap = pixmap

        def setRenderHint(self, *args, **kwargs):
            return None

        def setPen(self, *args, **kwargs):
            return None

        def setBrush(self, *args, **kwargs):
            return None

        def drawLine(self, *args, **kwargs):
            return None

        def drawRoundedRect(self, *args, **kwargs):
            return None

        def drawText(self, *args, **kwargs):
            return None

        def drawEllipse(self, *args, **kwargs):
            return None

        def end(self):
            return None

    class QThread(threading.Thread):
        def __init__(self, parent=None):
            super().__init__(daemon=True)
            self.parent = parent

    class QTimer(QObject):
        def __init__(self, parent=None):
            super().__init__()
            self.parent = parent
            self.timeout = _BoundSignal()
            self._stop = threading.Event()
            self._thread: threading.Thread | None = None
            self._interval = 0.0

        def start(self, interval_ms: int):
            self.stop()
            self._stop.clear()
            self._interval = max(float(interval_ms) / 1000.0, 0.001)

            def _run():
                while not self._stop.wait(self._interval):
                    self.timeout.emit()

            self._thread = threading.Thread(target=_run, daemon=True)
            self._thread.start()

        def stop(self):
            self._stop.set()
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=0.1)
            self._thread = None

        def isActive(self) -> bool:
            return self._thread is not None and self._thread.is_alive()

    pyside6_mod = types.ModuleType("PySide6")
    qtcore_mod = types.ModuleType("PySide6.QtCore")
    qtgui_mod = types.ModuleType("PySide6.QtGui")
    qtwidgets_mod = types.ModuleType("PySide6.QtWidgets")

    qtcore_mod.QObject = QObject
    qtcore_mod.Signal = Signal
    qtcore_mod.Slot = Slot
    qtcore_mod.QTimer = QTimer
    qtcore_mod.QThread = QThread
    qtcore_mod.QByteArray = QByteArray
    qtcore_mod.QBuffer = QBuffer
    qtcore_mod.QIODevice = QIODevice

    qtgui_mod.QGuiApplication = QGuiApplication
    qtgui_mod.QColor = QColor
    qtgui_mod.QPainter = QPainter
    qtgui_mod.QPixmap = QPixmap

    qtwidgets_mod.QApplication = QApplication
    qtwidgets_mod.QMessageBox = QMessageBox

    pyside6_mod.QtCore = qtcore_mod
    pyside6_mod.QtGui = qtgui_mod
    pyside6_mod.QtWidgets = qtwidgets_mod

    sys.modules.setdefault("PySide6", pyside6_mod)
    sys.modules.setdefault("PySide6.QtCore", qtcore_mod)
    sys.modules.setdefault("PySide6.QtGui", qtgui_mod)
    sys.modules.setdefault("PySide6.QtWidgets", qtwidgets_mod)
