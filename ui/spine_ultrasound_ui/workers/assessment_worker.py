from __future__ import annotations

from spine_ultrasound_ui.imaging.assessment import run_assessment
from spine_ultrasound_ui.workers._job_worker import JobWorker


class AssessmentWorker(JobWorker):
    def __init__(self, payload=None, parent=None) -> None:
        super().__init__("assessment", run_assessment, payload=payload, parent=parent)
