from __future__ import annotations

from threading import Lock
from typing import Any

from spine_ultrasound_ui.services.ipc_protocol import TelemetryEnvelope, protocol_schema
from spine_ultrasound_ui.utils import now_ns

class HeadlessTelemetryCache:
    def __init__(self, shared_lock: Lock | None = None) -> None:
        self._lock = shared_lock or Lock()
        self.latest_by_topic: dict[str, dict[str, Any]] = {}

    def store(self, env: TelemetryEnvelope) -> dict[str, Any]:
        payload = dict(env.data)
        payload["_ts_ns"] = env.ts_ns or now_ns()
        with self._lock:
            self.latest_by_topic[env.topic] = payload
        return payload

    def snapshot(self, topics: set[str] | None = None) -> list[dict[str, Any]]:
        with self._lock:
            return [{"topic": topic, "ts_ns": data.get("_ts_ns", now_ns()), "data": {k: v for k, v in data.items() if k != "_ts_ns"}} for topic, data in self.latest_by_topic.items() if topics is None or topic in topics]

    def status_slice(self) -> dict[str, Any]:
        with self._lock:
            return {
                "core": dict(self.latest_by_topic.get("core_state", {})),
                "robot": dict(self.latest_by_topic.get("robot_state", {})),
                "safety": dict(self.latest_by_topic.get("safety_status", {})),
                "topics": sorted(self.latest_by_topic.keys()),
            }

    def health_slice(self) -> dict[str, Any]:
        with self._lock:
            latest_ts_ns = max((int(data.get("_ts_ns", 0)) for data in self.latest_by_topic.values()), default=0)
            topics = sorted(self.latest_by_topic.keys())
            core = dict(self.latest_by_topic.get("core_state", {}))
            robot = dict(self.latest_by_topic.get("robot_state", {}))
        force_control = protocol_schema()["force_control"]
        latest_age_ms = max(0, int((now_ns() - latest_ts_ns) / 1_000_000)) if latest_ts_ns else None
        stale_threshold_ms = int(force_control.get("stale_telemetry_ms", 250))
        return {"topics": topics, "core": core, "robot": robot, "latest_ts_ns": latest_ts_ns, "latest_telemetry_age_ms": latest_age_ms, "telemetry_stale": latest_age_ms is None or latest_age_ms > stale_threshold_ms, "stale_threshold_ms": stale_threshold_ms}
