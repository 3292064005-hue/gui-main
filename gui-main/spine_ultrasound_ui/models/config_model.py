from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Dict


@dataclass
class RuntimeConfig:
    pressure_target: float = 1.5
    pressure_upper: float = 2.0
    pressure_lower: float = 1.0
    scan_speed_mm_s: float = 8.0
    sample_step_mm: float = 0.5
    segment_length_mm: float = 120.0
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
    force_sensor_provider: str = "mock_force_sensor"
    build_id: str = "dev"
    software_version: str = "0.2.0"

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RuntimeConfig":
        payload = dict(data)
        if "scan_speed" in payload and "scan_speed_mm_s" not in payload:
            payload["scan_speed_mm_s"] = payload.pop("scan_speed")
        if "network_tolerance" in payload and "network_stale_ms" not in payload:
            payload["network_stale_ms"] = int(payload.pop("network_tolerance")) * 10
        return cls(**{k: v for k, v in payload.items() if k in cls.__dataclass_fields__})


ConfigModel = RuntimeConfig
