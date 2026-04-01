from __future__ import annotations

from spine_ultrasound_ui.imaging.preprocess import run_preprocess
from spine_ultrasound_ui.workers._job_worker import JobWorker


class PreprocessWorker(JobWorker):
    def __init__(self, payload=None, parent=None) -> None:
        super().__init__("preprocess", run_preprocess, payload=payload, parent=parent)
