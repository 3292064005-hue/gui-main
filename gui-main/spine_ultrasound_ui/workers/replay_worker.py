from __future__ import annotations

from spine_ultrasound_ui.workers._job_worker import JobWorker


def _identity(payload):
    return payload


class ReplayWorker(JobWorker):
    def __init__(self, payload=None, parent=None) -> None:
        super().__init__("replay", _identity, payload=payload, parent=parent)
