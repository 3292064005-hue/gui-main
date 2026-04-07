from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.robot_identity_service import RobotIdentityService
from spine_ultrasound_ui.utils.sdk_unit_contract import with_sdk_boundary_fields


@dataclass
class DhParameter:
    joint: int
    a_mm: float
    alpha_rad: float
    d_mm: float
    theta_rad: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class XMateProfile:
    robot_model: str = "xmate3"
    sdk_robot_class: str = "xMateRobot"
    controller_series: str = "xCore"
    controller_version: str = "v2.1+"
    axis_count: int = 6
    remote_ip: str = "192.168.0.160"
    local_ip: str = "192.168.0.100"
    preferred_link: str = "wired_direct"
    requires_single_control_source: bool = True
    realtime_client_language: str = "C++"
    rt_loop_hz: int = 1000
    rt_mode: str = "cartesianImpedance"
    supported_rt_modes: list[str] = field(default_factory=lambda: [
        "jointPosition",
        "cartesianPosition",
        "jointImpedance",
        "cartesianImpedance",
        "directTorque",
    ])
    clinical_allowed_modes: list[str] = field(default_factory=lambda: [
        "MoveAbsJ",
        "MoveJ",
        "MoveL",
        "cartesianImpedance",
    ])
    direct_torque_in_clinical_mainline: bool = False
    tool_name: str = "ultrasound_probe"
    tcp_name: str = "ultrasound_tcp"
    work_object: str = "patient_spine"
    load_mass_kg: float = 0.85
    load_com_mm: list[float] = field(default_factory=lambda: [0.0, 0.0, 62.0])
    load_inertia: list[float] = field(default_factory=lambda: [0.0012, 0.0012, 0.0008, 0.0, 0.0, 0.0])
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
    cartesian_impedance: list[float] = field(default_factory=lambda: [1000.0, 1000.0, 1000.0, 80.0, 80.0, 80.0])
    desired_wrench_n: list[float] = field(default_factory=lambda: [0.0, 0.0, 8.0, 0.0, 0.0, 0.0])
    fc_frame_type: str = "path"
    fc_frame_matrix: list[float] = field(default_factory=lambda: [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 0.0,
        0.0, 0.0, 0.0, 1.0,
    ])
    tcp_frame_matrix: list[float] = field(default_factory=lambda: [
        1.0, 0.0, 0.0, 0.0,
        0.0, 1.0, 0.0, 0.0,
        0.0, 0.0, 1.0, 62.0,
        0.0, 0.0, 0.0, 1.0,
    ])
    strip_width_mm: float = 18.0
    strip_overlap_mm: float = 6.0
    approach_clearance_mm: float = 24.0
    contact_guard_margin_mm: float = 5.0
    seek_contact_max_travel_mm: float = 8.0
    retract_travel_mm: float = 12.0
    scan_follow_lateral_amplitude_mm: float = 0.5
    scan_follow_frequency_hz: float = 0.25
    rt_stale_state_timeout_ms: float = 40.0
    pressure_stale_ms: int = 100
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
    surface_tilt_limits_deg: dict[str, float] = field(default_factory=lambda: {"roll": 8.0, "pitch": 6.0, "yaw": 15.0})
    contact_force_policy: dict[str, float] = field(default_factory=lambda: {
        "target_n": 8.0,
        "warning_n": 12.0,
        "hard_limit_n": 20.0,
        "settle_band_n": 1.0,
        "settle_window_ms": 200.0,
    })
    sweep_policy: dict[str, float] = field(default_factory=lambda: {
        "scan_speed_mm_s": 8.0,
        "contact_seek_speed_mm_s": 3.0,
        "retreat_speed_mm_s": 20.0,
        "rescan_quality_threshold": 0.7,
        "max_rescan_passes": 2.0,
        "max_scan_travel_mm": 120.0,
    })
    motion_sequence: list[str] = field(default_factory=lambda: [
        "approach_nrt",
        "seek_contact_rt_cartesian_impedance",
        "scan_rt_cartesian_impedance",
        "safe_retreat",
    ])
    dh_parameters: list[DhParameter] = field(default_factory=lambda: [
        DhParameter(1, 0.0, -1.57079632679, 341.5),
        DhParameter(2, 394.0, 0.0, 0.0),
        DhParameter(3, 0.0, 1.57079632679, 0.0),
        DhParameter(4, 0.0, -1.57079632679, 366.0),
        DhParameter(5, 0.0, 1.57079632679, 0.0),
        DhParameter(6, 0.0, 0.0, 250.3),
    ])
    contact_control: dict[str, Any] = field(default_factory=dict)
    force_estimator: dict[str, Any] = field(default_factory=dict)
    orientation_trim: dict[str, Any] = field(default_factory=dict)
    compatibility_warnings: list[str] = field(default_factory=list)
    force_estimator_preferred_source: str = "fused"
    force_estimator_timeout_ms: int = 250
    force_estimator_min_confidence: float = 0.4

    def __post_init__(self) -> None:
        self.contact_control = self._normalize_contact_control(self.contact_control)
        self.force_estimator = self._normalize_force_estimator(self.force_estimator)
        self.orientation_trim = self._normalize_orientation_trim(self.orientation_trim)

    def _legacy_contact_control_defaults(self) -> dict[str, Any]:
        return {
            "mode": "normal_axis_admittance",
            "virtual_mass": max(0.05, 1.0 / max(self.normal_admittance_gain, 1e-6) / 10000.0),
            "virtual_damping": max(1.0, 1.0 / max(self.normal_damping_gain, 1e-6) / 10000.0),
            "virtual_stiffness": max(10.0, self.scan_normal_pi_kp * 1000.0),
            "force_deadband_n": 0.3,
            "max_normal_step_mm": self.seek_contact_max_step_mm,
            "max_normal_velocity_mm_s": min(self.rt_max_cart_vel_mm_s, 2.0),
            "max_normal_acc_mm_s2": min(self.rt_max_cart_acc_mm_s2, 30.0),
            "max_normal_travel_mm": self.seek_contact_max_travel_mm,
            "anti_windup_limit_n": self.rt_integrator_limit_n,
            "integrator_leak": self.pause_hold_integrator_leak,
        }

    def _legacy_force_estimator_defaults(self) -> dict[str, Any]:
        return {
            "preferred_source": str(self.force_estimator_preferred_source or "fused"),
            "pressure_weight": 0.7,
            "wrench_weight": 0.3,
            "stale_timeout_ms": int(self.pressure_stale_ms),
            "timeout_ms": max(1, int(self.force_estimator_timeout_ms)),
            "auto_bias_zero": True,
            "min_confidence": float(self.force_estimator_min_confidence),
        }

    def _legacy_orientation_trim_defaults(self) -> dict[str, Any]:
        return {
            "gain": self.scan_pose_trim_gain,
            "max_trim_deg": self.rt_max_pose_trim_deg,
            "lowpass_hz": 8.0,
        }

    def _normalize_contact_control(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        data = self._legacy_contact_control_defaults()
        if isinstance(payload, dict):
            data.update({k: payload[k] for k in payload if k in data})
        return data

    def _normalize_force_estimator(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        data = self._legacy_force_estimator_defaults()
        if isinstance(payload, dict):
            data.update({k: payload[k] for k in payload if k in data})
        return data

    def _normalize_orientation_trim(self, payload: dict[str, Any] | None) -> dict[str, Any]:
        data = self._legacy_orientation_trim_defaults()
        if isinstance(payload, dict):
            data.update({k: payload[k] for k in payload if k in data})
        return data

    def build_contact_control_profile(self) -> dict[str, Any]:
        return dict(self.contact_control)

    def build_force_estimator_profile(self) -> dict[str, Any]:
        return dict(self.force_estimator)

    def build_orientation_trim_profile(self) -> dict[str, Any]:
        return dict(self.orientation_trim)

    def build_rt_phase_contract(self) -> dict[str, Any]:
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
                "normal_velocity_quiet_threshold_mm_s": self.normal_velocity_quiet_threshold_mm_s,
                "contact_control": self.build_contact_control_profile(),
                "force_estimator": self.build_force_estimator_profile(),
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
                "scan_follow_max_travel_mm": float(self.sweep_policy.get("max_scan_travel_mm", 120.0)),
                "scan_follow_lateral_amplitude_mm": self.scan_follow_lateral_amplitude_mm,
                "scan_follow_frequency_hz": self.scan_follow_frequency_hz,
                "orientation_trim": self.build_orientation_trim_profile(),
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

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["dh_parameters"] = [item.to_dict() for item in self.dh_parameters]
        payload["contact_control"] = self.build_contact_control_profile()
        payload["force_estimator"] = self.build_force_estimator_profile()
        payload["orientation_trim"] = self.build_orientation_trim_profile()
        payload = with_sdk_boundary_fields(
            payload,
            fc_frame_matrix=self.fc_frame_matrix,
            tcp_frame_matrix=self.tcp_frame_matrix,
            load_com_mm=self.load_com_mm,
        )
        payload["sdk_mainline"] = {
            "robot_class": self.sdk_robot_class,
            "realtime_client_language": self.realtime_client_language,
            "preferred_link": self.preferred_link,
            "single_control_source": self.requires_single_control_source,
            "rt_network_tolerance_percent": self.rt_network_tolerance_percent,
        }
        payload["rt_control_contract"] = {
            "fc_frame_type": self.fc_frame_type,
            "cartesian_impedance": list(self.cartesian_impedance),
            "desired_wrench_n": list(self.desired_wrench_n),
            "joint_filter_hz": self.joint_filter_hz,
            "cart_filter_hz": self.cart_filter_hz,
            "torque_filter_hz": self.torque_filter_hz,
            "contact_control": self.build_contact_control_profile(),
            "force_estimator": self.build_force_estimator_profile(),
            "orientation_trim": self.build_orientation_trim_profile(),
        }
        payload["rt_phase_contract"] = self.build_rt_phase_contract()
        payload["legacy_compatibility"] = {
            "flat_field_projection": {
                "normal_admittance_gain": self.normal_admittance_gain,
                "normal_damping_gain": self.normal_damping_gain,
                "scan_normal_pi_kp": self.scan_normal_pi_kp,
                "scan_normal_pi_ki": self.scan_normal_pi_ki,
                "pause_hold_drift_kp": self.pause_hold_drift_kp,
                "pause_hold_drift_ki": self.pause_hold_drift_ki,
                "pause_hold_integrator_leak": self.pause_hold_integrator_leak,
            },
            "warnings": list(self.compatibility_warnings),
        }
        payload["safety_contract"] = {
            "collision_detection_enabled": self.collision_detection_enabled,
            "collision_sensitivity": self.collision_sensitivity,
            "collision_behavior": self.collision_behavior,
            "collision_fallback_mm": self.collision_fallback_mm,
            "soft_limit_enabled": self.soft_limit_enabled,
            "joint_soft_limit_margin_deg": self.joint_soft_limit_margin_deg,
            "singularity_avoidance_enabled": self.singularity_avoidance_enabled,
        }
        payload["clinical_scan_contract"] = {
            "strip_width_mm": self.strip_width_mm,
            "strip_overlap_mm": self.strip_overlap_mm,
            "approach_clearance_mm": self.approach_clearance_mm,
            "contact_guard_margin_mm": self.contact_guard_margin_mm,
            "seek_contact_max_travel_mm": self.seek_contact_max_travel_mm,
            "retract_travel_mm": self.retract_travel_mm,
            "scan_follow_lateral_amplitude_mm": self.scan_follow_lateral_amplitude_mm,
            "scan_follow_frequency_hz": self.scan_follow_frequency_hz,
            "surface_tilt_limits_deg": dict(self.surface_tilt_limits_deg),
            "contact_force_policy": dict(self.contact_force_policy),
            "sweep_policy": dict(self.sweep_policy),
        }
        return payload


def xmate_profile_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "robot.yaml"


def _coerce_list(value: Any, length: int, default: list[float]) -> list[float]:
    if not isinstance(value, list):
        return list(default)
    payload = [float(item) for item in value[:length]]
    if len(payload) < length:
        payload.extend(default[len(payload):length])
    return payload


def _identity_default_profile() -> XMateProfile:
    identity = RobotIdentityService().resolve("xmate3", "xMateRobot", 6)
    return XMateProfile(
        robot_model=identity.robot_model,
        sdk_robot_class=identity.sdk_robot_class,
        controller_series=identity.controller_series,
        controller_version=identity.controller_version,
        axis_count=identity.axis_count,
        preferred_link=identity.preferred_link,
        requires_single_control_source=identity.requires_single_control_source,
        rt_mode=identity.rt_mode,
        supported_rt_modes=list(identity.supported_rt_modes),
        clinical_allowed_modes=list(identity.clinical_allowed_modes),
        cartesian_impedance=[1000.0, 1000.0, 1000.0, 80.0, 80.0, 80.0],
        desired_wrench_n=[0.0, 0.0, 8.0, 0.0, 0.0, 0.0],
        dh_parameters=[DhParameter(item.joint, item.a_mm, item.alpha_rad, item.d_mm, item.theta_rad) for item in identity.official_dh_parameters],
    )


def load_xmate_profile(path: Path | None = None) -> XMateProfile:
    target = path or xmate_profile_path()
    defaults = _identity_default_profile()
    if not target.exists():
        return defaults
    try:
        import yaml  # type: ignore
    except Exception:
        return defaults
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return defaults

    identity_service = RobotIdentityService(defaults.robot_model)
    identity = identity_service.resolve(
        str(raw.get("robot_model", defaults.robot_model)),
        str(raw.get("sdk_robot_class", defaults.sdk_robot_class)),
        int(raw.get("axis_count", defaults.axis_count)),
    )

    dh_payload = raw.get("dh_parameters", [])
    dh_parameters: list[DhParameter] = []
    for item in dh_payload if isinstance(dh_payload, list) else []:
        if not isinstance(item, dict):
            continue
        dh_parameters.append(
            DhParameter(
                joint=int(item.get("joint", len(dh_parameters) + 1)),
                a_mm=float(item.get("a_mm", item.get("a", 0.0))),
                alpha_rad=float(item.get("alpha_rad", item.get("alpha", 0.0))),
                d_mm=float(item.get("d_mm", item.get("d", 0.0))),
                theta_rad=float(item.get("theta_rad", item.get("theta", 0.0))),
            )
        )

    data = defaults.to_dict()
    data.update(raw)
    data.pop("sdk_mainline", None)
    data.pop("rt_control_contract", None)
    data.pop("safety_contract", None)
    data.pop("clinical_scan_contract", None)
    legacy_warnings: list[str] = []
    if "contact_control" not in raw and any(key in raw for key in ("normal_admittance_gain", "normal_damping_gain", "seek_contact_max_step_mm", "pause_hold_integrator_leak")):
        legacy_warnings.append("xmate_profile loaded legacy flat contact-control fields; nested contact_control was synthesized")
    if "force_estimator" not in raw and any(key in raw for key in ("force_estimator_preferred_source", "pressure_stale_ms", "force_estimator_timeout_ms", "force_estimator_min_confidence")):
        legacy_warnings.append("xmate_profile loaded legacy flat force-estimator fields; nested force_estimator was synthesized")
    elif "force_estimator" not in raw and "rt_phase_contract" in raw:
        legacy_warnings.append("xmate_profile loaded force_estimator from legacy rt_phase_contract projection")
    if "orientation_trim" not in raw and any(key in raw for key in ("scan_pose_trim_gain", "rt_max_pose_trim_deg")):
        legacy_warnings.append("xmate_profile loaded legacy flat orientation-trim fields; nested orientation_trim was synthesized")

    data["robot_model"] = identity.robot_model
    data["sdk_robot_class"] = identity.sdk_robot_class
    data["axis_count"] = identity.axis_count
    data["controller_series"] = identity.controller_series
    data["controller_version"] = identity.controller_version
    data["preferred_link"] = identity.preferred_link
    data["rt_mode"] = identity.rt_mode
    data["supported_rt_modes"] = list(identity.supported_rt_modes)
    data["clinical_allowed_modes"] = list(identity.clinical_allowed_modes)
    data["requires_single_control_source"] = bool(identity.requires_single_control_source)
    data["dh_parameters"] = dh_parameters or [DhParameter(item.joint, item.a_mm, item.alpha_rad, item.d_mm, item.theta_rad) for item in identity.official_dh_parameters]
    data["tool_name"] = str(raw.get("tool_name", raw.get("tcp_name", defaults.tool_name)))
    data["pressure_stale_ms"] = int(raw.get("pressure_stale_ms", defaults.pressure_stale_ms))
    data["force_estimator_preferred_source"] = str(raw.get("force_estimator_preferred_source", defaults.force_estimator_preferred_source))
    data["force_estimator_timeout_ms"] = int(raw.get("force_estimator_timeout_ms", defaults.force_estimator_timeout_ms))
    data["force_estimator_min_confidence"] = float(raw.get("force_estimator_min_confidence", defaults.force_estimator_min_confidence))
    data["load_mass_kg"] = float(raw.get("load_mass_kg", raw.get("load_mass", raw.get("load_kg", defaults.load_mass_kg))))
    data["load_com_mm"] = _coerce_list(raw.get("load_com_mm"), 3, defaults.load_com_mm)
    data["load_inertia"] = _coerce_list(raw.get("load_inertia"), 6, defaults.load_inertia)
    data["cartesian_impedance"] = _coerce_list(raw.get("cartesian_impedance"), 6, defaults.cartesian_impedance)
    data["desired_wrench_n"] = _coerce_list(raw.get("desired_wrench_n"), 6, defaults.desired_wrench_n)
    data["fc_frame_matrix"] = _coerce_list(raw.get("fc_frame_matrix"), 16, defaults.fc_frame_matrix)
    data["tcp_frame_matrix"] = _coerce_list(raw.get("tcp_frame_matrix"), 16, defaults.tcp_frame_matrix)
    data["surface_tilt_limits_deg"] = dict(defaults.surface_tilt_limits_deg) | dict(raw.get("surface_tilt_limits_deg", {}))
    data["contact_force_policy"] = dict(defaults.contact_force_policy) | dict(raw.get("contact_force_policy", {}))
    data["sweep_policy"] = dict(defaults.sweep_policy) | dict(raw.get("sweep_policy", {}))

    rt_phase_contract = raw.get("rt_phase_contract", {})
    if isinstance(rt_phase_contract, dict):
        for section in ("common", "seek_contact", "scan_follow", "pause_hold", "controlled_retract"):
            section_payload = rt_phase_contract.get(section, {})
            if isinstance(section_payload, dict):
                data.update(section_payload)
        seek_contact = rt_phase_contract.get("seek_contact", {}) if isinstance(rt_phase_contract.get("seek_contact", {}), dict) else {}
        scan_follow = rt_phase_contract.get("scan_follow", {}) if isinstance(rt_phase_contract.get("scan_follow", {}), dict) else {}
        contact_control = raw.get("contact_control", seek_contact.get("contact_control", {}))
        force_estimator = raw.get("force_estimator", seek_contact.get("force_estimator", {}))
        orientation_trim = raw.get("orientation_trim", scan_follow.get("orientation_trim", {}))
        if isinstance(contact_control, dict):
            data["contact_control"] = contact_control
            data["seek_contact_max_step_mm"] = float(contact_control.get("max_normal_step_mm", data.get("seek_contact_max_step_mm", defaults.seek_contact_max_step_mm)))
            data["seek_contact_max_travel_mm"] = float(contact_control.get("max_normal_travel_mm", data.get("seek_contact_max_travel_mm", defaults.seek_contact_max_travel_mm)))
            data["pause_hold_integrator_leak"] = float(contact_control.get("integrator_leak", data.get("pause_hold_integrator_leak", defaults.pause_hold_integrator_leak)))
        if isinstance(force_estimator, dict):
            data["force_estimator"] = force_estimator
        if isinstance(orientation_trim, dict):
            data["orientation_trim"] = orientation_trim
            data["scan_pose_trim_gain"] = float(orientation_trim.get("gain", data.get("scan_pose_trim_gain", defaults.scan_pose_trim_gain)))
            data["rt_max_pose_trim_deg"] = float(orientation_trim.get("max_trim_deg", data.get("rt_max_pose_trim_deg", defaults.rt_max_pose_trim_deg)))
    else:
        if isinstance(raw.get("contact_control"), dict):
            data["contact_control"] = raw.get("contact_control")
        if isinstance(raw.get("force_estimator"), dict):
            data["force_estimator"] = raw.get("force_estimator")
        if isinstance(raw.get("orientation_trim"), dict):
            data["orientation_trim"] = raw.get("orientation_trim")

    data["compatibility_warnings"] = legacy_warnings
    return XMateProfile(**{k: v for k, v in data.items() if k in XMateProfile.__dataclass_fields__})


def export_xmate_profile(path: Path | None = None) -> dict[str, Any]:
    return load_xmate_profile(path).to_dict()


def build_control_authority_snapshot(*, read_only_mode: bool = False) -> dict[str, Any]:
    profile = load_xmate_profile()
    return {
        "robot_model": profile.robot_model,
        "sdk_robot_class": profile.sdk_robot_class,
        "requires_single_control_source": profile.requires_single_control_source,
        "read_only_mode": read_only_mode,
        "command_authority": "read_only" if read_only_mode else "operator",
        "recommended_operator_source": "sdk_only",
        "preferred_link": profile.preferred_link,
        "rt_network_tolerance_percent": profile.rt_network_tolerance_percent,
    }


def save_profile_json(target: Path, profile: XMateProfile | None = None) -> Path:
    payload = (profile or load_xmate_profile()).to_dict()
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    return target
