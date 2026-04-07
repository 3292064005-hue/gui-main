from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import shutil
from typing import Any, Optional

from spine_ultrasound_ui.core.command_journal import summarize_command_payload
from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.session_artifact_service import SessionArtifactService
from spine_ultrasound_ui.core.session_context_service import SessionContextService
from spine_ultrasound_ui.core.session_finalize_service import SessionFinalizeService
from spine_ultrasound_ui.core.session_lock_service import SessionLockService
from spine_ultrasound_ui.core.session_recorder_service import SessionRecorderService
from spine_ultrasound_ui.core.session_recorders import FrameRecorder, JsonlRecorder
from spine_ultrasound_ui.models import ExperimentRecord, RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.planning.types import LocalizationResult
from spine_ultrasound_ui.services.session_evidence_seal_service import SessionEvidenceSealService
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile


@dataclass
class LockedSessionContext:
    """Frozen lock result returned to callers after session lock.

    Attributes:
        session_id: Locked session identifier.
        session_dir: Session directory on disk.
        scan_plan: Frozen execution scan plan.
        manifest: Locked session manifest payload.
    """

    session_id: str
    session_dir: Path
    scan_plan: ScanPlan
    manifest: dict[str, Any]


class SessionService:
    """Compatibility façade over session context, governance, and artifacts.

    The public API remains stable while internal responsibilities are delegated
    to dedicated services for context state, recorders/artifacts, and freeze
    lifecycle.
    """

    def __init__(self, exp_manager: ExperimentManager):
        self.exp_manager = exp_manager
        self._context = SessionContextService()
        self.quality_recorder: Optional[JsonlRecorder] = None
        self.camera_recorder: Optional[FrameRecorder] = None
        self.ultrasound_recorder: Optional[FrameRecorder] = None
        self.pressure_recorder: Optional[JsonlRecorder] = None
        self.command_journal: Optional[JsonlRecorder] = None
        self.annotation_journal: Optional[JsonlRecorder] = None
        self.session_intelligence = SessionIntelligenceService()
        self.evidence_seal_service = SessionEvidenceSealService()
        self.lock_service = SessionLockService(exp_manager)
        self.recorder_service = SessionRecorderService(exp_manager)
        self.finalize_service = SessionFinalizeService(exp_manager, self.session_intelligence)
        self.artifact_service = SessionArtifactService(
            exp_manager=exp_manager,
            recorder_service=self.recorder_service,
            finalize_service=self.finalize_service,
            evidence_seal_service=self.evidence_seal_service,
        )

    @property
    def current_experiment(self) -> Optional[ExperimentRecord]:
        return self._context.current_experiment

    @current_experiment.setter
    def current_experiment(self, value: Optional[ExperimentRecord]) -> None:
        self._context.current_experiment = value

    @property
    def current_session_dir(self) -> Optional[Path]:
        return self._context.current_session_dir

    @current_session_dir.setter
    def current_session_dir(self, value: Optional[Path]) -> None:
        self._context.current_session_dir = value

    @property
    def current_scan_plan(self) -> Optional[ScanPlan]:
        return self._context.current_scan_plan

    @current_scan_plan.setter
    def current_scan_plan(self, value: Optional[ScanPlan]) -> None:
        self._context.current_scan_plan = value

    def create_experiment(self, config: RuntimeConfig, note: str = "") -> ExperimentRecord:
        """Create a new experiment and reset session-only context.

        Args:
            config: Runtime configuration captured into experiment metadata.
            note: Optional operator note.

        Returns:
            Created experiment record.

        Raises:
            OSError: If filesystem layout creation fails.
        """
        self.reset_for_new_experiment()
        data = self.exp_manager.create(config.to_dict(), note=note)
        self.current_experiment = ExperimentRecord(
            exp_id=data["exp_id"],
            created_at=data["metadata"]["created_at"],
            state="AUTO_READY",
            cobb_angle=0.0,
            pressure_target=config.pressure_target,
            save_dir=data["save_dir"],
            assessment_confidence=0.0,
            measurement_source="",
        )
        return self.current_experiment

    def apply_assessment_result(self, result: dict[str, Any]) -> None:
        """Apply authoritative assessment output to the current experiment.

        Args:
            result: Assessment summary or measurement payload containing the
                resolved Cobb-angle candidate.

        Returns:
            None.

        Raises:
            RuntimeError: Raised when no experiment context exists.

        Boundary behaviour:
            Missing optional fields default to zero/false so historical callers
            can pass partial measurement payloads without breaking the update
            path.
        """
        if self.current_experiment is None:
            raise RuntimeError("experiment has not been created")
        self.current_experiment.cobb_angle = float(
            result.get("cobb_angle_deg", result.get("angle_deg", self.current_experiment.cobb_angle)) or 0.0
        )
        self.current_experiment.assessment_confidence = float(
            result.get("confidence", self.current_experiment.assessment_confidence) or 0.0
        )
        self.current_experiment.measurement_source = str(
            result.get("measurement_source", self.current_experiment.measurement_source) or self.current_experiment.measurement_source
        )
        self.refresh_session_intelligence()

    def save_preview_plan(self, plan: ScanPlan) -> Path:
        """Persist the preview plan for the current experiment.

        Raises:
            RuntimeError: If no experiment has been created yet.
        """
        if self.current_experiment is None:
            raise RuntimeError("experiment has not been created")
        self.current_scan_plan = plan
        self._context.locked_template_hash = ""
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
        localization_result: LocalizationResult | None = None,
        control_authority: dict[str, Any] | None = None,
    ) -> LockedSessionContext:
        """Freeze session inputs and create a locked session if needed.

        Args:
            config: Active runtime configuration.
            device_roster: Device registry snapshot.
            preview_plan: Preview plan to be frozen.
            protocol_version: Runtime protocol version captured into manifest.
            safety_thresholds: Safety thresholds captured into the freeze.
            device_health_snapshot: Device health facts captured into the freeze.
            patient_registration: Optional patient/registration snapshot.
            localization_result: Optional structured localization bundle carrying
                readiness, calibration, lineage, and replay artifacts.
            control_authority: Optional control-authority snapshot copied into the manifest.

        Returns:
            Locked session context.

        Raises:
            RuntimeError: If experiment context is missing, if the locked session
                is inconsistent, or if the preview hash changed after lock.
        """
        if self.current_experiment is None:
            raise RuntimeError("experiment has not been created")
        preview_hash = preview_plan.template_hash()
        if self.current_session_dir is not None:
            if preview_hash != self._context.locked_template_hash:
                raise RuntimeError("scan plan changed after session lock")
            if self.current_scan_plan is None or not self.current_experiment.session_id:
                raise RuntimeError("locked session is inconsistent")
            return LockedSessionContext(
                session_id=self.current_experiment.session_id,
                session_dir=self.current_session_dir,
                scan_plan=self.current_scan_plan,
                manifest=self.exp_manager.load_manifest(self.current_session_dir),
            )
        registration_payload = dict(patient_registration or {})
        (
            localization_readiness_payload,
            calibration_bundle_payload,
            manual_adjustment_payload,
            source_frame_set_payload,
            localization_replay_index_payload,
            guidance_algorithm_registry_payload,
            guidance_processing_steps_payload,
        ) = self._coalesce_guidance_bundle(
            registration_payload=registration_payload,
            localization_result=localization_result,
        )
        locked = self.lock_service.lock(
            exp_id=self.current_experiment.exp_id,
            config=config,
            device_roster=device_roster,
            preview_plan=preview_plan,
            protocol_version=protocol_version,
            safety_thresholds=safety_thresholds or {},
            device_health_snapshot=device_health_snapshot or {},
            patient_registration=registration_payload,
            localization_readiness=localization_readiness_payload,
            calibration_bundle=calibration_bundle_payload,
            manual_adjustment=manual_adjustment_payload,
            source_frame_set=source_frame_set_payload,
            localization_replay_index=localization_replay_index_payload,
            guidance_algorithm_registry=guidance_algorithm_registry_payload,
            guidance_processing_steps=guidance_processing_steps_payload,
            control_authority=control_authority or {},
            force_control_hash=self._hash_payload(safety_thresholds or {}),
            robot_profile_hash=self._hash_payload(load_xmate_profile().to_dict()),
            patient_registration_hash=str(registration_payload.get("registration_hash", "")) or self._hash_payload(registration_payload),
        )
        self.current_session_dir = locked.session_dir
        self.current_scan_plan = locked.scan_plan
        self._context.locked_template_hash = preview_hash
        self.current_experiment.session_id = locked.session_id
        self.current_experiment.plan_id = self.current_scan_plan.plan_id
        self._open_ui_recorders(self.current_session_dir, locked.session_id)
        self.refresh_session_intelligence()
        return LockedSessionContext(
            session_id=locked.session_id,
            session_dir=self.current_session_dir,
            scan_plan=self.current_scan_plan,
            manifest=locked.manifest,
        )

    @staticmethod
    def _coalesce_guidance_bundle(
        *,
        registration_payload: dict[str, Any],
        localization_result: LocalizationResult | None,
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
        """Normalize guidance freeze artifacts for direct and compatibility call paths.

        Args:
            registration_payload: Registration snapshot already selected for session freeze.
            localization_result: Structured localization result produced by the canonical
                localization pipeline.

        Returns:
            Tuple of ``(localization_readiness, calibration_bundle, manual_adjustment,
            source_frame_set, localization_replay_index, guidance_algorithm_registry,
            guidance_processing_steps)`` ready to pass into ``SessionLockService``.

        Raises:
            ValueError: Propagated if any synthesized artifact cannot be serialized by
                the canonical hashing helpers.

        Boundary behavior:
            - Canonical localization results pass through unchanged.
            - Non-guidance registrations return empty artifacts.
            - ``guidance_only`` registrations synthesize the minimum freeze bundle needed
              by legacy callers that do not yet pass ``localization_result``.
        """
        if localization_result is not None:
            return (
                dict(localization_result.localization_readiness),
                dict(localization_result.calibration_bundle),
                dict(localization_result.manual_adjustment),
                dict(localization_result.source_frame_set),
                dict(localization_result.localization_replay_index),
                dict(localization_result.guidance_algorithm_registry),
                list(localization_result.guidance_processing_steps),
            )

        if registration_payload.get('role') != 'guidance_only':
            return {}, {}, {}, {}, {}, {}, []

        generated_at = str(registration_payload.get('generated_at', ''))
        review_approval = dict(registration_payload.get('review_approval', {}))
        freeze_ready = bool(registration_payload.get('freeze_ready', False))
        frame_refs = list(registration_payload.get('camera_frame_refs', []))
        frame_ref_payload = {
            'camera_device_id': registration_payload.get('camera_device_id', ''),
            'frame_refs': frame_refs,
            'provider_mode': registration_payload.get('camera_observations', {}).get('provider_mode', 'synthetic'),
        }
        source_frame_set_hash = str(registration_payload.get('source_frame_set_hash', '')) or SessionService._hash_payload(frame_ref_payload)
        source_frame_set = {
            'schema_version': '1.0',
            'generated_at': generated_at,
            'camera_device_id': registration_payload.get('camera_device_id', ''),
            'frame_refs': frame_refs,
            'frame_count': len(frame_refs),
            'fresh': True,
            'provider_mode': registration_payload.get('camera_observations', {}).get('provider_mode', 'synthetic'),
            'requested_mode': registration_payload.get('camera_observations', {}).get('provider_mode', 'synthetic'),
            'source_frame_set_hash': source_frame_set_hash,
        }
        bundle_payload = {
            'camera_intrinsics_hash': registration_payload.get('camera_intrinsics_hash', ''),
            'camera_to_base_hash': registration_payload.get('camera_to_base_hash', ''),
            'probe_tcp_hash': registration_payload.get('probe_tcp_hash', ''),
            'temporal_sync_hash': registration_payload.get('temporal_sync_hash', ''),
            'algorithm_bundle_hash': registration_payload.get('algorithm_bundle_hash', ''),
        }
        bundle_hash = str(registration_payload.get('calibration_bundle_hash', '')) or SessionService._hash_payload(bundle_payload)
        calibration_bundle = {
            'schema_version': '1.0',
            'generated_at': generated_at,
            'bundle_id': f"guidance_bundle::{registration_payload.get('camera_device_id', 'camera')}",
            'release_state': 'approved' if freeze_ready else 'pending_review',
            'bundle_role': 'guidance_only',
            'camera_device_id': registration_payload.get('camera_device_id', ''),
            **bundle_payload,
            'bundle_hash': bundle_hash,
        }
        readiness = {
            'schema_version': '1.0',
            'generated_at': generated_at,
            'status': 'READY_FOR_FREEZE' if freeze_ready else 'BLOCKED',
            'device_gate': {
                'camera_online': True,
                'frame_count': len(frame_refs),
                'frame_fresh': True,
            },
            'calibration_gate': {
                'bundle_release_state': calibration_bundle['release_state'],
                'camera_intrinsics_valid': bool(registration_payload.get('camera_intrinsics_hash')),
                'camera_to_base_valid': bool(registration_payload.get('camera_to_base_hash')),
                'probe_tcp_valid': bool(registration_payload.get('probe_tcp_hash')),
                'temporal_sync_valid': bool(registration_payload.get('temporal_sync_hash')),
            },
            'guidance_gate': {
                'guidance_mode': registration_payload.get('guidance_mode', 'guidance_only'),
                'source_type': registration_payload.get('source_type', ''),
                'registration_candidate_hash': registration_payload.get('registration_hash', ''),
                'manual_adjustment_count': len(registration_payload.get('manual_adjustments', [])),
                'review_approved': bool(review_approval.get('approved', False)),
            },
            'freeze_gate': {
                'freeze_ready': freeze_ready,
                'review_required': False,
                'review_approved': bool(review_approval.get('approved', False)),
                'stale_artifacts': False,
                'source_frame_set_hash': source_frame_set_hash,
                'algorithm_bundle_hash': registration_payload.get('algorithm_bundle_hash', ''),
            },
            'blocking_reasons': list(registration_payload.get('blocking_reasons', [])),
            'warnings': list(registration_payload.get('warnings', [])),
            'review_required': False,
            'review_approval': review_approval,
        }
        readiness['readiness_hash'] = SessionService._hash_payload(readiness)
        replay = {
            'schema_version': '1.0',
            'replay_id': f"guidance-replay::{registration_payload.get('registration_id', 'registration')}",
            'generated_at': generated_at,
            'frame_refs': frame_refs,
            'processing_step_refs': list(registration_payload.get('processing_step_refs', [])),
            'registration_hash': registration_payload.get('registration_hash', ''),
            'readiness_hash': readiness['readiness_hash'],
            'calibration_bundle_hash': bundle_hash,
        }
        replay['replay_hash'] = SessionService._hash_payload(replay)
        return readiness, calibration_bundle, {}, source_frame_set, replay, {}, []

    def save_summary(self, payload: dict[str, Any]) -> Path:
        """Save the structured session summary JSON artifact.

        Raises:
            RuntimeError: If the session is not locked.
        """
        if self.current_session_dir is None:
            raise RuntimeError("session is not locked")
        path = self.artifact_service.save_summary(self.current_session_dir, payload)
        self.refresh_session_intelligence()
        return path

    def export_summary(self, title: str, lines: list[str]) -> Path:
        """Export a human-readable text summary for the locked session.

        Raises:
            RuntimeError: If the session is not locked.
        """
        if self.current_session_dir is None:
            raise RuntimeError("session is not locked")
        target = self.artifact_service.export_summary(self.current_session_dir, title, lines)
        self.refresh_session_intelligence()
        return target

    def rollback_pending_lock(self, preview_plan: ScanPlan | None = None) -> None:
        """Discard a partially created session lock and restore preview state.

        Args:
            preview_plan: Preview plan that remains active after rollback.

        Raises:
            RuntimeError: If the locked session directory cannot be removed.
        """
        cleanup_target = self.current_session_dir
        if cleanup_target is not None:
            try:
                shutil.rmtree(cleanup_target)
            except FileNotFoundError:
                pass
            except OSError as exc:
                raise RuntimeError(f"failed to remove pending session directory: {cleanup_target}") from exc
            if cleanup_target.exists():
                raise RuntimeError(f"failed to remove pending session directory: {cleanup_target}")
        if self.current_experiment is not None:
            self.current_experiment.session_id = ""
            self.current_experiment.plan_id = preview_plan.plan_id if preview_plan is not None else ""
        self.current_session_dir = None
        self.current_scan_plan = preview_plan
        self._context.locked_template_hash = ""
        self._clear_recorder_handles()

    def record_quality_feedback(self, payload: dict[str, Any], source_ts_ns: Optional[int]) -> None:
        """Append a quality feedback record when the recorder is open."""
        if self.quality_recorder is not None:
            self.quality_recorder.append(dict(payload), source_ts_ns=source_ts_ns)

    def record_camera_pixmap(self, pixmap: Any, *, source_ts_ns: Optional[int] = None, metadata: Optional[dict[str, Any]] = None) -> None:
        """Append a camera frame when the recorder is open.

        Args:
            pixmap: UI-visible camera frame.
            source_ts_ns: Source timestamp used for sync indexing.
            metadata: Optional frame metadata stored in the index.

        Returns:
            None.

        Raises:
            No exceptions are raised; null pixmaps are ignored.
        """
        if self.camera_recorder is not None:
            self.camera_recorder.append_pixmap(pixmap, "camera", source_ts_ns=source_ts_ns, metadata=metadata)

    def record_ultrasound_pixmap(self, pixmap: Any, *, source_ts_ns: Optional[int] = None, metadata: Optional[dict[str, Any]] = None) -> None:
        """Append an ultrasound frame when the recorder is open.

        Args:
            pixmap: UI-visible ultrasound frame.
            source_ts_ns: Source timestamp used for sync indexing.
            metadata: Optional frame metadata stored in the index.

        Returns:
            None.

        Raises:
            No exceptions are raised; null pixmaps are ignored.
        """
        if self.ultrasound_recorder is not None:
            self.ultrasound_recorder.append_pixmap(pixmap, "ultrasound", source_ts_ns=source_ts_ns, metadata=metadata)

    def record_pressure_sample(self, payload: dict[str, Any], source_ts_ns: Optional[int]) -> None:
        """Append a pressure-sensor sample when the recorder is open.

        Args:
            payload: Pressure/contact sample payload.
            source_ts_ns: Source timestamp for later sync and analytics.

        Returns:
            None.

        Raises:
            No exceptions are raised; missing recorder handles are ignored.
        """
        if self.pressure_recorder is not None:
            self.pressure_recorder.append(dict(payload), source_ts_ns=source_ts_ns)

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
        return hashlib.sha256(blob).hexdigest() if blob else ""

    def refresh_session_intelligence(self) -> None:
        """Refresh derived session intelligence/evidence artifacts if locked."""
        if self.current_session_dir is None:
            return
        self.artifact_service.refresh_intelligence(self.current_session_dir)

    def reset_for_new_experiment(self) -> None:
        """Clear session-only state and recorder handles for a new experiment."""
        self._context.reset_for_new_experiment()
        self._clear_recorder_handles()

    def reset(self) -> None:
        """Reset both experiment and session state."""
        self._context.reset_all()
        self._clear_recorder_handles()

    def _open_ui_recorders(self, session_dir: Path, session_id: str) -> None:
        """Open recorder bundle and publish handles on the compatibility surface."""
        bundle = self.artifact_service.open_recorders(session_dir, session_id)
        self.quality_recorder = bundle.quality_recorder
        self.camera_recorder = bundle.camera_recorder
        self.ultrasound_recorder = bundle.ultrasound_recorder
        self.pressure_recorder = bundle.pressure_recorder
        self.command_journal = bundle.command_journal
        self.annotation_journal = bundle.annotation_journal

    def _clear_recorder_handles(self) -> None:
        self.quality_recorder = None
        self.camera_recorder = None
        self.ultrasound_recorder = None
        self.pressure_recorder = None
        self.command_journal = None
        self.annotation_journal = None

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
        """Record a free-form session annotation.

        Notes:
            Missing recorder handles are treated as a no-op for compatibility.
        """
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
        """Record a normalized command journal entry.

        Notes:
            Missing recorder handles are treated as a no-op for compatibility.
        """
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
