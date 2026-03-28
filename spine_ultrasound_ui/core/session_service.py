from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import shutil
from typing import Any, Optional

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.command_journal import summarize_command_payload
from spine_ultrasound_ui.core.session_recorders import FrameRecorder, JsonlRecorder
from spine_ultrasound_ui.models import ExperimentRecord, RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.export_service import export_text_report


@dataclass
class LockedSessionContext:
    session_id: str
    session_dir: Path
    scan_plan: ScanPlan
    manifest: dict[str, Any]


class SessionService:
    def __init__(self, exp_manager: ExperimentManager):
        self.exp_manager = exp_manager
        self.current_experiment: Optional[ExperimentRecord] = None
        self.current_session_dir: Optional[Path] = None
        self.current_scan_plan: Optional[ScanPlan] = None
        self._locked_template_hash = ""
        self.quality_recorder: Optional[JsonlRecorder] = None
        self.camera_recorder: Optional[FrameRecorder] = None
        self.ultrasound_recorder: Optional[FrameRecorder] = None
        self.command_journal: Optional[JsonlRecorder] = None

    def create_experiment(self, config: RuntimeConfig, note: str = "") -> ExperimentRecord:
        self.reset_for_new_experiment()
        data = self.exp_manager.create(config.to_dict(), note=note)
        self.current_experiment = ExperimentRecord(
            exp_id=data["exp_id"],
            created_at=data["metadata"]["created_at"],
            state="AUTO_READY",
            cobb_angle=0.0,
            pressure_target=config.pressure_target,
            save_dir=data["save_dir"],
        )
        return self.current_experiment

    def save_preview_plan(self, plan: ScanPlan) -> Path:
        if self.current_experiment is None:
            raise RuntimeError("experiment has not been created")
        self.current_scan_plan = plan
        self._locked_template_hash = ""
        self.current_experiment.plan_id = plan.plan_id
        return self.exp_manager.save_preview_plan(self.current_experiment.exp_id, plan)

    def ensure_locked(
        self,
        config: RuntimeConfig,
        device_roster: dict[str, Any],
        preview_plan: ScanPlan,
        *,
        protocol_version: int,
        safety_thresholds: dict[str, Any],
        device_health_snapshot: dict[str, Any],
    ) -> LockedSessionContext:
        if self.current_experiment is None:
            raise RuntimeError("experiment has not been created")
        preview_hash = preview_plan.template_hash()
        if self.current_session_dir is not None:
            if preview_hash != self._locked_template_hash:
                raise RuntimeError("scan plan changed after session lock")
            if self.current_scan_plan is None or not self.current_experiment.session_id:
                raise RuntimeError("locked session is inconsistent")
            return LockedSessionContext(
                session_id=self.current_experiment.session_id,
                session_dir=self.current_session_dir,
                scan_plan=self.current_scan_plan,
                manifest=self.exp_manager.load_manifest(self.current_session_dir),
            )
        locked = self.exp_manager.lock_session(
            exp_id=self.current_experiment.exp_id,
            config_snapshot=config.to_dict(),
            device_roster=device_roster,
            software_version=config.software_version,
            build_id=config.build_id,
            scan_plan=preview_plan,
            protocol_version=protocol_version,
            force_sensor_provider=config.force_sensor_provider,
            safety_thresholds=safety_thresholds,
            device_health_snapshot=device_health_snapshot,
        )
        self.current_session_dir = Path(locked["session_dir"])
        self.current_scan_plan = ScanPlan.from_dict(locked["scan_plan"])
        self._locked_template_hash = preview_hash
        self.current_experiment.session_id = locked["session_id"]
        self.current_experiment.plan_id = self.current_scan_plan.plan_id
        self._open_ui_recorders(self.current_session_dir, locked["session_id"])
        return LockedSessionContext(
            session_id=locked["session_id"],
            session_dir=self.current_session_dir,
            scan_plan=self.current_scan_plan,
            manifest=locked["manifest"],
        )

    def save_summary(self, payload: dict[str, Any]) -> Path:
        if self.current_session_dir is None:
            raise RuntimeError("session is not locked")
        path = self.exp_manager.save_summary(self.current_session_dir, payload)
        self.exp_manager.append_artifact(self.current_session_dir, "summary_json", path)
        return path

    def export_summary(self, title: str, lines: list[str]) -> Path:
        if self.current_session_dir is None:
            raise RuntimeError("session is not locked")
        target = self.current_session_dir / "export" / "summary.txt"
        export_text_report(target, title, lines)
        self.exp_manager.append_artifact(self.current_session_dir, "summary_text", target)
        return target

    def rollback_pending_lock(self, preview_plan: ScanPlan | None = None) -> None:
        if self.current_session_dir is not None:
            shutil.rmtree(self.current_session_dir, ignore_errors=True)
        if self.current_experiment is not None:
            self.current_experiment.session_id = ""
            self.current_experiment.plan_id = preview_plan.plan_id if preview_plan is not None else ""
        self.current_session_dir = None
        self.current_scan_plan = preview_plan
        self._locked_template_hash = ""
        self.quality_recorder = None
        self.camera_recorder = None
        self.ultrasound_recorder = None
        self.command_journal = None

    def record_quality_feedback(self, payload: dict[str, Any], source_ts_ns: Optional[int]) -> None:
        if self.quality_recorder is not None:
            self.quality_recorder.append(dict(payload), source_ts_ns=source_ts_ns)

    def record_camera_pixmap(self, pixmap: Any) -> None:
        if self.camera_recorder is not None:
            self.camera_recorder.append_pixmap(pixmap, "camera")

    def record_ultrasound_pixmap(self, pixmap: Any) -> None:
        if self.ultrasound_recorder is not None:
            self.ultrasound_recorder.append_pixmap(pixmap, "ultrasound")

    def reset_for_new_experiment(self) -> None:
        self.current_session_dir = None
        self.current_scan_plan = None
        self._locked_template_hash = ""
        self.quality_recorder = None
        self.camera_recorder = None
        self.ultrasound_recorder = None
        self.command_journal = None

    def reset(self) -> None:
        self.current_experiment = None
        self.reset_for_new_experiment()

    def _open_ui_recorders(self, session_dir: Path, session_id: str) -> None:
        self.quality_recorder = JsonlRecorder(session_dir / "raw" / "ui" / "quality_feedback.jsonl", session_id)
        self.camera_recorder = FrameRecorder(session_dir / "raw" / "camera" / "frames", session_dir / "raw" / "camera" / "index.jsonl", session_id)
        self.ultrasound_recorder = FrameRecorder(session_dir / "raw" / "ultrasound" / "frames", session_dir / "raw" / "ultrasound" / "index.jsonl", session_id)
        self.command_journal = JsonlRecorder(session_dir / "raw" / "ui" / "command_journal.jsonl", session_id)

    def record_command_journal(
        self,
        *,
        source: str,
        command: str,
        payload: dict[str, Any] | None,
        reply: dict[str, Any],
        workflow_step: str,
        auto_action: str = "",
    ) -> None:
        if self.command_journal is None:
            return
        self.command_journal.append_event(
            {
                "ts_ns": reply.get("ts_ns", 0),
                "source": source,
                "command": command,
                "workflow_step": workflow_step,
                "auto_action": auto_action,
                "payload_summary": summarize_command_payload(payload),
                "reply": {
                    "ok": bool(reply.get("ok", False)),
                    "message": str(reply.get("message", "")),
                    "request_id": str(reply.get("request_id", "")),
                    "data": dict(reply.get("data", {})),
                },
            }
        )
