from __future__ import annotations

import threading
from typing import Callable


class HeadlessLoopDriver:
    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    @property
    def stop_event(self) -> threading.Event:
        return self._stop

    def start(self, target: Callable[[], None]) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def stop(self, *, join_timeout: float = 1.5) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=join_timeout)
        self._thread = None
