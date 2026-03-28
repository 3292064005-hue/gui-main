from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, QTimer, Signal
from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils import ensure_dir, generate_demo_pixmap

from .backend_base import BackendBase
from .ipc_protocol import ReplyEnvelope, TelemetryEnvelope
from .mock_core_runtime import MockCoreRuntime


class MockBackend(QObject, BackendBase):
    telemetry_received = Signal(object)
    log_generated = Signal(str, str)
    camera_pixmap_ready = Signal(QPixmap)
    ultrasound_pixmap_ready = Signal(QPixmap)
    reconstruction_pixmap_ready = Signal(QPixmap)

    def __init__(self, root_dir: Path):
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.runtime = MockCoreRuntime()
        self.runtime.update_runtime_config(RuntimeConfig())
        self.phase = 0.0
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._tick)

    def start(self) -> None:
        self.timer.start(120)
        self._emit_telemetry(self.runtime.telemetry_snapshot())

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        self.runtime.update_runtime_config(config)
        self._emit_telemetry(self.runtime.telemetry_snapshot())

    def send_command(self, command: str, payload: Optional[dict] = None) -> ReplyEnvelope:
        reply = self.runtime.handle_command(command, payload or {})
        self.log_generated.emit("INFO" if reply.ok else "ERROR", f"[mock_core] {command}: {reply.message}")
        self._emit_telemetry(self.runtime.telemetry_snapshot())
        return reply

    def _tick(self) -> None:
        self.phase += 0.12
        self._emit_telemetry(self.runtime.tick())
        if generate_demo_pixmap is None:
            return
        self.camera_pixmap_ready.emit(generate_demo_pixmap(720, 360, "camera", self.phase))
        self.ultrasound_pixmap_ready.emit(generate_demo_pixmap(720, 360, "ultrasound", self.phase))
        self.reconstruction_pixmap_ready.emit(generate_demo_pixmap(720, 360, "reconstruction", self.phase))

    def _emit_telemetry(self, messages: list[TelemetryEnvelope]) -> None:
        for message in messages:
            if not message.ts_ns:
                message.ts_ns = uuid.uuid4().int % (10**12)
            self.telemetry_received.emit(message)
