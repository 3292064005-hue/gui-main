from __future__ import annotations

import base64
import os
import sys
import threading
import types
from pathlib import Path

_MINIMAL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Zz7kAAAAASUVORK5CYII="
)


def install_pyside6_stub() -> None:
    if "PySide6" in sys.modules:
        return

    png_bytes = base64.b64decode(_MINIMAL_PNG_BASE64)

    class _BoundSignal:
        def __init__(self) -> None:
            self._slots: list = []
            self._connections: list[tuple] = []

        def connect(self, slot, connection_type=None):
            self._slots.append(slot)
            self._connections.append((slot, connection_type))

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
            self.aboutToQuit = _BoundSignal()

        @classmethod
        def instance(cls):
            return cls._instance

        def exec(self):
            return 0

        def processEvents(self):
            return None

        def setApplicationName(self, name: str) -> None:
            self.application_name = name

        def setOrganizationName(self, name: str) -> None:
            self.organization_name = name

    class QGuiApplication(_BaseApplication):
        pass

    class QApplication(_BaseApplication):
        pass

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

        def scaled(self, *args, **kwargs):
            return self

    class QPainter:
        Antialiasing = 1

        def __init__(self, pixmap=None):
            self.pixmap = pixmap

        def setRenderHint(self, *args, **kwargs): return None
        def setPen(self, *args, **kwargs): return None
        def setBrush(self, *args, **kwargs): return None
        def drawLine(self, *args, **kwargs): return None
        def drawRoundedRect(self, *args, **kwargs): return None
        def drawText(self, *args, **kwargs): return None
        def drawEllipse(self, *args, **kwargs): return None
        def drawPixmap(self, *args, **kwargs): return None
        def end(self): return None

    class _Widget(QObject):
        def __init__(self, *args, **kwargs):
            super().__init__()
            self._text = ""
            self._layout = None
            self._children = []
            self.clicked = _BoundSignal()
            self.triggered = _BoundSignal()
            self.currentTextChanged = _BoundSignal()
            self.textChanged = _BoundSignal()
            self.itemSelectionChanged = _BoundSignal()
            self._header = None

        def show(self): return None
        def close(self): return None
        def setLayout(self, layout): self._layout = layout
        def layout(self): return self._layout
        def addWidget(self, widget): self._children.append(widget)
        def addLayout(self, layout): self._children.append(layout)
        def setText(self, text): self._text = str(text)
        def text(self): return self._text
        def setPlainText(self, text): self._text = str(text)
        def toPlainText(self): return self._text
        def append(self, text): self._text += ("\n" if self._text else "") + str(text)
        def clear(self): self._text = ""
        def setInformativeText(self, text): self._informative_text = str(text)
        def setWindowTitle(self, title): self._title = str(title)
        def setIcon(self, icon): self._icon = icon
        def setStandardButtons(self, buttons): self._buttons = buttons
        def exec(self): return 0
        def setPixmap(self, pixmap): self._pixmap = pixmap
        def setWordWrap(self, value): self._word_wrap = bool(value)
        def setAlignment(self, value): self._alignment = value
        def setObjectName(self, value): self._object_name = value
        def setStyleSheet(self, value): self._style = value
        def setReadOnly(self, value): self._read_only = bool(value)
        def setEnabled(self, value): self._enabled = bool(value)
        def setValue(self, value): self._value = value
        def value(self): return getattr(self, "_value", 0)
        def setRange(self, low, high): self._range = (low, high)
        def setMinimumWidth(self, value): self._min_width = value
        def setMinimumHeight(self, value): self._min_height = value
        def setMaximumWidth(self, value): self._max_width = value
        def setMaximumHeight(self, value): self._max_height = value
        def setCentralWidget(self, widget): self._central_widget = widget
        def addAction(self, action): self._children.append(action)
        def addMenu(self, menu): self._children.append(menu); return menu
        def setModel(self, model): self._model = model
        def model(self): return getattr(self, "_model", None)
        def horizontalHeader(self):
            if self._header is None:
                self._header = QHeaderView()
            return self._header

    class QWidget(_Widget):
        pass

    class QFrame(QWidget):
        pass

    class QLabel(QWidget):
        pass

    class QTextEdit(QWidget):
        pass

    class QPushButton(QWidget):
        pass

    class QGroupBox(QWidget):
        pass

    class QProgressBar(QWidget):
        pass

    class QListWidget(QWidget):
        pass

    class QListWidgetItem:
        def __init__(self, text=""):
            self._text = text

    class QSplitter(QWidget):
        pass

    class QTableView(QWidget):
        pass

    class QComboBox(QWidget):
        def addItems(self, items):
            self._items = list(items)

        def currentText(self):
            return self._text or (self._items[0] if getattr(self, "_items", []) else "")

    class QLineEdit(QWidget):
        @property
        def editingFinished(self):
            return self.textChanged

    class QMessageBox(QWidget):
        Ok = 1
        Warning = 2
        Critical = 3

    class QMainWindow(QWidget):
        pass

    class QAction(QWidget):
        pass

    class QMenu(QWidget):
        pass

    class QMenuBar(QWidget):
        pass

    class QHeaderView(QWidget):
        Stretch = 1
        ResizeToContents = 2

        def setSectionResizeMode(self, *args, **kwargs):
            return None

    class _Layout:
        def __init__(self, *args, **kwargs):
            self.children = []

        def addWidget(self, widget, *args, **kwargs):
            self.children.append(widget)

        def addLayout(self, layout, *args, **kwargs):
            self.children.append(layout)

        def addRow(self, *items):
            self.children.extend(items)

        def setContentsMargins(self, *args):
            return None

        def setSpacing(self, *args):
            return None

    class QVBoxLayout(_Layout):
        pass

    class QGridLayout(_Layout):
        pass

    class QFormLayout(_Layout):
        pass

    class QThread(threading.Thread):
        def __init__(self, parent=None):
            super().__init__(daemon=True)
            self.parent = parent

        def wait(self, timeout: int | None = None):
            self.join(None if timeout is None else timeout / 1000.0)
            return not self.is_alive()

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

    class Qt:
        Horizontal = 1
        Vertical = 2
        AlignCenter = 0x84
        KeepAspectRatio = 1
        SmoothTransformation = 1
        DisplayRole = 0
        EditRole = 1
        QueuedConnection = 3

    class QAbstractTableModel(QObject):
        def rowCount(self, parent=None): return 0
        def columnCount(self, parent=None): return 0
        def data(self, index, role=None): return None
        def headerData(self, section, orientation, role=None): return None

    class QRectF:
        def __init__(self, *args): self.args = args

    class QVector3D:
        def __init__(self, *args): self.args = args

    class QQuaternion:
        def __init__(self, *args): self.args = args

    class QMatrix4x4:
        def __init__(self, *args): self.args = args

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
    qtcore_mod.Qt = Qt
    qtcore_mod.QAbstractTableModel = QAbstractTableModel
    qtcore_mod.QRectF = QRectF

    qtgui_mod.QGuiApplication = QGuiApplication
    qtgui_mod.QColor = QColor
    qtgui_mod.QPainter = QPainter
    qtgui_mod.QPixmap = QPixmap
    qtgui_mod.QAction = QAction
    qtgui_mod.QVector3D = QVector3D
    qtgui_mod.QQuaternion = QQuaternion
    qtgui_mod.QMatrix4x4 = QMatrix4x4

    qtwidgets_mod.QApplication = QApplication
    qtwidgets_mod.QWidget = QWidget
    qtwidgets_mod.QFrame = QFrame
    qtwidgets_mod.QLabel = QLabel
    qtwidgets_mod.QVBoxLayout = QVBoxLayout
    qtwidgets_mod.QGridLayout = QGridLayout
    qtwidgets_mod.QGroupBox = QGroupBox
    qtwidgets_mod.QTextEdit = QTextEdit
    qtwidgets_mod.QFormLayout = QFormLayout
    qtwidgets_mod.QPushButton = QPushButton
    qtwidgets_mod.QProgressBar = QProgressBar
    qtwidgets_mod.QListWidget = QListWidget
    qtwidgets_mod.QListWidgetItem = QListWidgetItem
    qtwidgets_mod.QSplitter = QSplitter
    qtwidgets_mod.QHeaderView = QHeaderView
    qtwidgets_mod.QTableView = QTableView
    qtwidgets_mod.QComboBox = QComboBox
    qtwidgets_mod.QLineEdit = QLineEdit
    qtwidgets_mod.QMessageBox = QMessageBox
    qtwidgets_mod.QMainWindow = QMainWindow
    qtwidgets_mod.QMenu = QMenu
    qtwidgets_mod.QMenuBar = QMenuBar
    qtwidgets_mod.QAction = QAction

    pyside6_mod.QtCore = qtcore_mod
    pyside6_mod.QtGui = qtgui_mod
    pyside6_mod.QtWidgets = qtwidgets_mod

    sys.modules.setdefault("PySide6", pyside6_mod)
    sys.modules.setdefault("PySide6.QtCore", qtcore_mod)
    sys.modules.setdefault("PySide6.QtGui", qtgui_mod)
    sys.modules.setdefault("PySide6.QtWidgets", qtwidgets_mod)
