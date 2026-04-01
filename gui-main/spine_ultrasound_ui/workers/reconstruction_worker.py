from __future__ import annotations

from spine_ultrasound_ui.imaging.reconstruction import run_reconstruction
from spine_ultrasound_ui.workers._job_worker import JobWorker


class ReconstructionWorker(JobWorker):
    def __init__(self, payload=None, parent=None) -> None:
        super().__init__("reconstruction", run_reconstruction, payload=payload, parent=parent)
