from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List

from spine_ultrasound_ui.utils.sdk_unit_contract import build_sdk_boundary_contract


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
    image_quality_threshold: float = 0.7
    roi_mode: str = "auto"
    smoothing_factor: float = 0.35
    reconstruction_step: float = 0.5
    feature_threshold: float = 0.6
    rt_mode: str = "cartesianImpedance"
    network_stale_ms: int = 150
    pressure_stale_ms: int = 100
    telemetry_rate_hz: int = 20
    tool_name: str = "ultrasound_probe"
    tcp_name: str = "ultrasound_tcp"
    load_kg: float = 0.85
    remote_ip: str = "192.168.0.160"
    local_ip: str = "192.168.0.100"
    force_sensor_provider: str = "mock_force_sensor"
    robot_model: str = "xmate3"
    axis_count: int = 6
    sdk_robot_class: str = "xMateRobot"
    preferred_link: str = "wired_direct"
    requires_single_control_source: bool = True
    build_id: str = "dev"
    software_version: str = "0.3.0"
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

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["sdk_boundary_units"] = build_sdk_boundary_contract(
            fc_frame_matrix=self.fc_frame_matrix,
            tcp_frame_matrix=self.tcp_frame_matrix,
            load_com_mm=self.load_com_mm,
        )
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
        return cls(**{k: v for k, v in payload.items() if k in cls.__dataclass_fields__})


ConfigModel = RuntimeConfig
