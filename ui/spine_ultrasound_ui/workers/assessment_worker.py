from __future__ import annotations

from spine_ultrasound_ui.workers._job_worker import JobWorker
from spine_ultrasound_ui.workers.demo_postprocess_tasks import run_demo_assessment


class AssessmentWorker(JobWorker):
    def __init__(self, payload=None, parent=None) -> None:
        super().__init__("assessment", run_demo_assessment, payload=payload, parent=parent)
