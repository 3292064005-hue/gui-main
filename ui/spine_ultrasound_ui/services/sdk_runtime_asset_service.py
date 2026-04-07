from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils.sdk_unit_contract import build_sdk_boundary_contract
from spine_ultrasound_ui.services.backend_base import BackendBase
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.services.sdk_environment_doctor_service import SdkEnvironmentDoctorService
from spine_ultrasound_ui.services.mainline_runtime_doctor_service import MainlineRuntimeDoctorService
from spine_ultrasound_ui.services.mainline_task_tree_service import MainlineTaskTreeService
from spine_ultrasound_ui.services.robot_family_registry_service import RobotFamilyRegistryService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService


@dataclass
class SdkRuntimeAssetSnapshot:
    controller_logs: list[dict[str, Any]] = field(default_factory=list)
    rl_projects: list[dict[str, Any]] = field(default_factory=list)
    rl_status: dict[str, Any] = field(default_factory=dict)
    path_library: list[dict[str, Any]] = field(default_factory=list)
    drag_status: dict[str, Any] = field(default_factory=dict)
    io_snapshot: dict[str, Any] = field(default_factory=dict)
    safety_profile: dict[str, Any] = field(default_factory=dict)
    motion_contract: dict[str, Any] = field(default_factory=dict)
    register_snapshot: dict[str, Any] = field(default_factory=dict)
    runtime_alignment: dict[str, Any] = field(default_factory=dict)
    xmate_model_summary: dict[str, Any] = field(default_factory=dict)
    runtime_config_snapshot: dict[str, Any] = field(default_factory=dict)
    environment_doctor: dict[str, Any] = field(default_factory=dict)
    identity_contract: dict[str, Any] = field(default_factory=dict)
    robot_family_contract: dict[str, Any] = field(default_factory=dict)
    vendor_boundary_contract: dict[str, Any] = field(default_factory=dict)
    profile_matrix_contract: dict[str, Any] = field(default_factory=dict)
    clinical_mainline_contract: dict[str, Any] = field(default_factory=dict)
    capability_contract: dict[str, Any] = field(default_factory=dict)
    model_authority_contract: dict[str, Any] = field(default_factory=dict)
    session_freeze: dict[str, Any] = field(default_factory=dict)
    session_drift_contract: dict[str, Any] = field(default_factory=dict)
    hardware_lifecycle_contract: dict[str, Any] = field(default_factory=dict)
    rt_kernel_contract: dict[str, Any] = field(default_factory=dict)
    control_governance_contract: dict[str, Any] = field(default_factory=dict)
    controller_evidence: dict[str, Any] = field(default_factory=dict)
    mainline_runtime_doctor: dict[str, Any] = field(default_factory=dict)
    dual_state_machine_contract: dict[str, Any] = field(default_factory=dict)
    mainline_executor_contract: dict[str, Any] = field(default_factory=dict)
    mainline_task_tree: dict[str, Any] = field(default_factory=dict)
    recovery_contract: dict[str, Any] = field(default_factory=dict)
    safety_recovery_contract: dict[str, Any] = field(default_factory=dict)
    release_contract: dict[str, Any] = field(default_factory=dict)
    deployment_contract: dict[str, Any] = field(default_factory=dict)
    fault_injection_contract: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "controller_logs": list(self.controller_logs),
            "rl_projects": list(self.rl_projects),
            "rl_status": dict(self.rl_status),
            "path_library": list(self.path_library),
            "drag_status": dict(self.drag_status),
            "io_snapshot": dict(self.io_snapshot),
            "safety_profile": dict(self.safety_profile),
            "motion_contract": dict(self.motion_contract),
            "register_snapshot": dict(self.register_snapshot),
            "runtime_alignment": dict(self.runtime_alignment),
            "xmate_model_summary": dict(self.xmate_model_summary),
            "runtime_config_snapshot": dict(self.runtime_config_snapshot),
            "environment_doctor": dict(self.environment_doctor),
            "identity_contract": dict(self.identity_contract),
            "robot_family_contract": dict(self.robot_family_contract),
            "vendor_boundary_contract": dict(self.vendor_boundary_contract),
            "profile_matrix_contract": dict(self.profile_matrix_contract),
            "clinical_mainline_contract": dict(self.clinical_mainline_contract),
            "capability_contract": dict(self.capability_contract),
            "model_authority_contract": dict(self.model_authority_contract),
            "session_freeze": dict(self.session_freeze),
            "session_drift_contract": dict(self.session_drift_contract),
            "hardware_lifecycle_contract": dict(self.hardware_lifecycle_contract),
            "rt_kernel_contract": dict(self.rt_kernel_contract),
            "control_governance_contract": dict(self.control_governance_contract),
            "controller_evidence": dict(self.controller_evidence),
            "mainline_runtime_doctor": dict(self.mainline_runtime_doctor),
            "dual_state_machine_contract": dict(self.dual_state_machine_contract),
            "mainline_executor_contract": dict(self.mainline_executor_contract),
            "mainline_task_tree": dict(self.mainline_task_tree),
            "recovery_contract": dict(self.recovery_contract),
            "safety_recovery_contract": dict(self.safety_recovery_contract),
            "release_contract": dict(self.release_contract),
            "deployment_contract": dict(self.deployment_contract),
            "fault_injection_contract": dict(self.fault_injection_contract),
            "errors": list(self.errors),
        }


class SdkRuntimeAssetService:
    """Best-effort operational asset aggregator.

    The UI uses this service to surface runtime-facing SDK capabilities such as
    controller logs, RL project inventory, path replay inventory, I/O state, and
    safety governance settings. Failures are captured as asset errors instead of
    crashing the mainline UI.
    """

    def __init__(self) -> None:
        self.snapshot = SdkRuntimeAssetSnapshot()
        self.doctor = SdkEnvironmentDoctorService()
        self.mainline_doctor = MainlineRuntimeDoctorService()
        self.task_tree = MainlineTaskTreeService()
        self.family_registry = RobotFamilyRegistryService()
        self.deployment_profiles = DeploymentProfileService()

    def refresh(self, backend: BackendBase, config: RuntimeConfig) -> dict[str, Any]:
        self.snapshot = SdkRuntimeAssetSnapshot()
        self.snapshot.controller_logs = list(self._query_list(backend, "query_controller_log", {"count": 12, "level": "INFO"}, "logs"))
        rl_payload = self._query_data(backend, "query_rl_projects", {}, default={})
        self.snapshot.rl_projects = list(rl_payload.get("projects", []))
        self.snapshot.rl_status = dict(rl_payload.get("status", {}))
        path_payload = self._query_data(backend, "query_path_lists", {}, default={})
        self.snapshot.path_library = list(path_payload.get("paths", []))
        self.snapshot.drag_status = dict(path_payload.get("drag", {}))
        self.snapshot.io_snapshot = dict(self._query_data(backend, "get_io_snapshot", {}, default={}))
        self.snapshot.safety_profile = dict(self._query_data(backend, "get_safety_config", {}, default={}))
        motion_contract = dict(self._query_data(backend, "get_motion_contract", {}, default={}))
        motion_contract.setdefault("rt_mode", config.rt_mode)
        motion_contract.setdefault("preferred_link", config.preferred_link)
        motion_contract.setdefault("network_tolerance_percent", config.rt_network_tolerance_percent)
        motion_contract.setdefault("sdk_boundary_units", build_sdk_boundary_contract(fc_frame_matrix=config.fc_frame_matrix, tcp_frame_matrix=config.tcp_frame_matrix, load_com_mm=config.load_com_mm))
        self.snapshot.motion_contract = motion_contract
        self.snapshot.register_snapshot = dict(self._query_data(backend, "get_register_snapshot", {}, default={}))
        self.snapshot.runtime_alignment = dict(self._query_data(backend, "get_runtime_alignment", {}, default={}))
        self.snapshot.xmate_model_summary = dict(self._query_data(backend, "get_xmate_model_summary", {}, default={}))
        self.snapshot.runtime_config_snapshot = dict(self._query_data(backend, "get_sdk_runtime_config", {}, default={}))
        self.snapshot.environment_doctor = dict(self.doctor.inspect(config))
        self.snapshot.identity_contract = dict(self._query_data(backend, "get_identity_contract", {}, default={}))
        self.snapshot.robot_family_contract = dict(self._query_data(backend, "get_robot_family_contract", {}, default=self.family_registry.build_contract(config)))
        self.snapshot.vendor_boundary_contract = dict(self._query_data(backend, "get_vendor_boundary_contract", {}, default={"summary_state": "warning", "detail": "runtime did not expose vendor boundary contract", "binding_mode": "unknown"}))
        self.snapshot.profile_matrix_contract = dict(self.deployment_profiles.build_snapshot(config))
        self.snapshot.clinical_mainline_contract = dict(self._query_data(backend, "get_clinical_mainline_contract", {}, default={}))
        self.snapshot.capability_contract = dict(self._query_data(backend, "get_capability_contract", {}, default={}))
        self.snapshot.model_authority_contract = dict(self._query_data(backend, "get_model_authority_contract", {}, default={}))
        self.snapshot.session_freeze = dict(self._query_data(backend, "get_session_freeze", {}, default={}))
        self.snapshot.session_drift_contract = dict(self._query_data(backend, "get_session_drift_contract", {}, default={}))
        self.snapshot.hardware_lifecycle_contract = dict(self._query_data(backend, "get_hardware_lifecycle_contract", {}, default={}))
        self.snapshot.rt_kernel_contract = dict(self._query_data(backend, "get_rt_kernel_contract", {}, default={}))
        self.snapshot.control_governance_contract = dict(self._query_data(backend, "get_control_governance_contract", {}, default={}))
        self.snapshot.controller_evidence = dict(self._query_data(backend, "get_controller_evidence", {}, default={}))
        self.snapshot.dual_state_machine_contract = dict(self._query_data(backend, "get_dual_state_machine_contract", {}, default={}))
        self.snapshot.mainline_executor_contract = dict(self._query_data(backend, "get_mainline_executor_contract", {}, default={}))
        self.snapshot.recovery_contract = dict(self._query_data(backend, "get_recovery_contract", {}, default={}))
        self.snapshot.safety_recovery_contract = dict(self._query_data(backend, "get_safety_recovery_contract", {}, default=self.snapshot.recovery_contract))
        self.snapshot.release_contract = dict(self._query_data(backend, "get_release_contract", {}, default={}))
        self.snapshot.deployment_contract = dict(self._query_data(backend, "get_deployment_contract", {}, default={}))
        self.snapshot.fault_injection_contract = dict(self._query_data(backend, "get_fault_injection_contract", {}, default={}))
        backend_link = backend.link_snapshot() if hasattr(backend, "link_snapshot") else {}
        self.snapshot.mainline_task_tree = dict(self.task_tree.build(
            config=config,
            sdk_runtime=self.snapshot.to_dict(),
            backend_link=backend_link,
            model_report={},
            session_governance={},
        ))
        self.snapshot.mainline_runtime_doctor = dict(self.mainline_doctor.inspect(
            config=config,
            sdk_runtime=self.snapshot.to_dict(),
            backend_link=backend_link,
            model_report={},
            session_governance={},
        ))
        return self.snapshot.to_dict()

    def _query_list(self, backend: BackendBase, command: str, payload: dict[str, Any], key: str) -> list[dict[str, Any]]:
        data = self._query_data(backend, command, payload, default={})
        values = data.get(key, [])
        return values if isinstance(values, list) else []

    def _query_data(self, backend: BackendBase, command: str, payload: dict[str, Any], *, default: dict[str, Any]) -> dict[str, Any]:
        try:
            reply = backend.send_command(command, payload)
        except Exception as exc:
            self.snapshot.errors.append(f"{command}: {exc}")
            return dict(default)
        if not isinstance(reply, ReplyEnvelope):
            self.snapshot.errors.append(f"{command}: invalid reply envelope")
            return dict(default)
        if not reply.ok:
            self.snapshot.errors.append(f"{command}: {reply.message}")
            return dict(default)
        return dict(reply.data or {})
