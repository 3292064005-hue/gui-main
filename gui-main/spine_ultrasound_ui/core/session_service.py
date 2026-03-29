from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import platform
import shutil
from typing import Any, Optional

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.command_journal import summarize_command_payload
from spine_ultrasound_ui.services.device_readiness import build_device_readiness
from spine_ultrasound_ui.services.spine_scan_protocol import build_scan_protocol
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile
from spine_ultrasound_ui.core.session_recorders import FrameRecorder, JsonlRecorder
from spine_ultrasound_ui.models import ExperimentRecord, RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.export_service import export_text_report
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService


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
        self.annotation_journal: Optional[JsonlRecorder] = None
        self.session_intelligence = SessionIntelligenceService()

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
        patient_registration: dict[str, Any] | None = None,
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
        robot_profile = load_xmate_profile().to_dict()
        registration_payload = dict(patient_registration or {})
        locked = self.exp_manager.lock_session(
            exp_id=self.current_experiment.exp_id,
            config_snapshot=config.to_dict(),
            device_roster=device_roster,
            software_version=config.software_version,
            build_id=config.build_id,
            scan_plan=preview_plan,
            protocol_version=protocol_version,
            planner_version=preview_plan.planner_version,
            registration_version=str(registration_payload.get("source", "camera_backed_registration_v2")),
            core_protocol_version=protocol_version,
            frontend_build_id=config.build_id,
            environment_snapshot={
                "platform": platform.platform(),
                "tool_name": config.tool_name,
                "tcp_name": config.tcp_name,
                "robot_model": config.robot_model,
            },
            force_control_hash=self._hash_payload(safety_thresholds or {}),
            robot_profile_hash=self._hash_payload(robot_profile),
            patient_registration_hash=self._hash_payload(registration_payload),
            force_sensor_provider=config.force_sensor_provider,
            safety_thresholds=safety_thresholds or {},
            device_health_snapshot=device_health_snapshot or {},
            robot_profile=robot_profile or {},
            patient_registration=registration_payload,
            scan_protocol={},
        )
        self.current_session_dir = Path(locked["session_dir"])
        self.current_scan_plan = ScanPlan.from_dict(locked["scan_plan"])
        self._locked_template_hash = preview_hash
        self.current_experiment.session_id = locked["session_id"]
        self.current_experiment.plan_id = self.current_scan_plan.plan_id
        self._open_ui_recorders(self.current_session_dir, locked["session_id"])
        readiness = build_device_readiness(config=config, device_roster=device_health_snapshot, protocol_version=protocol_version)
        readiness_path = self.exp_manager.save_json_artifact(self.current_session_dir, "meta/device_readiness.json", readiness)
        self.exp_manager.append_artifact(self.current_session_dir, "device_readiness", readiness_path)
        xmate_profile_path = self.exp_manager.save_json_artifact(self.current_session_dir, "meta/xmate_profile.json", robot_profile)
        self.exp_manager.append_artifact(self.current_session_dir, "xmate_profile", xmate_profile_path)
        registration_path = self.exp_manager.save_json_artifact(self.current_session_dir, "meta/patient_registration.json", registration_payload)
        self.exp_manager.append_artifact(self.current_session_dir, "patient_registration", registration_path)
        scan_protocol = build_scan_protocol(
            session_id=locked["session_id"],
            plan=self.current_scan_plan,
            config=config,
            robot_profile=load_xmate_profile(),
            patient_registration=registration_payload,
        )
        protocol_path = self.exp_manager.save_json_artifact(self.current_session_dir, "derived/preview/scan_protocol.json", scan_protocol)
        self.exp_manager.append_artifact(self.current_session_dir, "scan_protocol", protocol_path)
        self.exp_manager.update_manifest(
            self.current_session_dir,
            device_readiness=readiness,
            robot_profile=robot_profile,
            patient_registration=registration_payload,
            scan_protocol=scan_protocol,
        )
        self.refresh_session_intelligence()
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
        self.refresh_session_intelligence()
        return path

    def export_summary(self, title: str, lines: list[str]) -> Path:
        if self.current_session_dir is None:
            raise RuntimeError("session is not locked")
        target = self.current_session_dir / "export" / "summary.txt"
        export_text_report(target, title, lines)
        self.exp_manager.append_artifact(self.current_session_dir, "summary_text", target)
        self.refresh_session_intelligence()
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
        self.annotation_journal = None

    def record_quality_feedback(self, payload: dict[str, Any], source_ts_ns: Optional[int]) -> None:
        if self.quality_recorder is not None:
            self.quality_recorder.append(dict(payload), source_ts_ns=source_ts_ns)

    def record_camera_pixmap(self, pixmap: Any) -> None:
        if self.camera_recorder is not None:
            self.camera_recorder.append_pixmap(pixmap, "camera")

    def record_ultrasound_pixmap(self, pixmap: Any) -> None:
        if self.ultrasound_recorder is not None:
            self.ultrasound_recorder.append_pixmap(pixmap, "ultrasound")

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(blob).hexdigest() if blob else ""

    def refresh_session_intelligence(self) -> None:
        if self.current_session_dir is None:
            return
        products = self.session_intelligence.build_all(self.current_session_dir)
        targets = {
            "lineage": self.exp_manager.save_json_artifact(self.current_session_dir, "meta/lineage.json", products["lineage"]),
            "resume_state": self.exp_manager.save_json_artifact(self.current_session_dir, "meta/resume_state.json", products["resume_state"]),
            "resume_decision": self.exp_manager.save_json_artifact(self.current_session_dir, "meta/resume_decision.json", products["resume_decision"]),
            "resume_attempts": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/session/resume_attempts.json", products["resume_attempts"]),
            "resume_attempt_outcomes": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/session/resume_attempt_outcomes.json", products["resume_attempt_outcomes"]),
            "command_state_policy": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/session/command_state_policy.json", products["command_state_policy"]),
            "command_policy_snapshot": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/session/command_policy_snapshot.json", products["command_policy_snapshot"]),
            "contract_kernel_diff": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/session/contract_kernel_diff.json", products["contract_kernel_diff"]),
            "recovery_report": self.exp_manager.save_json_artifact(self.current_session_dir, "export/recovery_report.json", products["recovery_report"]),
            "recovery_decision_timeline": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/recovery/recovery_decision_timeline.json", products["recovery_decision_timeline"]),
            "operator_incident_report": self.exp_manager.save_json_artifact(self.current_session_dir, "export/operator_incident_report.json", products["operator_incident_report"]),
            "session_incidents": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/incidents/session_incidents.json", products["session_incidents"]),
            "event_log_index": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/events/event_log_index.json", products["event_log_index"]),
            "event_delivery_summary": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/events/event_delivery_summary.json", products["event_delivery_summary"]),
            "selected_execution_rationale": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/planning/selected_execution_rationale.json", products["selected_execution_rationale"]),
            "contract_consistency": self.exp_manager.save_json_artifact(self.current_session_dir, "derived/session/contract_consistency.json", products["contract_consistency"]),
            "release_evidence_pack": self.exp_manager.save_json_artifact(self.current_session_dir, "export/release_evidence_pack.json", products["release_evidence_pack"]),
            "release_gate_decision": self.exp_manager.save_json_artifact(self.current_session_dir, "export/release_gate_decision.json", products["release_gate_decision"]),
        }
        for name, path in targets.items():
            self.exp_manager.append_artifact(self.current_session_dir, name, path)


    def reset_for_new_experiment(self) -> None:
        self.current_session_dir = None
        self.current_scan_plan = None
        self._locked_template_hash = ""
        self.quality_recorder = None
        self.camera_recorder = None
        self.ultrasound_recorder = None
        self.command_journal = None
        self.annotation_journal = None

    def reset(self) -> None:
        self.current_experiment = None
        self.reset_for_new_experiment()

    def _open_ui_recorders(self, session_dir: Path, session_id: str) -> None:
        quality_path = session_dir / "raw" / "ui" / "quality_feedback.jsonl"
        camera_index = session_dir / "raw" / "camera" / "index.jsonl"
        ultrasound_index = session_dir / "raw" / "ultrasound" / "index.jsonl"
        command_journal_path = session_dir / "raw" / "ui" / "command_journal.jsonl"
        annotations_path = session_dir / "raw" / "ui" / "annotations.jsonl"
        self.quality_recorder = JsonlRecorder(quality_path, session_id)
        self.camera_recorder = FrameRecorder(session_dir / "raw" / "camera" / "frames", camera_index, session_id)
        self.ultrasound_recorder = FrameRecorder(session_dir / "raw" / "ultrasound" / "frames", ultrasound_index, session_id)
        self.command_journal = JsonlRecorder(command_journal_path, session_id)
        self.annotation_journal = JsonlRecorder(annotations_path, session_id)
        for name, path in {
            "quality_feedback": quality_path,
            "camera_index": camera_index,
            "ultrasound_index": ultrasound_index,
            "command_journal": command_journal_path,
            "annotations": annotations_path,
        }.items():
            self.exp_manager.append_artifact(session_dir, name, path)


    def record_annotation(
        self,
        *,
        kind: str,
        message: str,
        ts_ns: int | None = None,
        segment_id: int | None = None,
        severity: str = "INFO",
        tags: list[str] | None = None,
    ) -> None:
        if self.annotation_journal is None:
            return
        self.annotation_journal.append_event(
            {
                "kind": kind,
                "message": message,
                "ts_ns": int(ts_ns or 0),
                "segment_id": int(segment_id or 0),
                "severity": severity,
                "tags": list(tags or []),
            }
        )
        self.refresh_session_intelligence()

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
        self.refresh_session_intelligence()
