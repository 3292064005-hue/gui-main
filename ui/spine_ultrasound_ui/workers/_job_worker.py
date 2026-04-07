from __future__ import annotations

from typing import Any, Callable

from PySide6.QtCore import QThread, Signal


class JobWorker(QThread):
    completed = Signal(object)
    failed = Signal(str)

    def __init__(self, stage_name: str, task: Callable[[Any], Any], payload: Any = None, parent=None) -> None:
        super().__init__(parent)
        self.stage_name = stage_name
        self._task = task
        self._payload = payload

    def configure(self, payload: Any) -> None:
        self._payload = payload

    def run(self) -> None:
        try:
            result = self._task(self._payload)
        except Exception as exc:  # pragma: no cover - GUI thread failure path
            self.failed.emit(f"{self.stage_name} failed: {exc}")
            return
        self.completed.emit(result)
