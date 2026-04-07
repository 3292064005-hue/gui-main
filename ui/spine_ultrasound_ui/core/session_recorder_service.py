from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.session_recorders import FrameRecorder, JsonlRecorder


@dataclass
class SessionRecorderBundle:
    quality_recorder: JsonlRecorder
    camera_recorder: FrameRecorder
    ultrasound_recorder: FrameRecorder
    pressure_recorder: JsonlRecorder
    command_journal: JsonlRecorder
    annotation_journal: JsonlRecorder


class SessionRecorderService:
    """Create and register session-scoped recorders.

    The public ``SessionService`` keeps recorder attributes for compatibility,
    while this helper owns recorder construction and artifact registration.
    """

    def __init__(self, exp_manager: ExperimentManager) -> None:
        self.exp_manager = exp_manager

    def open_recorders(self, session_dir: Path, session_id: str) -> SessionRecorderBundle:
        """Create UI/camera/ultrasound/pressure recorders for a locked session.

        Args:
            session_dir: Locked session directory.
            session_id: Locked session identifier.

        Returns:
            Recorder bundle ready for assignment by the façade.

        Raises:
            RuntimeError: Propagated when recorder paths cannot be created.
        """
        quality_path = session_dir / "raw" / "ui" / "quality_feedback.jsonl"
        camera_index = session_dir / "raw" / "camera" / "index.jsonl"
        ultrasound_index = session_dir / "raw" / "ultrasound" / "index.jsonl"
        pressure_path = session_dir / "raw" / "pressure" / "samples.jsonl"
        command_journal_path = session_dir / "raw" / "ui" / "command_journal.jsonl"
        annotations_path = session_dir / "raw" / "ui" / "annotations.jsonl"
        bundle = SessionRecorderBundle(
            quality_recorder=JsonlRecorder(quality_path, session_id),
            camera_recorder=FrameRecorder(session_dir / "raw" / "camera" / "frames", camera_index, session_id),
            ultrasound_recorder=FrameRecorder(session_dir / "raw" / "ultrasound" / "frames", ultrasound_index, session_id),
            pressure_recorder=JsonlRecorder(pressure_path, session_id),
            command_journal=JsonlRecorder(command_journal_path, session_id),
            annotation_journal=JsonlRecorder(annotations_path, session_id),
        )
        for name, path in {
            "quality_feedback": quality_path,
            "camera_index": camera_index,
            "ultrasound_index": ultrasound_index,
            "pressure_samples": pressure_path,
            "command_journal": command_journal_path,
            "annotations": annotations_path,
        }.items():
            self.exp_manager.append_artifact(session_dir, name, path)
        return bundle
