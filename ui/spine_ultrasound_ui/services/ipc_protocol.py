from __future__ import annotations

import json
from copy import deepcopy
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Optional

from .force_control_config import load_force_control_config
from .runtime_command_catalog import COMMANDS, COMMAND_SPECS, is_write_command
from .runtime_command_contracts import export_contract_document
from .runtime_payload_validator import validate_command_payload

PROTOCOL_VERSION = 1

TELEMETRY_TOPIC_SCHEMAS: dict[str, dict[str, Any]] = {
    "core_state": {
        "core_fields": ["execution_state", "armed", "fault_code", "active_segment", "progress_pct", "session_id", "recovery_state", "plan_hash", "contact_stable"],
    },
    "robot_state": {
        "core_fields": [
            "powered",
            "operate_mode",
            "joint_pos",
            "joint_vel",
            "joint_torque",
            "cart_force",
            "tcp_pose",
            "last_event",
            "last_controller_log",
            "runtime_source",
            "pose_source",
            "force_source",
            "pose_available",
            "force_available",
            "pose_authoritative",
            "force_authoritative",
        ],
    },
    "contact_state": {
        "core_fields": ["mode", "confidence", "pressure_current", "recommended_action", "pressure_source", "quality_source", "pressure_available", "quality_available", "authoritative", "contact_stable"],
    },
    "scan_progress": {
        "core_fields": ["active_segment", "path_index", "overall_progress", "frame_id"],
    },
    "device_health": {
        "core_fields": ["devices"],
    },
    "safety_status": {
        "core_fields": ["safe_to_arm", "safe_to_scan", "active_interlocks", "recovery_reason", "last_recovery_action"],
    },
    "recording_status": {
        "core_fields": ["session_id", "recording", "dropped_samples", "last_flush_ns"],
    },
    "alarm_event": {
        "core_fields": [
            "severity",
            "source",
            "message",
            "session_id",
            "segment_id",
            "event_ts_ns",
            "workflow_step",
            "request_id",
            "auto_action",
        ],
    },
    "quality_feedback": {
        "core_fields": ["image_quality", "feature_confidence", "quality_score", "need_resample", "source", "available", "authoritative"],
    },
}

TELEMETRY_TOPICS = set(TELEMETRY_TOPIC_SCHEMAS)

try:
    from . import ipc_messages_pb2
except Exception as exc:  # pragma: no cover - exercised only when protobuf runtime is absent
    ipc_messages_pb2 = None
    _PROTO_IMPORT_ERROR = exc
else:  # pragma: no cover - trivial assignment
    _PROTO_IMPORT_ERROR = None


class ProtocolVersionError(ValueError):
    pass


def _require_proto():
    if ipc_messages_pb2 is None:
        raise RuntimeError(
            "protobuf transport is unavailable. Install the Python 'protobuf' package "
            "from requirements.txt before using the core backend."
        ) from _PROTO_IMPORT_ERROR
    return ipc_messages_pb2


def _loads_object(raw: str) -> Dict[str, Any]:
    if not raw:
        return {}
    value = json.loads(raw)
    if isinstance(value, dict):
        return value
    raise ValueError(f"expected JSON object payload, got {type(value).__name__}")


def ensure_protocol_version(protocol_version: int, message_kind: str) -> None:
    version = int(protocol_version or PROTOCOL_VERSION)
    if version != PROTOCOL_VERSION:
        raise ProtocolVersionError(
            f"{message_kind} protocol_version mismatch: expected {PROTOCOL_VERSION}, got {version}"
        )


def protocol_schema() -> dict[str, Any]:
    return {
        "api_version": "v1",
        "protocol_version": PROTOCOL_VERSION,
        "transport": {
            "command": "TLS 1.3 + length-prefixed Protobuf",
            "telemetry": "TLS 1.3 + length-prefixed Protobuf",
        },
        "compatibility_policy": "v1 is additive-only; fields may be added but not renamed or removed",
        "reply_envelope": {
            "fields": ["ok", "message", "request_id", "data", "protocol_version"],
        },
        "commands": deepcopy(COMMAND_SPECS),
        "command_contracts": export_contract_document(),
        "telemetry_topics": deepcopy(TELEMETRY_TOPIC_SCHEMAS),
        "force_control": load_force_control_config(),
    }


@dataclass
class CommandEnvelope:
    command: str
    payload: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    protocol_version: int = PROTOCOL_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_protobuf(self):
        proto = _require_proto().Command()
        proto.protocol_version = self.protocol_version
        proto.command = self.command
        proto.payload_json = json.dumps(self.payload, ensure_ascii=False, sort_keys=True)
        proto.request_id = self.request_id
        return proto

    @staticmethod
    def from_json(line: str) -> "CommandEnvelope":
        obj = json.loads(line)
        return CommandEnvelope(
            command=str(obj.get("command", "")),
            payload=dict(obj.get("payload", {})),
            request_id=str(obj.get("request_id", "")),
            protocol_version=int(obj.get("protocol_version", PROTOCOL_VERSION)),
        )

    @staticmethod
    def from_protobuf(proto) -> "CommandEnvelope":
        return CommandEnvelope(
            command=str(proto.command),
            payload=_loads_object(getattr(proto, "payload_json", "{}")),
            request_id=str(proto.request_id),
            protocol_version=int(proto.protocol_version or PROTOCOL_VERSION),
        )


@dataclass
class ReplyEnvelope:
    ok: bool
    message: str = ""
    request_id: str = ""
    data: Dict[str, Any] = field(default_factory=dict)
    protocol_version: int = PROTOCOL_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_protobuf(self):
        proto = _require_proto().Reply()
        proto.protocol_version = self.protocol_version
        proto.ok = self.ok
        proto.message = self.message
        proto.request_id = self.request_id
        proto.data_json = json.dumps(self.data, ensure_ascii=False, sort_keys=True)
        return proto

    @staticmethod
    def from_json(line: str) -> "ReplyEnvelope":
        obj = json.loads(line)
        return ReplyEnvelope(
            ok=bool(obj.get("ok", False)),
            message=str(obj.get("message", "")),
            request_id=str(obj.get("request_id", "")),
            data=dict(obj.get("data", {})),
            protocol_version=int(obj.get("protocol_version", PROTOCOL_VERSION)),
        )

    @staticmethod
    def from_protobuf(proto) -> "ReplyEnvelope":
        return ReplyEnvelope(
            ok=bool(proto.ok),
            message=str(proto.message),
            request_id=str(proto.request_id),
            data=_loads_object(getattr(proto, "data_json", "{}")),
            protocol_version=int(proto.protocol_version or PROTOCOL_VERSION),
        )


@dataclass
class TelemetryEnvelope:
    topic: str
    data: Dict[str, Any] = field(default_factory=dict)
    ts_ns: Optional[int] = None
    protocol_version: int = PROTOCOL_VERSION

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    def to_protobuf(self):
        proto = _require_proto().TelemetryEnvelope()
        proto.protocol_version = self.protocol_version
        proto.topic = self.topic
        proto.ts_ns = int(self.ts_ns or 0)
        proto.data_json = json.dumps(self.data, ensure_ascii=False, sort_keys=True)
        return proto

    @staticmethod
    def from_json(line: str) -> "TelemetryEnvelope":
        obj = json.loads(line)
        return TelemetryEnvelope(
            topic=str(obj.get("topic", "unknown")),
            data=dict(obj.get("data", {})),
            ts_ns=obj.get("ts_ns"),
            protocol_version=int(obj.get("protocol_version", PROTOCOL_VERSION)),
        )

    @staticmethod
    def from_protobuf(proto) -> "TelemetryEnvelope":
        return TelemetryEnvelope(
            topic=str(proto.topic),
            data=_loads_object(getattr(proto, "data_json", "{}")),
            ts_ns=int(proto.ts_ns) if getattr(proto, "ts_ns", 0) else None,
            protocol_version=int(proto.protocol_version or PROTOCOL_VERSION),
        )
