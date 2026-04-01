from __future__ import annotations

"""Session artifact materialization and recorder lifecycle helpers."""

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.session_finalize_service import SessionFinalizeService
from spine_ultrasound_ui.core.session_recorder_service import SessionRecorderService
from spine_ultrasound_ui.services.export_service import export_text_report
from spine_ultrasound_ui.services.session_evidence_seal_service import SessionEvidenceSealService


class SessionArtifactService:
    """Produce persistent session artifacts and manage UI-side recorders."""

    def __init__(
        self,
        *,
        exp_manager: ExperimentManager,
        recorder_service: SessionRecorderService,
        finalize_service: SessionFinalizeService,
        evidence_seal_service: SessionEvidenceSealService,
    ) -> None:
        self.exp_manager = exp_manager
        self.recorder_service = recorder_service
        self.finalize_service = finalize_service
        self.evidence_seal_service = evidence_seal_service

    def open_recorders(self, session_dir: Path, session_id: str):
        """Open all UI-side session recorders for a locked session."""
        return self.recorder_service.open_recorders(session_dir, session_id)

    def save_summary(self, session_dir: Path, payload: dict[str, Any]) -> Path:
        """Persist the JSON session summary and refresh artifact registry."""
        path = self.exp_manager.save_summary(session_dir, payload)
        self.exp_manager.append_artifact(session_dir, "summary_json", path)
        return path

    def export_summary(self, session_dir: Path, title: str, lines: list[str]) -> Path:
        """Persist the operator-facing text summary and register it."""
        target = session_dir / "export" / "summary.txt"
        export_text_report(target, title, lines)
        self.exp_manager.append_artifact(session_dir, "summary_text", target)
        return target

    def refresh_intelligence(self, session_dir: Path) -> dict[str, Path]:
        """Refresh derived intelligence artifacts and evidence seal.

        Returns:
            Mapping of artifact identifiers to generated paths.
        """
        targets = self.finalize_service.refresh(session_dir)
        seal_path = self.evidence_seal_service.write(session_dir, manifest=self.exp_manager.load_manifest(session_dir))
        targets["session_evidence_seal"] = seal_path
        self.exp_manager.append_artifact(session_dir, "session_evidence_seal", seal_path)
        return targets
