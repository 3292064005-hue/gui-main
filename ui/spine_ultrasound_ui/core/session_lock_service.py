from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import hashlib
import json
import platform
from typing import Any

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.device_readiness import build_device_readiness
from spine_ultrasound_ui.services.spine_scan_protocol import build_scan_protocol
from spine_ultrasound_ui.services.runtime_source_policy_service import RuntimeSourcePolicyService
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile
from spine_ultrasound_ui.utils.robot_family_descriptor import build_profile_snapshot, build_robot_family_descriptor
from spine_ultrasound_ui.utils.truth_ledger_service import build_live_truth_ledger, build_repo_truth_ledger


@dataclass
class SessionLockResult:
    session_id: str
    session_dir: Path
    scan_plan: ScanPlan
    manifest: dict[str, Any]
    robot_profile: dict[str, Any]
    readiness: dict[str, Any]
    patient_registration: dict[str, Any]
    scan_protocol: dict[str, Any]
    repo_truth_ledger: dict[str, Any]
    live_truth_ledger: dict[str, Any]
    localization_readiness: dict[str, Any]
    calibration_bundle: dict[str, Any]
    localization_freeze: dict[str, Any]
    manual_adjustment: dict[str, Any]
    source_frame_set: dict[str, Any]


class SessionLockService:
    """Freeze a preview scan plan into a persistent session directory.

    This service extracts the lock-time side effects from ``SessionService`` so
    that session freeze rules, artifact registration, and manifest updates can
    evolve independently from the UI-facing façade.
    """

    def __init__(self, exp_manager: ExperimentManager) -> None:
        self.exp_manager = exp_manager

    def lock(
        self,
        *,
        exp_id: str,
        config: RuntimeConfig,
        device_roster: dict[str, Any],
        preview_plan: ScanPlan,
        protocol_version: int,
        safety_thresholds: dict[str, Any],
        device_health_snapshot: dict[str, Any],
        patient_registration: dict[str, Any] | None = None,
        localization_readiness: dict[str, Any] | None = None,
        calibration_bundle: dict[str, Any] | None = None,
        manual_adjustment: dict[str, Any] | None = None,
        source_frame_set: dict[str, Any] | None = None,
        localization_replay_index: dict[str, Any] | None = None,
        guidance_algorithm_registry: dict[str, Any] | None = None,
        guidance_processing_steps: list[dict[str, Any]] | None = None,
        control_authority: dict[str, Any] | None = None,
        force_control_hash: str,
        robot_profile_hash: str,
        patient_registration_hash: str,
    ) -> SessionLockResult:
        """Create a locked session and materialize lock-time artifacts.

        Args:
            exp_id: Experiment identifier owning the future session.
            config: Frozen runtime configuration snapshot.
            device_roster: Device roster captured before lock.
            preview_plan: Preview scan plan to freeze.
            protocol_version: Current UI/core protocol version.
            safety_thresholds: Safety thresholds recorded into the manifest.
            device_health_snapshot: Point-in-time device health payload.
            patient_registration: Optional patient registration payload.
            localization_readiness: Optional guidance freeze-readiness verdict.
            calibration_bundle: Optional calibration bundle tied to the
                guidance result.
            manual_adjustment: Optional frozen operator adjustment artifact.
            source_frame_set: Optional source frame set consumed by guidance.
            localization_replay_index: Optional replay index for guidance.
            guidance_algorithm_registry: Optional guidance-plugin registry.
            guidance_processing_steps: Optional guidance-stage processing steps.
            control_authority: Optional control-authority snapshot.
            force_control_hash: Stable hash of force-control settings.
            robot_profile_hash: Stable hash of the xMate profile.
            patient_registration_hash: Stable hash of registration payload.

        Returns:
            A fully materialized lock result with paths and derived artifacts.

        Raises:
            RuntimeError: Propagated from the underlying experiment manager when
                manifest creation or artifact writes fail.
        """
        robot_profile = load_xmate_profile().to_dict()
        registration_payload = dict(patient_registration or {})
        readiness_payload = dict(localization_readiness or {})
        calibration_payload = dict(calibration_bundle or {})
        manual_adjustment_payload = dict(manual_adjustment or {})
        source_frame_set_payload = dict(source_frame_set or {})
        replay_payload = dict(localization_replay_index or {})
        guidance_registry_payload = dict(guidance_algorithm_registry or {})
        guidance_steps_payload = list(guidance_processing_steps or [])
        RuntimeSourcePolicyService().validate_session_lock(
            config=config,
            patient_registration=registration_payload,
            localization_readiness=readiness_payload,
            source_frame_set=source_frame_set_payload,
        )
        localization_freeze = self._build_localization_freeze(
            patient_registration=registration_payload,
            localization_readiness=readiness_payload,
            calibration_bundle=calibration_payload,
            manual_adjustment=manual_adjustment_payload,
            source_frame_set=source_frame_set_payload,
            guidance_algorithm_registry=guidance_registry_payload,
        )
        self._validate_guidance_freeze_inputs(
            patient_registration=registration_payload,
            localization_readiness=readiness_payload,
            calibration_bundle=calibration_payload,
            source_frame_set=source_frame_set_payload,
        )
        profile_snapshot = build_profile_snapshot(config)
        robot_family_descriptor = build_robot_family_descriptor(config)
        repo_truth_ledger = build_repo_truth_ledger(
            session_id="pending",
            session_dir="pending",
            profile=profile_snapshot,
            build_id=config.build_id,
            protocol_version=protocol_version,
            scan_plan_hash=preview_plan.plan_hash(),
            runtime_config=config.to_dict(),
            robot_family_descriptor=robot_family_descriptor,
        )
        live_truth_ledger = build_live_truth_ledger(
            session_id="pending",
            session_dir="pending",
            build_id=config.build_id,
            profile=profile_snapshot,
            robot_family_descriptor=robot_family_descriptor,
        )
        locked = self.exp_manager.lock_session(
            exp_id=exp_id,
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
            force_control_hash=force_control_hash,
            robot_profile_hash=robot_profile_hash,
            patient_registration_hash=self._canonical_hash(registration_payload, preferred_keys=("registration_hash",)) or patient_registration_hash,
            localization_readiness_hash=self._canonical_hash(readiness_payload, preferred_keys=("readiness_hash",)),
            calibration_bundle_hash=self._canonical_hash(calibration_payload, preferred_keys=("bundle_hash",)),
            localization_freeze_hash=self._canonical_hash(localization_freeze, preferred_keys=("freeze_hash",)),
            manual_adjustment_hash=self._canonical_hash(manual_adjustment_payload, preferred_keys=("hash",)),
            source_frame_set_hash=self._canonical_hash(source_frame_set_payload, preferred_keys=("source_frame_set_hash",)),
            guidance_version="camera_guidance_v1",
            guidance_mode="guidance_only",
            guidance_source_type=self._resolved_guidance_source_type(patient_registration=registration_payload, localization_readiness=readiness_payload, source_frame_set=source_frame_set_payload, config=config),
            force_sensor_provider=config.force_sensor_provider,
            safety_thresholds=safety_thresholds or {},
            device_health_snapshot=device_health_snapshot or {},
            robot_profile=robot_profile,
            patient_registration=registration_payload,
            localization_readiness=readiness_payload,
            calibration_bundle=calibration_payload,
            localization_freeze=localization_freeze,
            manual_adjustment=manual_adjustment_payload,
            source_frame_set=source_frame_set_payload,
            scan_protocol={},
            control_authority=control_authority or {},
            guidance_algorithm_registry=guidance_registry_payload,
            guidance_processing_steps=guidance_steps_payload,
            repo_truth_ledger=repo_truth_ledger,
            live_truth_ledger=live_truth_ledger,
        )
        session_dir = Path(locked["session_dir"])
        locked_plan = ScanPlan.from_dict(locked["scan_plan"])
        repo_truth_ledger = build_repo_truth_ledger(
            session_id=locked["session_id"],
            session_dir=str(session_dir),
            profile=profile_snapshot,
            build_id=config.build_id,
            protocol_version=protocol_version,
            scan_plan_hash=locked_plan.plan_hash(),
            runtime_config=config.to_dict(),
            robot_family_descriptor=robot_family_descriptor,
        )
        live_truth_ledger = build_live_truth_ledger(
            session_id=locked["session_id"],
            session_dir=str(session_dir),
            build_id=config.build_id,
            profile=profile_snapshot,
            robot_family_descriptor=robot_family_descriptor,
        )
        repo_truth_ledger_path = self.exp_manager.save_json_artifact(session_dir, "meta/repo_truth_ledger.json", repo_truth_ledger)
        self.exp_manager.append_artifact(session_dir, "repo_truth_ledger", repo_truth_ledger_path)
        live_truth_ledger_path = self.exp_manager.save_json_artifact(session_dir, "meta/live_truth_ledger.json", live_truth_ledger)
        self.exp_manager.append_artifact(session_dir, "live_truth_ledger", live_truth_ledger_path)
        readiness = build_device_readiness(
            config=config,
            device_roster=device_health_snapshot,
            protocol_version=protocol_version,
            calibration_bundle=calibration_payload,
            guidance_algorithm_registry=guidance_registry_payload,
            source_frame_set=source_frame_set_payload,
            localization_readiness=readiness_payload,
            storage_dir=session_dir,
        )
        readiness_path = self.exp_manager.save_json_artifact(session_dir, "meta/device_readiness.json", readiness)
        self.exp_manager.append_artifact(session_dir, "device_readiness", readiness_path)
        xmate_profile_path = self.exp_manager.save_json_artifact(session_dir, "meta/xmate_profile.json", robot_profile)
        self.exp_manager.append_artifact(session_dir, "xmate_profile", xmate_profile_path)
        registration_path = self.exp_manager.save_json_artifact(session_dir, "meta/patient_registration.json", registration_payload)
        self.exp_manager.append_artifact(session_dir, "patient_registration", registration_path)
        localization_readiness_path = self.exp_manager.save_json_artifact(session_dir, "meta/localization_readiness.json", readiness_payload)
        self.exp_manager.append_artifact(session_dir, "localization_readiness", localization_readiness_path)
        calibration_bundle_path = self.exp_manager.save_json_artifact(session_dir, "meta/calibration_bundle.json", calibration_payload)
        self.exp_manager.append_artifact(session_dir, "calibration_bundle", calibration_bundle_path)
        localization_freeze_path = self.exp_manager.save_json_artifact(session_dir, "meta/localization_freeze.json", localization_freeze)
        self.exp_manager.append_artifact(session_dir, "localization_freeze", localization_freeze_path)
        manual_adjustment_path = self.exp_manager.save_json_artifact(session_dir, "meta/manual_adjustment.json", manual_adjustment_payload)
        self.exp_manager.append_artifact(session_dir, "manual_adjustment", manual_adjustment_path)
        source_frame_set_path = self.exp_manager.save_json_artifact(session_dir, "derived/sync/source_frame_set.json", source_frame_set_payload)
        self.exp_manager.append_artifact(session_dir, "source_frame_set", source_frame_set_path)
        replay_index_path = self.exp_manager.save_json_artifact(session_dir, "replay/localization_replay_index.json", replay_payload)
        self.exp_manager.append_artifact(session_dir, "localization_replay_index", replay_index_path)
        scan_protocol = build_scan_protocol(
            session_id=locked["session_id"],
            plan=locked_plan,
            config=config,
            robot_profile=load_xmate_profile(),
            patient_registration=registration_payload,
        )
        protocol_path = self.exp_manager.save_json_artifact(session_dir, "derived/preview/scan_protocol.json", scan_protocol)
        self.exp_manager.append_artifact(session_dir, "scan_protocol", protocol_path)
        for artifact_name, relative_path in {
            "registration_candidate": "derived/guidance/registration_candidate.json",
            "back_roi": "derived/guidance/back_roi.json",
            "midline_polyline": "derived/guidance/midline_polyline.json",
            "landmarks": "derived/guidance/landmarks.json",
            "body_surface": "derived/guidance/body_surface.json",
            "guidance_targets": "derived/guidance/guidance_targets.json",
        }.items():
            payload = self._guidance_artifact_payload(artifact_name=artifact_name, registration_payload=registration_payload)
            path = self.exp_manager.save_json_artifact(session_dir, relative_path, payload)
            self.exp_manager.append_artifact(session_dir, artifact_name, path)
        self.exp_manager.sync_canonical_manifest_fields(
            session_dir,
            device_readiness=readiness,
            robot_profile=robot_profile,
            patient_registration=registration_payload,
            localization_readiness=readiness_payload,
            calibration_bundle=calibration_payload,
            localization_freeze=localization_freeze,
            manual_adjustment=manual_adjustment_payload,
            source_frame_set=source_frame_set_payload,
            scan_protocol=scan_protocol,
            repo_truth_ledger=repo_truth_ledger,
            live_truth_ledger=live_truth_ledger,
            localization_readiness_hash=self._canonical_hash(readiness_payload, preferred_keys=("readiness_hash",)),
            calibration_bundle_hash=self._canonical_hash(calibration_payload, preferred_keys=("bundle_hash",)),
            localization_freeze_hash=self._canonical_hash(localization_freeze, preferred_keys=("freeze_hash",)),
            manual_adjustment_hash=self._canonical_hash(manual_adjustment_payload, preferred_keys=("hash",)),
            source_frame_set_hash=self._canonical_hash(source_frame_set_payload, preferred_keys=("source_frame_set_hash",)),
        )
        self.exp_manager.update_manifest(
            session_dir,
            control_authority=control_authority or {},
            guidance_algorithm_registry=guidance_registry_payload,
            guidance_processing_steps=guidance_steps_payload,
            guidance_version="camera_guidance_v1",
            guidance_mode="guidance_only",
            guidance_source_type=self._resolved_guidance_source_type(patient_registration=registration_payload, localization_readiness=readiness_payload, source_frame_set=source_frame_set_payload, config=config),
        )
        return SessionLockResult(
            session_id=locked["session_id"],
            session_dir=session_dir,
            scan_plan=locked_plan,
            manifest=self.exp_manager.load_manifest(session_dir),
            robot_profile=robot_profile,
            readiness=readiness,
            patient_registration=registration_payload,
            scan_protocol=scan_protocol,
            repo_truth_ledger=repo_truth_ledger,
            live_truth_ledger=live_truth_ledger,
            localization_readiness=readiness_payload,
            calibration_bundle=calibration_payload,
            localization_freeze=localization_freeze,
            manual_adjustment=manual_adjustment_payload,
            source_frame_set=source_frame_set_payload,
        )

    @staticmethod
    def _resolved_guidance_source_type(
        *,
        patient_registration: dict[str, Any],
        localization_readiness: dict[str, Any],
        source_frame_set: dict[str, Any],
        config: RuntimeConfig,
    ) -> str:
        return str(
            patient_registration.get("source_type")
            or localization_readiness.get("source_type")
            or source_frame_set.get("source_type")
            or source_frame_set.get("provider_mode")
            or getattr(config, "camera_guidance_input_mode", "")
            or ""
        )

    @staticmethod
    def _hash_payload(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest() if blob else ""

    @classmethod
    def _canonical_hash(cls, payload: dict[str, Any], *, preferred_keys: tuple[str, ...]) -> str:
        for key in preferred_keys:
            value = str(payload.get(key, ""))
            if value:
                return value
        return cls._hash_payload(payload)

    @staticmethod
    def _requires_guidance_validation(
        *,
        patient_registration: dict[str, Any],
        localization_readiness: dict[str, Any],
        calibration_bundle: dict[str, Any],
        source_frame_set: dict[str, Any],
    ) -> bool:
        return bool(
            patient_registration.get("role") == "guidance_only"
            or localization_readiness
            or calibration_bundle
            or source_frame_set
        )

    def _validate_guidance_freeze_inputs(
        self,
        *,
        patient_registration: dict[str, Any],
        localization_readiness: dict[str, Any],
        calibration_bundle: dict[str, Any],
        source_frame_set: dict[str, Any],
    ) -> None:
        if not self._requires_guidance_validation(
            patient_registration=patient_registration,
            localization_readiness=localization_readiness,
            calibration_bundle=calibration_bundle,
            source_frame_set=source_frame_set,
        ):
            return
        if not localization_readiness:
            raise RuntimeError("guidance readiness payload is required before session lock")
        if not calibration_bundle:
            raise RuntimeError("calibration bundle is required before session lock")
        if not source_frame_set:
            raise RuntimeError("source frame set is required before session lock")
        status = str(localization_readiness.get("status", "BLOCKED"))
        freeze_ready = bool(localization_readiness.get("freeze_gate", {}).get("freeze_ready", False))
        if status != "READY_FOR_FREEZE" or not freeze_ready:
            raise RuntimeError(
                f"guidance bundle is not eligible for session lock: status={status} freeze_ready={freeze_ready}"
            )
        if not str(patient_registration.get("registration_hash", "")):
            raise RuntimeError("patient registration hash is required before session lock")
        if not str(calibration_bundle.get("bundle_hash", "")):
            raise RuntimeError("calibration bundle hash is required before session lock")
        if not str(source_frame_set.get("source_frame_set_hash", "")):
            raise RuntimeError("source frame set hash is required before session lock")

    def _build_localization_freeze(
        self,
        *,
        patient_registration: dict[str, Any],
        localization_readiness: dict[str, Any],
        calibration_bundle: dict[str, Any],
        manual_adjustment: dict[str, Any],
        source_frame_set: dict[str, Any],
        guidance_algorithm_registry: dict[str, Any],
    ) -> dict[str, Any]:
        verdict = str(localization_readiness.get("status", "BLOCKED")).lower()
        if verdict == "ready_for_freeze":
            freeze_verdict = "accepted"
        elif verdict == "ready_with_review":
            freeze_verdict = "reviewed"
        else:
            freeze_verdict = "blocked"
        payload = {
            "schema_version": "1.0",
            "generated_at": patient_registration.get("generated_at", ""),
            "freeze_id": f"freeze::{patient_registration.get('registration_id', 'registration')}",
            "patient_registration_hash": self._canonical_hash(patient_registration, preferred_keys=("registration_hash",)),
            "localization_readiness_hash": self._canonical_hash(localization_readiness, preferred_keys=("readiness_hash",)),
            "calibration_bundle_hash": self._canonical_hash(calibration_bundle, preferred_keys=("bundle_hash",)),
            "algorithm_bundle_hash": self._canonical_hash(guidance_algorithm_registry, preferred_keys=()),
            "source_frame_set_hash": self._canonical_hash(source_frame_set, preferred_keys=("source_frame_set_hash",)),
            "manual_adjustment_hash": self._canonical_hash(manual_adjustment, preferred_keys=("hash",)),
            "freeze_verdict": freeze_verdict,
        }
        payload["freeze_hash"] = self._hash_payload(payload)
        return payload

    @classmethod
    def _guidance_artifact_payload(cls, *, artifact_name: str, registration_payload: dict[str, Any]) -> dict[str, Any]:
        if artifact_name == "registration_candidate":
            payload = {
                "schema_version": "1.0",
                "candidate_id": f"candidate::{registration_payload.get('registration_id', 'registration')}::{registration_payload.get('source_type', 'camera_only')}",
                "source_type": str(registration_payload.get("source_type", "camera_only")),
                "patient_frame": dict(registration_payload.get("patient_frame", {})),
                "scan_corridor": dict(registration_payload.get("scan_corridor", {})),
                "landmarks": list(registration_payload.get("landmarks", [])),
                "quality_metrics": dict(registration_payload.get("quality_metrics", {})),
                "confidence": float(registration_payload.get("registration_quality", {}).get("overall_confidence", 0.0) or 0.0),
                "registration_covariance": dict(registration_payload.get("registration_covariance", {})),
                "usable_segment_count": len(list(registration_payload.get("usable_segments", []))),
                "algorithm_bundle_hash": str(registration_payload.get("algorithm_bundle_hash", "")),
            }
            payload["candidate_hash"] = cls._hash_payload(payload)
            return payload
        if artifact_name == "back_roi":
            return dict(registration_payload.get("back_roi", {}))
        if artifact_name == "midline_polyline":
            return dict(registration_payload.get("midline_polyline", {}))
        if artifact_name == "landmarks":
            return {"items": list(registration_payload.get("landmarks", []))}
        if artifact_name == "body_surface":
            return dict(registration_payload.get("body_surface", {}))
        if artifact_name == "guidance_targets":
            return dict(registration_payload.get("guidance_targets", {}))
        return {}
