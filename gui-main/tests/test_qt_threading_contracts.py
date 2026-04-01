from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.core.app_controller_runtime_mixin import AppControllerRuntimeMixin


class _BackendSignals(QObject):
    telemetry_received = Signal(object)
    log_generated = Signal(str, str)
    camera_pixmap_ready = Signal(QPixmap)
    ultrasound_pixmap_ready = Signal(QPixmap)
    reconstruction_pixmap_ready = Signal(QPixmap)


class _ControllerHarness(AppControllerRuntimeMixin):
    def __init__(self) -> None:
        self.backend = _BackendSignals()
        self.runtime_bridge = SimpleNamespace(
            handle_telemetry=lambda env: None,
            on_camera_pixmap=lambda pix: None,
            on_ultrasound_pixmap=lambda pix: None,
        )
        self.reconstruction_pixmap_ready = Signal(QPixmap).__get__(self, _ControllerHarness)
        self.log_generated = Signal(str, str).__get__(self, _ControllerHarness)


def test_app_controller_backend_connections_are_queued() -> None:
    harness = _ControllerHarness()
    harness._connect_backend()
    for signal_name in [
        'telemetry_received',
        'log_generated',
        'camera_pixmap_ready',
        'ultrasound_pixmap_ready',
        'reconstruction_pixmap_ready',
    ]:
        signal = getattr(harness.backend, signal_name)
        assert signal._connections, f'{signal_name} should be connected'
        assert all(connection_type == Qt.QueuedConnection for _, connection_type in signal._connections)


def test_exception_handler_connection_is_queued() -> None:
    source = Path('spine_ultrasound_ui/core/app_controller_runtime_mixin.py').read_text(encoding='utf-8')
    assert 'error_occurred.connect(self._on_error_occurred, Qt.QueuedConnection)' in source


def test_main_window_backend_connections_are_queued() -> None:
    source = Path('spine_ultrasound_ui/main_window.py').read_text(encoding='utf-8')
    assert 'status_updated.connect(self._on_status, Qt.QueuedConnection)' in source
    assert 'log_generated.connect(self._append_log, Qt.QueuedConnection)' in source
    assert '.connect(handler, Qt.QueuedConnection)' in source
    assert 'experiments_updated.connect(self._on_experiments, Qt.QueuedConnection)' in source
    assert 'system_state_changed.connect(self._on_system_state, Qt.QueuedConnection)' in source
    assert 'alarm_raised.connect(self._on_alarm, Qt.QueuedConnection)' in source
