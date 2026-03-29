from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import uuid4

from spine_ultrasound_ui.utils import now_ns


@dataclass
class EventEnvelope:
    topic: str
    payload: dict[str, Any]
    ts_ns: int = field(default_factory=now_ns)
    event_id: str = field(default_factory=lambda: uuid4().hex)
    session_id: str = ""
    source: str = "headless_adapter"
    schema_version: str = "event_envelope_v1"
    request_id: str = ""
    correlation_id: str = ""
    causation_id: str = ""
    category: str = "runtime"
    delivery: str = "telemetry"

    def to_message(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "ts_ns": int(self.ts_ns),
            "data": dict(self.payload),
            "event_id": self.event_id,
            "session_id": self.session_id,
            "source": self.source,
            "schema_version": self.schema_version,
            "request_id": self.request_id,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "category": self.category,
            "delivery": self.delivery,
        }

    @classmethod
    def from_any(
        cls,
        item: dict[str, Any] | str,
        payload: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> "EventEnvelope":
        if isinstance(item, dict):
            data_payload = item.get("data", payload or {})
            return cls(
                topic=str(item.get("topic", kwargs.get("topic", ""))),
                payload=dict(data_payload or {}),
                ts_ns=int(item.get("ts_ns", kwargs.get("ts_ns", now_ns()))),
                event_id=str(item.get("event_id", kwargs.get("event_id", uuid4().hex))),
                session_id=str(item.get("session_id", kwargs.get("session_id", ""))),
                source=str(item.get("source", kwargs.get("source", "headless_adapter"))),
                schema_version=str(item.get("schema_version", kwargs.get("schema_version", "event_envelope_v1"))),
                request_id=str(item.get("request_id", kwargs.get("request_id", ""))),
                correlation_id=str(item.get("correlation_id", kwargs.get("correlation_id", ""))),
                causation_id=str(item.get("causation_id", kwargs.get("causation_id", ""))),
                category=str(item.get("category", kwargs.get("category", "runtime"))),
                delivery=str(item.get("delivery", kwargs.get("delivery", "telemetry"))),
            )
        return cls(topic=str(item), payload=dict(payload or {}), **kwargs)
