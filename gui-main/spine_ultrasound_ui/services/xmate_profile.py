from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


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
    robot_model: str = "xmate_er3"
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
    cartesian_impedance: list[float] = field(default_factory=lambda: [2200.0, 2200.0, 1400.0, 45.0, 45.0, 35.0])
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
    })
    motion_sequence: list[str] = field(default_factory=lambda: [
        "approach_nrt",
        "seek_contact_rt_cartesian_impedance",
        "scan_rt_cartesian_impedance",
        "safe_retreat",
    ])
    dh_parameters: list[DhParameter] = field(default_factory=lambda: [
        DhParameter(1, 0.0, -1.57079632679, 341.5),
        DhParameter(2, 0.0, 1.57079632679, 0.0),
        DhParameter(3, 0.0, -1.57079632679, 394.0),
        DhParameter(4, 0.0, 1.57079632679, 0.0),
        DhParameter(5, 0.0, -1.57079632679, 366.0),
        DhParameter(6, 0.0, 1.57079632679, 0.0),
    ])

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["dh_parameters"] = [item.to_dict() for item in self.dh_parameters]
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
        }
        payload["clinical_scan_contract"] = {
            "strip_width_mm": self.strip_width_mm,
            "strip_overlap_mm": self.strip_overlap_mm,
            "approach_clearance_mm": self.approach_clearance_mm,
            "contact_guard_margin_mm": self.contact_guard_margin_mm,
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


def load_xmate_profile(path: Path | None = None) -> XMateProfile:
    target = path or xmate_profile_path()
    defaults = XMateProfile()
    if not target.exists():
        return defaults
    try:
        import yaml  # type: ignore
    except Exception:
        return defaults
    raw = yaml.safe_load(target.read_text(encoding="utf-8")) or {}
    if not isinstance(raw, dict):
        return defaults
    dh_payload = raw.get("dh_parameters", [])
    dh_parameters = []
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
    data.pop("clinical_scan_contract", None)
    data["dh_parameters"] = dh_parameters or defaults.dh_parameters
    data["tool_name"] = str(raw.get("tool_name", raw.get("tcp_name", defaults.tool_name)))
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
