from __future__ import annotations

"""Session ownership/context state separated from artifact production."""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from spine_ultrasound_ui.models import ExperimentRecord, ScanPlan


@dataclass
class SessionContextState:
    """Mutable session context state.

    Attributes:
        current_experiment: Active experiment record, if any.
        current_session_dir: Locked session directory.
        current_scan_plan: Active preview/locked scan plan.
        locked_template_hash: Frozen preview hash recorded at lock time.
    """

    current_experiment: Optional[ExperimentRecord] = None
    current_session_dir: Optional[Path] = None
    current_scan_plan: Optional[ScanPlan] = None
    locked_template_hash: str = ""


class SessionContextService:
    """Own active experiment/session identity and lock consistency state."""

    def __init__(self) -> None:
        self._state = SessionContextState()

    @property
    def current_experiment(self) -> Optional[ExperimentRecord]:
        return self._state.current_experiment

    @current_experiment.setter
    def current_experiment(self, value: Optional[ExperimentRecord]) -> None:
        self._state.current_experiment = value

    @property
    def current_session_dir(self) -> Optional[Path]:
        return self._state.current_session_dir

    @current_session_dir.setter
    def current_session_dir(self, value: Optional[Path]) -> None:
        self._state.current_session_dir = value

    @property
    def current_scan_plan(self) -> Optional[ScanPlan]:
        return self._state.current_scan_plan

    @current_scan_plan.setter
    def current_scan_plan(self, value: Optional[ScanPlan]) -> None:
        self._state.current_scan_plan = value

    @property
    def locked_template_hash(self) -> str:
        return self._state.locked_template_hash

    @locked_template_hash.setter
    def locked_template_hash(self, value: str) -> None:
        self._state.locked_template_hash = str(value or "")

    def reset_for_new_experiment(self) -> None:
        """Clear session lock state while preserving experiment identity."""
        self._state.current_session_dir = None
        self._state.current_scan_plan = None
        self._state.locked_template_hash = ""

    def reset_all(self) -> None:
        """Clear both experiment and session context."""
        self._state = SessionContextState()
