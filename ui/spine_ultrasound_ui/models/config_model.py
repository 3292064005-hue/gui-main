from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from spine_ultrasound_ui.utils.mainline_identity_defaults import MAINLINE_IDENTITY_DEFAULTS
from spine_ultrasound_ui.utils.sdk_unit_contract import build_sdk_boundary_contract
from spine_ultrasound_ui.utils.session_freeze_policy import normalize_strict_runtime_freeze_gate


FORBIDDEN_LEGACY_RUNTIME_CONFIG_KEYS = frozenset({
    "fallback_home_joint_rad",
    "fallback_approach_pose_xyzabc",
    "fallback_entry_pose_xyzabc",
    "fallback_retreat_pose_xyzabc",
    "emergency_home_joint_rad",
    "emergency_approach_pose_xyzabc",
    "emergency_entry_pose_xyzabc",
    "emergency_retreat_pose_xyzabc",
    "allow_contract_shell_writes",
})


@dataclass
class ContactControlConfig:
    mode: str = "normal_axis_admittance"
    virtual_mass: float = 0.8
    virtual_damping: float = 120.0
    virtual_stiffness: float = 40.0
    force_deadband_n: float = 0.3
    max_normal_step_mm: float = 0.08
    max_normal_velocity_mm_s: float = 2.0
    max_normal_acc_mm_s2: float = 30.0
    max_normal_travel_mm: float = 8.0
    anti_windup_limit_n: float = 10.0
    integrator_leak: float = 0.02


@dataclass
class ForceEstimatorConfig:
    preferred_source: str = "fused"
    pressure_weight: float = 0.7
    wrench_weight: float = 0.3
    stale_timeout_ms: int = 100
    timeout_ms: int = 250
    auto_bias_zero: bool = True
    min_confidence: float = 0.4


@dataclass
class OrientationTrimConfig:
    gain: float = 0.08
    max_trim_deg: float = 1.5
    lowpass_hz: float = 8.0


@dataclass
class RuntimeConfig:
    pressure_target: float = 8.0
    pressure_upper: float = 12.0
    pressure_lower: float = 5.0
    scan_speed_mm_s: float = 8.0
    sample_step_mm: float = 0.5
    segment_length_mm: float = 120.0
    strip_width_mm: float = 18.0
    strip_overlap_mm: float = 6.0
    contact_seek_speed_mm_s: float = 3.0
    retreat_speed_mm_s: float = 20.0
    seek_contact_max_travel_mm: float = 8.0
    retract_travel_mm: float = 12.0
    scan_follow_lateral_amplitude_mm: float = 0.5
    scan_follow_frequency_hz: float = 0.25
    rt_stale_state_timeout_ms: float = 40.0
    rt_phase_transition_debounce_cycles: int = 5
    rt_max_cart_step_mm: float = 0.25
    rt_max_cart_vel_mm_s: float = 25.0
    rt_max_cart_acc_mm_s2: float = 200.0
    rt_max_pose_trim_deg: float = 1.5
    rt_max_force_error_n: float = 8.0
    rt_integrator_limit_n: float = 10.0
    contact_force_target_n: float = 8.0
    contact_force_tolerance_n: float = 1.0
    contact_establish_cycles: int = 12
    normal_admittance_gain: float = 0.00012
    normal_damping_gain: float = 0.00004
    seek_contact_max_step_mm: float = 0.08
    normal_velocity_quiet_threshold_mm_s: float = 0.3
    scan_force_target_n: float = 8.0
    scan_force_tolerance_n: float = 1.0
    scan_normal_pi_kp: float = 0.012
    scan_normal_pi_ki: float = 0.008
    scan_tangent_speed_min_mm_s: float = 2.0
    scan_tangent_speed_max_mm_s: float = 12.0
    scan_pose_trim_gain: float = 0.08
    scan_follow_enable_lateral_modulation: bool = True
    pause_hold_position_guard_mm: float = 0.4
    pause_hold_force_guard_n: float = 3.0
    pause_hold_drift_kp: float = 0.010
    pause_hold_drift_ki: float = 0.004
    pause_hold_integrator_leak: float = 0.02
    retract_release_force_n: float = 1.5
    retract_release_cycles: int = 6
    retract_safe_gap_mm: float = 3.0
    retract_max_travel_mm: float = 15.0
    retract_jerk_limit_mm_s3: float = 500.0
    retract_timeout_ms: float = 1200.0
    image_quality_threshold: float = 0.7
    roi_mode: str = "auto"
    smoothing_factor: float = 0.35
    reconstruction_step: float = 0.5
    feature_threshold: float = 0.6
    rt_mode: str = "cartesianImpedance"
    network_stale_ms: int = 150
    strict_runtime_freeze_gate: str = "enforce"
    pressure_stale_ms: int = 100
    telemetry_rate_hz: int = 20
    tool_name: str = "ultrasound_probe"
    tcp_name: str = "ultrasound_tcp"
    load_kg: float = 0.85
    remote_ip: str = "192.168.0.160"
    local_ip: str = "192.168.0.100"
    force_sensor_provider: str = "mock_force_sensor"
    contact_control: ContactControlConfig = field(default_factory=ContactControlConfig)
    force_estimator: ForceEstimatorConfig = field(default_factory=ForceEstimatorConfig)
    orientation_trim: OrientationTrimConfig = field(default_factory=OrientationTrimConfig)
    robot_model: str = MAINLINE_IDENTITY_DEFAULTS.robot_model
    axis_count: int = MAINLINE_IDENTITY_DEFAULTS.axis_count
    sdk_robot_class: str = MAINLINE_IDENTITY_DEFAULTS.sdk_robot_class
    preferred_link: str = MAINLINE_IDENTITY_DEFAULTS.preferred_link
    requires_single_control_source: bool = True
    build_id: str = "dev"
    software_version: str = "0.3.0"
    runtime_config_contract_digest: str = ""
    runtime_config_schema_version: str = ""
    camera_guidance_input_mode: str = "synthetic"
    camera_guidance_source_path: str = ""
    camera_guidance_file_glob: str = "*.npy"
    camera_guidance_frame_count: int = 3
    camera_capture_device_index: int = 0
    camera_capture_timeout_ms: int = 500
    guidance_review_operator_id: str = "operator"
    rt_network_tolerance_percent: int = 15
    joint_filter_hz: float = 40.0
    cart_filter_hz: float = 30.0
    torque_filter_hz: float = 25.0
    collision_detection_enabled: bool = True
    collision_sensitivity: int = 4
    collision_behavior: str = "pause_hold"
    collision_fallback_mm: float = 8.0
    soft_limit_enabled: bool = True
    joint_soft_limit_margin_deg: float = 5.0
    singularity_avoidance_enabled: bool = True
    rl_project_name: str = "spine_mainline"
    rl_task_name: str = "scan"
    xpanel_vout_mode: str = "off"
    cartesian_impedance: List[float] = field(default_factory=lambda: [1000.0, 1000.0, 1000.0, 80.0, 80.0, 80.0])
    desired_wrench_n: List[float] = field(default_factory=lambda: [0.0, 0.0, 8.0, 0.0, 0.0, 0.0])
    fc_frame_type: str = "path"
    fc_frame_matrix: List[float] = field(default_factory=lambda: [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ])
    tcp_frame_matrix: List[float] = field(default_factory=lambda: [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 62.0,
        0.0, 0.0, 0.0, 1.0,
    ])
    load_com_mm: List[float] = field(default_factory=lambda: [0.0, 0.0, 62.0])
    load_inertia: List[float] = field(default_factory=lambda: [0.0012, 0.0012, 0.0008, 0.0, 0.0, 0.0])
    home_joint_rad: List[float] = field(default_factory=lambda: [0.0, 0.30, 0.60, 0.0, 1.20, 0.0, 0.0])


    def build_rt_phase_contract(self) -> Dict[str, Any]:
        return {
            "common": {
                "rt_stale_state_timeout_ms": self.rt_stale_state_timeout_ms,
                "rt_phase_transition_debounce_cycles": self.rt_phase_transition_debounce_cycles,
                "rt_max_cart_step_mm": self.rt_max_cart_step_mm,
                "rt_max_cart_vel_mm_s": self.rt_max_cart_vel_mm_s,
                "rt_max_cart_acc_mm_s2": self.rt_max_cart_acc_mm_s2,
                "rt_max_pose_trim_deg": self.rt_max_pose_trim_deg,
                "rt_max_force_error_n": self.rt_max_force_error_n,
                "rt_integrator_limit_n": self.rt_integrator_limit_n,
            },
            "seek_contact": {
                "contact_force_target_n": self.contact_force_target_n,
                "contact_force_tolerance_n": self.contact_force_tolerance_n,
                "contact_establish_cycles": self.contact_establish_cycles,
                "normal_admittance_gain": self.normal_admittance_gain,
                "normal_damping_gain": self.normal_damping_gain,
                "seek_contact_max_step_mm": self.seek_contact_max_step_mm,
                "seek_contact_max_travel_mm": self.seek_contact_max_travel_mm,
                "contact_control": asdict(self.contact_control),
                "force_estimator": asdict(self.force_estimator),
                "normal_velocity_quiet_threshold_mm_s": self.normal_velocity_quiet_threshold_mm_s,
            },
            "scan_follow": {
                "scan_force_target_n": self.scan_force_target_n,
                "scan_force_tolerance_n": self.scan_force_tolerance_n,
                "scan_normal_pi_kp": self.scan_normal_pi_kp,
                "scan_normal_pi_ki": self.scan_normal_pi_ki,
                "scan_tangent_speed_min_mm_s": self.scan_tangent_speed_min_mm_s,
                "scan_tangent_speed_max_mm_s": self.scan_tangent_speed_max_mm_s,
                "scan_pose_trim_gain": self.scan_pose_trim_gain,
                "scan_follow_enable_lateral_modulation": self.scan_follow_enable_lateral_modulation,
                "orientation_trim": asdict(self.orientation_trim),
                "scan_follow_lateral_amplitude_mm": self.scan_follow_lateral_amplitude_mm,
                "scan_follow_frequency_hz": self.scan_follow_frequency_hz,
            },
            "pause_hold": {
                "pause_hold_position_guard_mm": self.pause_hold_position_guard_mm,
                "pause_hold_force_guard_n": self.pause_hold_force_guard_n,
                "pause_hold_drift_kp": self.pause_hold_drift_kp,
                "pause_hold_drift_ki": self.pause_hold_drift_ki,
                "pause_hold_integrator_leak": self.pause_hold_integrator_leak,
            },
            "controlled_retract": {
                "retract_release_force_n": self.retract_release_force_n,
                "retract_release_cycles": self.retract_release_cycles,
                "retract_safe_gap_mm": self.retract_safe_gap_mm,
                "retract_max_travel_mm": self.retract_max_travel_mm,
                "retract_jerk_limit_mm_s3": self.retract_jerk_limit_mm_s3,
                "retract_timeout_ms": self.retract_timeout_ms,
                "retract_travel_mm": self.retract_travel_mm,
            },
        }

    def to_dict(self) -> Dict[str, Any]:
        from spine_ultrasound_ui.utils.runtime_config_contract import runtime_config_contract_metadata

        payload = asdict(self)
        payload["contact_control"] = asdict(self.contact_control)
        payload["force_estimator"] = asdict(self.force_estimator)
        payload["orientation_trim"] = asdict(self.orientation_trim)
        payload["sdk_boundary_units"] = build_sdk_boundary_contract(
            fc_frame_matrix=self.fc_frame_matrix,
            tcp_frame_matrix=self.tcp_frame_matrix,
            load_com_mm=self.load_com_mm,
        )
        payload["rt_phase_contract"] = self.build_rt_phase_contract()
        payload["strict_runtime_freeze_gate"] = normalize_strict_runtime_freeze_gate(self.strict_runtime_freeze_gate)
        contract_metadata = runtime_config_contract_metadata()
        payload["runtime_config_contract"] = contract_metadata
        payload["runtime_config_contract_digest"] = str(contract_metadata.get("digest", ""))
        payload["runtime_config_schema_version"] = str(contract_metadata.get("schema_version", ""))
        return payload

    def sdk_boundary_contract(self) -> Dict[str, Any]:
        return build_sdk_boundary_contract(
            fc_frame_matrix=self.fc_frame_matrix,
            tcp_frame_matrix=self.tcp_frame_matrix,
            load_com_mm=self.load_com_mm,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeConfig":
        payload = dict(data)
        if "scan_speed" in payload and "scan_speed_mm_s" not in payload:
            payload["scan_speed_mm_s"] = payload.pop("scan_speed")
        if "network_tolerance" in payload and "network_stale_ms" not in payload:
            payload["network_stale_ms"] = int(payload.pop("network_tolerance")) * 10
        if "load_mass_kg" in payload and "load_kg" not in payload:
            payload["load_kg"] = payload.pop("load_mass_kg")
        payload["strict_runtime_freeze_gate"] = normalize_strict_runtime_freeze_gate(payload.get("strict_runtime_freeze_gate"))
        runtime_config_contract = payload.get("runtime_config_contract", {})
        if isinstance(runtime_config_contract, dict):
            payload["runtime_config_contract"] = dict(runtime_config_contract)
            payload.setdefault("runtime_config_contract_digest", str(runtime_config_contract.get("digest", "")))
            payload.setdefault("runtime_config_schema_version", str(runtime_config_contract.get("schema_version", "")))
        else:
            payload.pop("runtime_config_contract", None)
        forbidden_legacy_keys = sorted(FORBIDDEN_LEGACY_RUNTIME_CONFIG_KEYS.intersection(payload))
        if forbidden_legacy_keys:
            raise ValueError(
                "runtime config contains forbidden legacy keys that are no longer supported: "
                + ", ".join(forbidden_legacy_keys)
            )

        rt_phase_contract = payload.get("rt_phase_contract")
        if isinstance(rt_phase_contract, dict):
            for section_name, section_payload in rt_phase_contract.items():
                if isinstance(section_payload, dict):
                    payload.update(section_payload)

        contact_control_payload = payload.get("contact_control", {})
        if isinstance(contact_control_payload, dict):
            payload["contact_control"] = ContactControlConfig(**{k: v for k, v in contact_control_payload.items() if k in ContactControlConfig.__dataclass_fields__})
        else:
            payload["contact_control"] = ContactControlConfig()
        force_estimator_payload = payload.get("force_estimator", {})
        if isinstance(force_estimator_payload, dict):
            payload["force_estimator"] = ForceEstimatorConfig(**{k: v for k, v in force_estimator_payload.items() if k in ForceEstimatorConfig.__dataclass_fields__})
        else:
            payload["force_estimator"] = ForceEstimatorConfig()
        orientation_trim_payload = payload.get("orientation_trim", {})
        if isinstance(orientation_trim_payload, dict):
            payload["orientation_trim"] = OrientationTrimConfig(**{k: v for k, v in orientation_trim_payload.items() if k in OrientationTrimConfig.__dataclass_fields__})
        else:
            payload["orientation_trim"] = OrientationTrimConfig()

        # synchronize derived flat-field values from the canonical nested sections
        cc = payload["contact_control"]
        if not isinstance(contact_control_payload, dict) or not contact_control_payload:
            cc.mode = str(payload.get("contact_control_mode", cc.mode))
            cc.max_normal_step_mm = float(payload.get("seek_contact_max_step_mm", cc.max_normal_step_mm))
            cc.max_normal_travel_mm = float(payload.get("seek_contact_max_travel_mm", cc.max_normal_travel_mm))
            cc.anti_windup_limit_n = float(payload.get("rt_integrator_limit_n", cc.anti_windup_limit_n))
            cc.integrator_leak = float(payload.get("pause_hold_integrator_leak", cc.integrator_leak))
            flat_gain = payload.get("normal_admittance_gain")
            flat_damping = payload.get("normal_damping_gain")
            if flat_gain is not None:
                cc.virtual_mass = max(0.05, 1.0 / max(float(flat_gain), 1e-6) / 10000.0)
            if flat_damping is not None:
                cc.virtual_damping = max(5.0, 1.0 / max(float(flat_damping), 1e-6) / 10000.0)
            cc.max_normal_velocity_mm_s = float(payload.get("rt_max_cart_vel_mm_s", cc.max_normal_velocity_mm_s if cc.max_normal_velocity_mm_s > 0 else 2.0))
            cc.max_normal_acc_mm_s2 = float(payload.get("rt_max_cart_acc_mm_s2", cc.max_normal_acc_mm_s2 if cc.max_normal_acc_mm_s2 > 0 else 30.0))
        fe = payload["force_estimator"]
        if not isinstance(force_estimator_payload, dict) or not force_estimator_payload:
            fe.preferred_source = str(payload.get("force_estimator_preferred_source", fe.preferred_source))
            fe.stale_timeout_ms = int(payload.get("pressure_stale_ms", fe.stale_timeout_ms))
            fe.timeout_ms = int(payload.get("force_estimator_timeout_ms", fe.timeout_ms))
            fe.min_confidence = float(payload.get("force_estimator_min_confidence", fe.min_confidence))
        ot = payload["orientation_trim"]
        if not isinstance(orientation_trim_payload, dict) or not orientation_trim_payload:
            ot.gain = float(payload.get("scan_pose_trim_gain", ot.gain))
            ot.max_trim_deg = float(payload.get("rt_max_pose_trim_deg", ot.max_trim_deg))
            ot.lowpass_hz = float(payload.get("orientation_trim_lowpass_hz", ot.lowpass_hz))

        payload["seek_contact_max_step_mm"] = float(payload.get("seek_contact_max_step_mm", cc.max_normal_step_mm))
        payload["seek_contact_max_travel_mm"] = float(payload.get("seek_contact_max_travel_mm", cc.max_normal_travel_mm))
        payload["normal_damping_gain"] = float(payload.get("normal_damping_gain", max(1e-6, 1.0 / max(cc.virtual_damping, 1.0) / 10000.0)))
        payload["normal_admittance_gain"] = float(payload.get("normal_admittance_gain", max(1e-6, 1.0 / max(cc.virtual_mass, 0.05) / 10000.0)))
        payload["pause_hold_integrator_leak"] = float(payload.get("pause_hold_integrator_leak", cc.integrator_leak))
        payload["rt_integrator_limit_n"] = float(payload.get("rt_integrator_limit_n", cc.anti_windup_limit_n))
        ot = payload["orientation_trim"]
        payload["scan_pose_trim_gain"] = float(payload.get("scan_pose_trim_gain", ot.gain))
        payload["rt_max_pose_trim_deg"] = float(payload.get("rt_max_pose_trim_deg", ot.max_trim_deg))
        return cls(**{k: v for k, v in payload.items() if k in cls.__dataclass_fields__})


ConfigModel = RuntimeConfig
