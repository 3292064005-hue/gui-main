from __future__ import annotations

import hashlib
import json
import mimetypes
import platform
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from spine_ultrasound_ui.models import ArtifactDescriptor, ProcessingStepRecord, ScanPlan, SessionManifest
from spine_ultrasound_ui.utils import ensure_dir, now_text


_ARTIFACT_SCHEMA_HINTS = {
    "summary_json": "summary.schema.json",
    "session_report": "session_report.schema.json",
    "replay_index": "replay_index.schema.json",
    "quality_timeline": "quality_timeline.schema.json",
    "alarm_timeline": "alarm_event.schema.json",
    "qa_pack": "qa_pack.schema.json",
    "session_compare": "session_compare.schema.json",
    "session_trends": "session_trends.schema.json",
    "diagnostics_pack": "diagnostics_pack.schema.json",
    "device_readiness": "device_readiness.schema.json",
    "xmate_profile": "xmate_profile.schema.json",
    "patient_registration": "patient_registration.schema.json",
    "scan_protocol": "scan_protocol.schema.json",
    "frame_sync_index": "frame_sync_index.schema.json",
    "session_integrity": "artifact_registry.schema.json",
    "lineage": "session/lineage.schema.json",
    "resume_state": "session/resume_state.schema.json",
    "recovery_report": "session/recovery_report.schema.json",
    "operator_incident_report": "session/operator_incident_report.schema.json",
    "session_incidents": "session/session_incidents.schema.json",
    "resume_decision": "session/resume_decision.schema.json",
    "event_log_index": "session/event_log_index_v1.schema.json",
    "event_delivery_summary": "session/event_delivery_summary_v1.schema.json",
    "selected_execution_rationale": "session/selected_execution_rationale_v1.schema.json",
    "release_gate_decision": "runtime/release_gate_decision_v1.schema.json",
    "recovery_decision_timeline": "session/recovery_timeline_v1.schema.json",
    "resume_attempts": "session/resume_attempts_v1.schema.json",
    "resume_attempt_outcomes": "session/resume_attempt_outcomes_v1.schema.json",
    "contract_consistency": "session/contract_consistency_v1.schema.json",
    "release_evidence_pack": "session/release_evidence_pack_v1.schema.json",
    "command_state_policy": "runtime/command_state_policy_v1.schema.json",
    "command_policy_snapshot": "session/command_policy_snapshot_v1.schema.json",
    "contract_kernel_diff": "session/contract_kernel_diff_v1.schema.json",
}


class ExperimentManager:
    def __init__(self, root: Path):
        self.root = ensure_dir(root)

    def make_experiment_id(self) -> str:
        year = now_text()[:4]
        idx = 1
        while True:
            exp_id = f"EXP_{year}_{idx:04d}"
            if not (self.root / exp_id).exists():
                return exp_id
            idx += 1

    def make_session_id(self, exp_id: str) -> str:
        idx = 1
        while True:
            session_id = f"{exp_id}_S{idx:03d}"
            if not (self.root / exp_id / "sessions" / session_id).exists():
                return session_id
            idx += 1

    def create(self, config_snapshot: dict, note: str = "") -> dict:
        exp_id = self.make_experiment_id()
        exp_dir = ensure_dir(self.root / exp_id)
        for p in ["meta", "sessions", "derived", "export", "replay"]:
            ensure_dir(exp_dir / p)
        metadata = {
            "experiment_id": exp_id,
            "created_at": now_text(),
            "note": note,
            "software": {"platform": platform.platform()},
            "config_snapshot": config_snapshot,
            "state": "CREATED",
        }
        (exp_dir / "meta" / "experiment.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"exp_id": exp_id, "save_dir": str(exp_dir), "metadata": metadata}

    def save_preview_plan(self, exp_id: str, plan: ScanPlan) -> Path:
        exp_dir = self.root / exp_id
        target = exp_dir / "derived" / "preview" / "scan_plan_preview.json"
        ensure_dir(target.parent)
        target.write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def lock_session(
        self,
        exp_id: str,
        config_snapshot: Dict[str, Any],
        device_roster: Dict[str, Any],
        software_version: str,
        build_id: str,
        scan_plan: ScanPlan,
        *,
        protocol_version: int = 1,
        planner_version: str = "deterministic_planner_v2",
        registration_version: str = "camera_backed_registration_v2",
        core_protocol_version: int = 1,
        frontend_build_id: str = "",
        environment_snapshot: Dict[str, Any] | None = None,
        force_control_hash: str = "",
        robot_profile_hash: str = "",
        patient_registration_hash: str = "",
        force_sensor_provider: str = "mock_force_sensor",
        safety_thresholds: Dict[str, Any] | None = None,
        device_health_snapshot: Dict[str, Any] | None = None,
        robot_profile: Dict[str, Any] | None = None,
        patient_registration: Dict[str, Any] | None = None,
        scan_protocol: Dict[str, Any] | None = None,
    ) -> dict:
        exp_dir = self.root / exp_id
        session_id = self.make_session_id(exp_id)
        session_dir = ensure_dir(exp_dir / "sessions" / session_id)
        for p in [
            "meta",
            "raw/core",
            "raw/camera/frames",
            "raw/ultrasound/frames",
            "raw/ui",
            "derived/preview",
            "derived/keyframes",
            "derived/reconstruction",
            "derived/assessment",
            "derived/quality",
            "derived/alarms",
            "replay",
            "export",
        ]:
            ensure_dir(session_dir / p)
        final_plan = scan_plan.with_session(session_id, plan_id=f"PLAN_{session_id}")
        readiness_payload = {"ready_to_lock": True}
        manifest = SessionManifest(
            experiment_id=exp_id,
            session_id=session_id,
            created_at=now_text(),
            config_snapshot=config_snapshot,
            scan_plan_hash=final_plan.plan_hash(),
            device_roster=device_roster,
            software_version=software_version,
            build_id=build_id,
            planner_version=planner_version,
            registration_version=registration_version,
            core_protocol_version=core_protocol_version,
            frontend_build_id=frontend_build_id,
            environment_snapshot=environment_snapshot or {},
            force_control_hash=force_control_hash,
            robot_profile_hash=robot_profile_hash,
            patient_registration_hash=patient_registration_hash,
            protocol_version=protocol_version,
            force_sensor_provider=force_sensor_provider,
            safety_thresholds=safety_thresholds or {},
            device_health_snapshot=device_health_snapshot or {},
            device_readiness=readiness_payload,
            robot_profile=robot_profile or {},
            patient_registration=patient_registration or {},
            scan_protocol=scan_protocol or {},
            artifacts={"scan_plan": "meta/scan_plan.json"},
            artifact_registry={
                "scan_plan": ArtifactDescriptor(
                    artifact_type="scan_plan",
                    path="meta/scan_plan.json",
                    producer="experiment_manager",
                    artifact_id="scan_plan",
                    created_at=now_text(),
                    summary="Frozen locked scan plan",
                    source_stage="workflow_lock",
                ).to_dict()
            },
        )
        self._write_manifest(session_dir, manifest)
        (session_dir / "meta" / "scan_plan.json").write_text(
            json.dumps(final_plan.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {
            "session_id": session_id,
            "session_dir": str(session_dir),
            "manifest": manifest.to_dict(),
            "scan_plan": final_plan.to_dict(),
        }

    def append_artifact(self, session_dir: Path, name: str, artifact_path: Path) -> dict:
        descriptor = self._build_artifact_descriptor(session_dir, name, artifact_path)
        return self.register_artifact(session_dir, name, descriptor)

    def register_artifact(self, session_dir: Path, name: str, descriptor: ArtifactDescriptor | Dict[str, Any]) -> dict:
        manifest = self.load_manifest(session_dir)
        artifacts = dict(manifest.get("artifacts", {}))
        artifact_registry = dict(manifest.get("artifact_registry", {}))
        payload = descriptor.to_dict() if isinstance(descriptor, ArtifactDescriptor) else dict(descriptor)
        payload.setdefault("artifact_id", name)
        payload.setdefault("schema", _ARTIFACT_SCHEMA_HINTS.get(name, ""))
        artifacts[name] = payload["path"]
        artifact_registry[name] = payload
        manifest["artifacts"] = artifacts
        manifest["artifact_registry"] = artifact_registry
        self._write_manifest(session_dir, SessionManifest(**manifest))
        return manifest

    def append_processing_step(self, session_dir: Path, step: ProcessingStepRecord | Dict[str, Any]) -> dict:
        manifest = self.load_manifest(session_dir)
        steps = list(manifest.get("processing_steps", []))
        steps.append(step.to_dict() if isinstance(step, ProcessingStepRecord) else dict(step))
        manifest["processing_steps"] = steps
        self._write_manifest(session_dir, SessionManifest(**manifest))
        return manifest

    def update_manifest(self, session_dir: Path, **updates: Any) -> dict:
        manifest = self.load_manifest(session_dir)
        manifest.update(updates)
        self._write_manifest(session_dir, SessionManifest(**manifest))
        return manifest

    def load_manifest(self, session_dir: Path) -> Dict[str, Any]:
        path = session_dir / "meta" / "manifest.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        normalized = SessionManifest(**raw).to_dict()
        if normalized != raw:
            path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
        return normalized

    def save_summary(self, session_dir: Path, payload: Dict[str, Any]) -> Path:
        target = session_dir / "export" / "summary.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def save_json_artifact(self, session_dir: Path, relative_path: str, payload: Dict[str, Any]) -> Path:
        target = session_dir / relative_path
        ensure_dir(target.parent)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def load_json_artifact(self, session_dir: Path, relative_path: str) -> Dict[str, Any]:
        target = session_dir / relative_path
        return json.loads(target.read_text(encoding="utf-8"))

    def _build_artifact_descriptor(self, session_dir: Path, name: str, artifact_path: Path) -> ArtifactDescriptor:
        mime_type = mimetypes.guess_type(str(artifact_path))[0] or "application/octet-stream"
        rel_path = str(artifact_path.relative_to(session_dir))
        return ArtifactDescriptor(
            artifact_type=name,
            path=rel_path,
            mime_type=mime_type,
            producer="experiment_manager",
            schema=_ARTIFACT_SCHEMA_HINTS.get(name, ""),
            artifact_id=name,
            size_bytes=artifact_path.stat().st_size if artifact_path.exists() else 0,
            checksum=self._checksum_for_path(artifact_path),
            created_at=now_text(),
            summary=name.replace("_", " "),
            source_stage=self._infer_source_stage(name),
            dependencies=self._infer_dependencies(name),
        )

    def _write_manifest(self, session_dir: Path, manifest: SessionManifest) -> None:
        path = session_dir / "meta" / "manifest.json"
        path.write_text(json.dumps(asdict(manifest), indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _checksum_for_path(path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()


    @staticmethod
    def _infer_source_stage(name: str) -> str:
        if name in {"scan_plan", "device_readiness"}:
            return "workflow_lock"
        if name in {"summary_json", "summary_text", "quality_feedback", "camera_index", "ultrasound_index", "command_journal", "annotations"}:
            return "capture"
        if name in {"quality_timeline", "alarm_timeline"}:
            return "preprocess"
        if name in {"frame_sync_index", "replay_index"}:
            return "reconstruction"
        if name in {"session_report", "session_compare", "session_trends", "diagnostics_pack", "qa_pack", "session_integrity", "lineage", "resume_state", "resume_decision", "resume_attempts", "resume_attempt_outcomes", "recovery_report", "operator_incident_report", "session_incidents", "event_log_index", "recovery_decision_timeline", "contract_consistency", "release_evidence_pack", "release_gate_decision", "command_state_policy", "event_delivery_summary", "selected_execution_rationale"}:
            return "assessment"
        return "session_service"

    @staticmethod
    def _infer_dependencies(name: str) -> list[str]:
        mapping = {
            "device_readiness": ["scan_plan"],
            "quality_timeline": ["quality_feedback"],
            "alarm_timeline": ["command_journal"],
            "frame_sync_index": ["quality_feedback", "camera_index", "ultrasound_index", "annotations"],
            "replay_index": ["alarm_timeline", "quality_timeline", "annotations", "frame_sync_index"],
            "session_report": ["summary_json", "replay_index", "quality_timeline", "alarm_timeline", "frame_sync_index"],
            "session_compare": ["session_report"],
            "session_trends": ["session_report", "diagnostics_pack"],
            "diagnostics_pack": ["command_journal", "alarm_timeline", "quality_timeline", "annotations"],
            "qa_pack": ["session_report", "replay_index", "quality_timeline", "alarm_timeline", "session_compare", "session_trends", "diagnostics_pack"],
            "session_integrity": ["scan_plan", "device_readiness", "xmate_profile", "patient_registration", "scan_protocol"],
            "lineage": ["scan_plan", "patient_registration", "command_journal", "session_report"],
            "resume_state": ["scan_plan", "command_journal", "session_integrity", "recovery_report"],
            "recovery_report": ["command_journal", "alarm_timeline", "annotations"],
            "operator_incident_report": ["annotations", "alarm_timeline"],
            "session_incidents": ["operator_incident_report", "recovery_report", "quality_timeline"],
            "resume_decision": ["resume_state", "session_incidents", "recovery_report", "session_integrity"],
            "event_log_index": ["command_journal", "alarm_timeline", "annotations", "recovery_report", "resume_decision"],
            "recovery_decision_timeline": ["recovery_report", "resume_decision"],
            "resume_attempts": ["resume_decision", "command_journal"],
            "resume_attempt_outcomes": ["resume_attempts", "resume_decision", "contract_consistency", "command_state_policy"],
            "command_state_policy": ["scan_plan"],
            "event_delivery_summary": ["event_log_index", "resume_attempt_outcomes", "contract_consistency"],
            "selected_execution_rationale": ["scan_plan"],
            "contract_consistency": ["scan_plan", "session_integrity", "diagnostics_pack", "resume_decision", "event_log_index"],
            "release_evidence_pack": ["contract_consistency", "session_integrity", "diagnostics_pack", "event_log_index", "recovery_decision_timeline", "session_report", "qa_pack"],
            "release_gate_decision": ["contract_consistency", "release_evidence_pack", "event_delivery_summary", "resume_attempt_outcomes", "selected_execution_rationale"],
        }
        return list(mapping.get(name, []))
