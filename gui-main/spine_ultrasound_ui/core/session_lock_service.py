from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import platform
from typing import Any

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan
from spine_ultrasound_ui.services.device_readiness import build_device_readiness
from spine_ultrasound_ui.services.spine_scan_protocol import build_scan_protocol
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile


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
            patient_registration_hash=patient_registration_hash,
            force_sensor_provider=config.force_sensor_provider,
            safety_thresholds=safety_thresholds or {},
            device_health_snapshot=device_health_snapshot or {},
            robot_profile=robot_profile,
            patient_registration=registration_payload,
            scan_protocol={},
            control_authority=control_authority or {},
        )
        session_dir = Path(locked["session_dir"])
        locked_plan = ScanPlan.from_dict(locked["scan_plan"])
        readiness = build_device_readiness(config=config, device_roster=device_health_snapshot, protocol_version=protocol_version)
        readiness_path = self.exp_manager.save_json_artifact(session_dir, "meta/device_readiness.json", readiness)
        self.exp_manager.append_artifact(session_dir, "device_readiness", readiness_path)
        xmate_profile_path = self.exp_manager.save_json_artifact(session_dir, "meta/xmate_profile.json", robot_profile)
        self.exp_manager.append_artifact(session_dir, "xmate_profile", xmate_profile_path)
        registration_path = self.exp_manager.save_json_artifact(session_dir, "meta/patient_registration.json", registration_payload)
        self.exp_manager.append_artifact(session_dir, "patient_registration", registration_path)
        scan_protocol = build_scan_protocol(
            session_id=locked["session_id"],
            plan=locked_plan,
            config=config,
            robot_profile=load_xmate_profile(),
            patient_registration=registration_payload,
        )
        protocol_path = self.exp_manager.save_json_artifact(session_dir, "derived/preview/scan_protocol.json", scan_protocol)
        self.exp_manager.append_artifact(session_dir, "scan_protocol", protocol_path)
        self.exp_manager.update_manifest(
            session_dir,
            device_readiness=readiness,
            robot_profile=robot_profile,
            patient_registration=registration_payload,
            scan_protocol=scan_protocol,
            control_authority=control_authority or {},
        )
        return SessionLockResult(
            session_id=locked["session_id"],
            session_dir=session_dir,
            scan_plan=locked_plan,
            manifest=locked["manifest"],
            robot_profile=robot_profile,
            readiness=readiness,
            patient_registration=registration_payload,
            scan_protocol=scan_protocol,
        )
