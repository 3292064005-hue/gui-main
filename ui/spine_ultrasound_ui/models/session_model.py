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
class ExecutionConstraints:
    max_segment_duration_ms: int = 0
    allowed_contact_band: Dict[str, float] = field(default_factory=dict)
    transition_smoothing: str = "standard"
    recovery_checkpoint_policy: str = "segment_boundary"
    probe_spacing_mm: float = 0.0
    probe_depth_mm: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "max_segment_duration_ms": int(self.max_segment_duration_ms),
            "allowed_contact_band": {str(k): float(v) for k, v in dict(self.allowed_contact_band).items()},
            "transition_smoothing": self.transition_smoothing,
            "recovery_checkpoint_policy": self.recovery_checkpoint_policy,
            "probe_spacing_mm": float(self.probe_spacing_mm),
            "probe_depth_mm": float(self.probe_depth_mm),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ExecutionConstraints":
        return cls(
            max_segment_duration_ms=int(data.get("max_segment_duration_ms", 0) or 0),
            allowed_contact_band={str(k): float(v) for k, v in dict(data.get("allowed_contact_band", {})).items()},
            transition_smoothing=str(data.get("transition_smoothing", "standard")),
            recovery_checkpoint_policy=str(data.get("recovery_checkpoint_policy", "segment_boundary")),
            probe_spacing_mm=float(data.get("probe_spacing_mm", 0.0) or 0.0),
            probe_depth_mm=float(data.get("probe_depth_mm", 0.0) or 0.0),
        )


@dataclass
class ScanSegment:
    segment_id: int
    waypoints: List[ScanWaypoint]
    target_pressure: float
    scan_direction: str
    needs_resample: bool = False
    estimated_duration_ms: int = 0
    requires_contact_probe: bool = False
    segment_priority: int = 0
    rescan_origin_segment: int = 0
    quality_target: float = 0.0
    coverage_target: float = 0.0
    segment_hash: str = ""
    contact_band: Dict[str, float] = field(default_factory=dict)
    transition_policy: str = "serpentine"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "segment_id": int(self.segment_id),
            "waypoints": [point.to_dict() for point in self.waypoints],
            "target_pressure": float(self.target_pressure),
            "scan_direction": self.scan_direction,
            "needs_resample": bool(self.needs_resample),
            "estimated_duration_ms": int(self.estimated_duration_ms),
            "requires_contact_probe": bool(self.requires_contact_probe),
            "segment_priority": int(self.segment_priority),
            "rescan_origin_segment": int(self.rescan_origin_segment),
            "quality_target": float(self.quality_target),
            "coverage_target": float(self.coverage_target),
            "segment_hash": self.segment_hash,
            "contact_band": {str(k): float(v) for k, v in dict(self.contact_band).items()},
            "transition_policy": self.transition_policy,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanSegment":
        return cls(
            segment_id=int(data["segment_id"]),
            waypoints=[ScanWaypoint.from_dict(point) for point in data.get("waypoints", [])],
            target_pressure=float(data.get("target_pressure", 1.5)),
            scan_direction=str(data.get("scan_direction", "caudal_to_cranial")),
            needs_resample=bool(data.get("needs_resample", False)),
            estimated_duration_ms=int(data.get("estimated_duration_ms", 0) or 0),
            requires_contact_probe=bool(data.get("requires_contact_probe", False)),
            segment_priority=int(data.get("segment_priority", 0) or 0),
            rescan_origin_segment=int(data.get("rescan_origin_segment", 0) or 0),
            quality_target=float(data.get("quality_target", 0.0) or 0.0),
            coverage_target=float(data.get("coverage_target", 0.0) or 0.0),
            segment_hash=str(data.get("segment_hash", "")),
            contact_band={str(k): float(v) for k, v in dict(data.get("contact_band", {})).items()},
            transition_policy=str(data.get("transition_policy", "serpentine")),
        )


@dataclass
class ScanPlan:
    session_id: str
    plan_id: str
    approach_pose: ScanWaypoint
    retreat_pose: ScanWaypoint
    segments: List[ScanSegment] = field(default_factory=list)
    planner_version: str = "deterministic_planner_v2"
    registration_hash: str = ""
    plan_kind: str = "preview"
    created_ts_ns: int = 0
    validation_summary: Dict[str, Any] = field(default_factory=dict)
    score_summary: Dict[str, Any] = field(default_factory=dict)
    surface_model_hash: str = ""
    execution_constraints: ExecutionConstraints = field(default_factory=ExecutionConstraints)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "session_id": self.session_id,
            "plan_id": self.plan_id,
            "approach_pose": self.approach_pose.to_dict(),
            "retreat_pose": self.retreat_pose.to_dict(),
            "segments": [segment.to_dict() for segment in self.segments],
            "planner_version": self.planner_version,
            "registration_hash": self.registration_hash,
            "plan_kind": self.plan_kind,
            "created_ts_ns": int(self.created_ts_ns),
            "validation_summary": dict(self.validation_summary),
            "score_summary": dict(self.score_summary),
            "surface_model_hash": self.surface_model_hash,
            "execution_constraints": self.execution_constraints.to_dict(),
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
            planner_version=self.planner_version,
            registration_hash=self.registration_hash,
            plan_kind=self.plan_kind,
            created_ts_ns=self.created_ts_ns,
            validation_summary=dict(self.validation_summary),
            score_summary=dict(self.score_summary),
            surface_model_hash=self.surface_model_hash,
            execution_constraints=ExecutionConstraints.from_dict(self.execution_constraints.to_dict()),
        )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScanPlan":
        return cls(
            session_id=str(data.get("session_id", "")),
            plan_id=str(data.get("plan_id", "")),
            approach_pose=ScanWaypoint.from_dict(dict(data.get("approach_pose", {}))),
            retreat_pose=ScanWaypoint.from_dict(dict(data.get("retreat_pose", {}))),
            segments=[ScanSegment.from_dict(segment) for segment in data.get("segments", [])],
            planner_version=str(data.get("planner_version", "deterministic_planner_v2")),
            registration_hash=str(data.get("registration_hash", "")),
            plan_kind=str(data.get("plan_kind", "preview")),
            created_ts_ns=int(data.get("created_ts_ns", 0) or 0),
            validation_summary=dict(data.get("validation_summary", {})),
            score_summary=dict(data.get("score_summary", {})),
            surface_model_hash=str(data.get("surface_model_hash", "")),
            execution_constraints=ExecutionConstraints.from_dict(dict(data.get("execution_constraints", {}))),
        )


@dataclass
class CoreStateSnapshot:
    execution_state: str
    armed: bool = False
    fault_code: str = ""
    active_segment: int = 0
    progress_pct: float = 0.0
    session_id: str = ""
    recovery_state: str = "IDLE"
    plan_hash: str = ""
    contact_stable: bool = False
    contact_stable_since_ns: int = 0
    active_waypoint_index: int = 0
    last_transition: str = ""
    state_reason: str = ""


@dataclass
class SafetyStatus:
    safe_to_arm: bool = False
    safe_to_scan: bool = False
    active_interlocks: List[str] = field(default_factory=list)
    recovery_reason: str = ""
    last_recovery_action: str = ""
    sensor_freshness_ms: int = 0
    pressure_band_state: str = "UNKNOWN"


@dataclass
class RecorderStatus:
    session_id: str = ""
    recording: bool = False
    dropped_samples: int = 0
    last_flush_ns: int = 0


@dataclass
class ArtifactDescriptor:
    artifact_type: str
    path: str
    mime_type: str = "application/json"
    producer: str = "session_service"
    schema: str = ""
    schema_version: str = "1.0"
    artifact_id: str = ""
    ready: bool = True
    size_bytes: int = 0
    checksum: str = ""
    created_at: str = ""
    summary: str = ""
    source_stage: str = ""
    dependencies: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        if not payload["artifact_id"]:
            payload["artifact_id"] = self.path or self.artifact_type
        return payload


@dataclass
class ProcessingStepRecord:
    step_id: str
    plugin_id: str
    plugin_version: str
    input_artifacts: List[str] = field(default_factory=list)
    output_artifacts: List[str] = field(default_factory=list)
    status: str = "completed"
    detail: str = ""
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class SessionManifest:
    experiment_id: str
    session_id: str
    config_snapshot: Dict[str, Any]
    scan_plan_hash: str
    device_roster: Dict[str, Any]
    software_version: str
    build_id: str
    planner_version: str = "deterministic_planner_v2"
    registration_version: str = "camera_backed_registration_v2"
    core_protocol_version: int = 1
    frontend_build_id: str = ""
    environment_snapshot: Dict[str, Any] = field(default_factory=dict)
    force_control_hash: str = ""
    robot_profile_hash: str = ""
    patient_registration_hash: str = ""
    localization_readiness_hash: str = ""
    calibration_bundle_hash: str = ""
    localization_freeze_hash: str = ""
    manual_adjustment_hash: str = ""
    source_frame_set_hash: str = ""
    guidance_version: str = "camera_guidance_v1"
    guidance_mode: str = "guidance_only"
    guidance_source_type: str = ""
    created_at: str = ""
    protocol_version: int = 1
    force_sensor_provider: str = "mock_force_sensor"
    safety_thresholds: Dict[str, Any] = field(default_factory=dict)
    device_health_snapshot: Dict[str, Any] = field(default_factory=dict)
    device_readiness: Dict[str, Any] = field(default_factory=dict)
    robot_profile: Dict[str, Any] = field(default_factory=dict)
    patient_registration: Dict[str, Any] = field(default_factory=dict)
    localization_readiness: Dict[str, Any] = field(default_factory=dict)
    calibration_bundle: Dict[str, Any] = field(default_factory=dict)
    localization_freeze: Dict[str, Any] = field(default_factory=dict)
    manual_adjustment: Dict[str, Any] = field(default_factory=dict)
    source_frame_set: Dict[str, Any] = field(default_factory=dict)
    scan_protocol: Dict[str, Any] = field(default_factory=dict)
    algorithm_registry: Dict[str, Any] = field(default_factory=dict)
    guidance_algorithm_registry: Dict[str, Any] = field(default_factory=dict)
    artifacts: Dict[str, str] = field(default_factory=dict)
    artifact_registry: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    processing_steps: List[Dict[str, Any]] = field(default_factory=list)
    guidance_processing_steps: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    alarms_summary: Dict[str, Any] = field(default_factory=dict)
    control_authority: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
