from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List


@dataclass
class ScanWaypoint:
    x: float
    y: float
    z: float
    rx: float
    ry: float
    rz: float

    def to_dict(self) -> Dict[str, float]:
        return {
            "x": float(self.x),
            "y": float(self.y),
            "z": float(self.z),
            "rx": float(self.rx),
            "ry": float(self.ry),
            "rz": float(self.rz),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanWaypoint":
        return cls(**{key: float(data[key]) for key in ["x", "y", "z", "rx", "ry", "rz"]})


@dataclass
class ScanSegment:
    segment_id: int
    waypoints: List[ScanWaypoint]
    target_pressure: float
    scan_direction: str
    needs_resample: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": int(self.segment_id),
            "waypoints": [point.to_dict() for point in self.waypoints],
            "target_pressure": float(self.target_pressure),
            "scan_direction": self.scan_direction,
            "needs_resample": bool(self.needs_resample),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanSegment":
        return cls(
            segment_id=int(data["segment_id"]),
            waypoints=[ScanWaypoint.from_dict(point) for point in data.get("waypoints", [])],
            target_pressure=float(data.get("target_pressure", 1.5)),
            scan_direction=str(data.get("scan_direction", "caudal_to_cranial")),
            needs_resample=bool(data.get("needs_resample", False)),
        )


@dataclass
class ScanPlan:
    session_id: str
    plan_id: str
    approach_pose: ScanWaypoint
    retreat_pose: ScanWaypoint
    segments: List[ScanSegment] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "plan_id": self.plan_id,
            "approach_pose": self.approach_pose.to_dict(),
            "retreat_pose": self.retreat_pose.to_dict(),
            "segments": [segment.to_dict() for segment in self.segments],
        }

    def plan_hash(self) -> str:
        blob = json.dumps(self.to_dict(), ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def template_hash(self) -> str:
        payload = self.to_dict()
        payload["session_id"] = ""
        payload["plan_id"] = ""
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()

    def with_session(self, session_id: str, plan_id: str | None = None) -> "ScanPlan":
        return ScanPlan(
            session_id=session_id,
            plan_id=plan_id or self.plan_id or f"PLAN_{session_id}",
            approach_pose=self.approach_pose,
            retreat_pose=self.retreat_pose,
            segments=self.segments,
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanPlan":
        return cls(
            session_id=str(data.get("session_id", "")),
            plan_id=str(data.get("plan_id", "")),
            approach_pose=ScanWaypoint.from_dict(dict(data.get("approach_pose", {}))),
            retreat_pose=ScanWaypoint.from_dict(dict(data.get("retreat_pose", {}))),
            segments=[ScanSegment.from_dict(segment) for segment in data.get("segments", [])],
        )


@dataclass
class CoreStateSnapshot:
    execution_state: str
    armed: bool = False
    fault_code: str = ""
    active_segment: int = 0
    progress_pct: float = 0.0
    session_id: str = ""


@dataclass
class SafetyStatus:
    safe_to_arm: bool = False
    safe_to_scan: bool = False
    active_interlocks: List[str] = field(default_factory=list)


@dataclass
class RecorderStatus:
    session_id: str = ""
    recording: bool = False
    dropped_samples: int = 0
    last_flush_ns: int = 0


@dataclass
class SessionManifest:
    experiment_id: str
    session_id: str
    config_snapshot: Dict[str, Any]
    scan_plan_hash: str
    device_roster: Dict[str, Any]
    software_version: str
    build_id: str
    protocol_version: int = 1
    force_sensor_provider: str = "mock_force_sensor"
    safety_thresholds: Dict[str, Any] = field(default_factory=dict)
    device_health_snapshot: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
