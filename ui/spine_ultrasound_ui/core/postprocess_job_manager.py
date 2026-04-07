from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from spine_ultrasound_ui.models import CapabilityStatus


@dataclass(frozen=True)
class PostprocessStageExecution:
    stage: str
    session_dir: Path
    metadata: dict[str, Any]
    status: CapabilityStatus


class PostprocessJobManager:
    def __init__(self) -> None:
        self._last_runs: dict[str, PostprocessStageExecution] = {}

    def run_stage(
        self,
        *,
        stage: str,
        session_dir: Path,
        metadata: dict[str, Any],
        build_status: Callable[[], CapabilityStatus],
    ) -> CapabilityStatus:
        status = build_status()
        self._last_runs[stage] = PostprocessStageExecution(
            stage=stage,
            session_dir=session_dir,
            metadata=dict(metadata),
            status=status,
        )
        return status

    def last_run(self, stage: str) -> PostprocessStageExecution | None:
        return self._last_runs.get(stage)
