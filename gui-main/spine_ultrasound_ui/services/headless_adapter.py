from __future__ import annotations

import base64
import json
import os
import queue
import socket
import threading
import time
from contextlib import suppress
from pathlib import Path
from typing import Any, Iterator

try:
    from PySide6.QtCore import QBuffer, QByteArray, QIODevice
    from PySide6.QtGui import QGuiApplication
except Exception:  # pragma: no cover
    QBuffer = QByteArray = QIODevice = QGuiApplication = None  # type: ignore

from spine_ultrasound_ui.services.core_transport import parse_telemetry_payload, send_tls_command
from spine_ultrasound_ui.core.command_journal import summarize_command_payload
from spine_ultrasound_ui.core.session_recorders import JsonlRecorder
from spine_ultrasound_ui.services.ipc_protocol import (
    COMMANDS,
    PROTOCOL_VERSION,
    ReplyEnvelope,
    TelemetryEnvelope,
    protocol_schema,
    validate_command_payload,
)
from spine_ultrasound_ui.services.mock_core_runtime import MockCoreRuntime
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService
from spine_ultrasound_ui.services.command_state_policy import CommandStatePolicyService
from spine_ultrasound_ui.services.event_bus import EventBus, EventSubscription
from spine_ultrasound_ui.services.role_matrix import RoleMatrix
from spine_ultrasound_ui.services.session_dir_watcher import SessionDirWatcher
from spine_ultrasound_ui.services.topic_registry import TopicRegistry
from spine_ultrasound_ui.services.protobuf_transport import (
    DEFAULT_TLS_SERVER_NAME,
    create_client_ssl_context,
    recv_length_prefixed_message,
)
from spine_ultrasound_ui.utils import generate_demo_pixmap, now_ns

_MINIMAL_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO7Zz7kAAAAASUVORK5CYII="
)


def _ensure_qt_app() -> bool:
    if QGuiApplication is None:
        return False
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if QGuiApplication.instance() is None:
        QGuiApplication([])
    return True


def _pixmap_to_base64(mode: str, phase: float) -> str:
    if generate_demo_pixmap is None or QBuffer is None or QByteArray is None or QIODevice is None:
        return _static_png_base64()
    if not _ensure_qt_app():
        return _static_png_base64()
    pixmap = generate_demo_pixmap(720, 360, mode, phase)
    if pixmap is None or pixmap.isNull():
        return _static_png_base64()
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, "PNG")
    return base64.b64encode(bytes(byte_array)).decode("ascii")


def _static_png_base64() -> str:
    return _MINIMAL_PNG_BASE64



class HeadlessAdapter:
    def __init__(self, mode: str, command_host: str, command_port: int, telemetry_host: str, telemetry_port: int):
        self.mode = mode
        self.command_host = command_host
        self.command_port = command_port
        self.telemetry_host = telemetry_host
        self.telemetry_port = telemetry_port
        self.runtime = MockCoreRuntime() if mode == "mock" else None
        self.ssl_context = create_client_ssl_context() if mode == "core" else None
        self.read_only_mode = os.getenv("SPINE_READ_ONLY_MODE", "0").lower() in {"1", "true", "yes", "on"}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.latest_by_topic: dict[str, dict[str, Any]] = {}
        self.phase = 0.0
        self._current_session_dir: Path | None = None
        self._current_session_id = ""
        self._command_journal: JsonlRecorder | None = None
        self._last_product_signature = ""
        self._product_topic_signatures: dict[str, str] = {}
        self.role_matrix = RoleMatrix()
        self.event_bus = EventBus()
        self.topic_registry = TopicRegistry(self.role_matrix)
        self.command_policy_service = CommandStatePolicyService(self.role_matrix)
        self.session_watcher = SessionDirWatcher()
        self.integrity_service = SessionIntegrityService()
        self.session_intelligence = SessionIntelligenceService()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        target = self._mock_loop if self.mode == "mock" else self._core_loop
        self._thread = threading.Thread(target=target, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.5)
        self.event_bus.close()

    def status(self) -> dict[str, Any]:
        with self._lock:
            core = self.latest_by_topic.get("core_state", {})
            robot = self.latest_by_topic.get("robot_state", {})
            safety = self.latest_by_topic.get("safety_status", {})
            topics = sorted(self.latest_by_topic.keys())
        manifest = self._read_manifest_if_available()
        return {
            "backend_mode": self.mode,
            "command_endpoint": f"{self.command_host}:{self.command_port}",
            "telemetry_endpoint": f"{self.telemetry_host}:{self.telemetry_port}",
            "execution_state": core.get("execution_state", "BOOT"),
            "powered": robot.get("powered", False),
            "safe_to_scan": safety.get("safe_to_scan", False),
            "protocol_version": PROTOCOL_VERSION,
            "session_id": core.get("session_id", self._current_session_id),
            "session_locked": bool(self._resolve_session_dir()),
            "force_sensor_provider": manifest.get("force_sensor_provider", ""),
            "robot_model": manifest.get("robot_profile", {}).get("robot_model", ""),
            "software_version": manifest.get("software_version", ""),
            "build_id": manifest.get("build_id", ""),
            "topics": topics,
            "read_only_mode": self.read_only_mode,
        }

    def health(self) -> dict[str, Any]:
        with self._lock:
            latest_ts_ns = max((int(data.get("_ts_ns", 0)) for data in self.latest_by_topic.values()), default=0)
            topics = sorted(self.latest_by_topic.keys())
            core = dict(self.latest_by_topic.get("core_state", {}))
            robot = dict(self.latest_by_topic.get("robot_state", {}))
        force_control = protocol_schema()["force_control"]
        latest_age_ms = max(0, int((now_ns() - latest_ts_ns) / 1_000_000)) if latest_ts_ns else None
        stale_threshold_ms = int(force_control.get("stale_telemetry_ms", 250))
        manifest = self._read_manifest_if_available()
        return {
            "backend_mode": self.mode,
            "adapter_running": self._thread is not None and self._thread.is_alive(),
            "protocol_version": PROTOCOL_VERSION,
            "topics": topics,
            "latest_telemetry_age_ms": latest_age_ms,
            "telemetry_stale": latest_age_ms is None or latest_age_ms > stale_threshold_ms,
            "stale_threshold_ms": stale_threshold_ms,
            "recovery_state": self._derive_recovery_state(core),
            "force_sensor_provider": manifest.get("force_sensor_provider", ""),
            "robot_model": manifest.get("robot_profile", {}).get("robot_model", ""),
            "session_locked": bool(self._resolve_session_dir()),
            "build_id": manifest.get("build_id", ""),
            "software_version": manifest.get("software_version", ""),
            "execution_state": core.get("execution_state", "BOOT"),
            "powered": robot.get("powered", False),
            "read_only_mode": self.read_only_mode,
        }

    def snapshot(self, topics: set[str] | None = None) -> list[dict[str, Any]]:
        with self._lock:
            payloads = [
                {"topic": topic, "ts_ns": data.get("_ts_ns", now_ns()), "data": {k: v for k, v in data.items() if k != "_ts_ns"}}
                for topic, data in self.latest_by_topic.items()
                if topics is None or topic in topics
            ]
        for product_update in self._session_product_update_envelopes():
            if topics is None or product_update["topic"] in topics:
                payloads.append(product_update)
        return payloads

    def schema(self) -> dict[str, Any]:
        payload = protocol_schema()
        payload["topic_catalog"] = self.topic_catalog()
        return payload

    def topic_catalog(self) -> dict[str, Any]:
        return self.topic_registry.catalog()

    def role_catalog(self) -> dict[str, Any]:
        return self.role_matrix.catalog()

    def command_policy_catalog(self) -> dict[str, Any]:
        return self.command_policy_service.catalog()

    def command(self, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if command not in COMMANDS:
            raise ValueError(f"unsupported command: {command}")
        payload = payload or {}
        validate_command_payload(command, payload)
        self._prepare_session_tracking(command, payload)
        if self.mode == "mock":
            assert self.runtime is not None
            reply = self.runtime.handle_command(command, payload)
            self._store_messages(self.runtime.telemetry_snapshot())
        else:
            assert self.ssl_context is not None
            reply = send_tls_command(
                self.command_host,
                self.command_port,
                self.ssl_context,
                command,
                payload,
            )
        if not reply.ok and command == "lock_session":
            self._clear_current_session()
        if command == "disconnect_robot" and reply.ok:
            self._clear_current_session()
        self._record_command_journal(command, payload, reply)
        return self._reply_dict(reply)

    def current_session(self) -> dict[str, Any]:
        session_dir = self._resolve_session_dir()
        if session_dir is None:
            raise FileNotFoundError("no active session")
        manifest = self._read_manifest_if_available(session_dir)
        report_path = session_dir / "export" / "session_report.json"
        replay_path = session_dir / "replay" / "replay_index.json"
        qa_path = session_dir / "export" / "qa_pack.json"
        compare_path = session_dir / "export" / "session_compare.json"
        trends_path = session_dir / "export" / "session_trends.json"
        diagnostics_path = session_dir / "export" / "diagnostics_pack.json"
        return {
            "session_id": manifest.get("session_id", self._current_session_id or session_dir.name),
            "session_dir": str(session_dir),
            "session_started_at": manifest.get("created_at", ""),
            "artifacts": manifest.get("artifacts", {}),
            "artifact_registry": manifest.get("artifact_registry", {}),
            "report_available": report_path.exists(),
            "replay_available": replay_path.exists(),
            "qa_pack_available": qa_path.exists(),
            "compare_available": compare_path.exists(),
            "trends_available": trends_path.exists(),
            "diagnostics_available": diagnostics_path.exists(),
            "readiness_available": (session_dir / "meta" / "device_readiness.json").exists(),
            "profile_available": (session_dir / "meta" / "xmate_profile.json").exists(),
            "patient_registration_available": (session_dir / "meta" / "patient_registration.json").exists(),
            "scan_protocol_available": (session_dir / "derived" / "preview" / "scan_protocol.json").exists(),
            "frame_sync_available": (session_dir / "derived" / "sync" / "frame_sync_index.json").exists(),
            "command_trace_available": (session_dir / "raw" / "ui" / "command_journal.jsonl").exists(),
            "assessment_available": report_path.exists() and (session_dir / "derived" / "sync" / "frame_sync_index.json").exists(),
            "contact_available": True,
            "recovery_available": True,
            "integrity_available": (session_dir / "meta" / "manifest.json").exists(),
            "operator_incidents_available": (session_dir / "derived" / "alarms" / "alarm_timeline.json").exists() or (session_dir / "raw" / "ui" / "annotations.jsonl").exists(),
            "event_log_index_available": (session_dir / "derived" / "events" / "event_log_index.json").exists(),
            "recovery_timeline_available": (session_dir / "derived" / "recovery" / "recovery_decision_timeline.json").exists(),
            "resume_attempts_available": (session_dir / "derived" / "session" / "resume_attempts.json").exists(),
            "resume_outcomes_available": (session_dir / "derived" / "session" / "resume_attempt_outcomes.json").exists(),
            "command_policy_available": (session_dir / "derived" / "session" / "command_state_policy.json").exists(),
            "command_policy_snapshot_available": (session_dir / "derived" / "session" / "command_policy_snapshot.json").exists(),
            "contract_kernel_diff_available": (session_dir / "derived" / "session" / "contract_kernel_diff.json").exists(),
            "contract_consistency_available": (session_dir / "derived" / "session" / "contract_consistency.json").exists(),
            "event_delivery_summary_available": (session_dir / "derived" / "events" / "event_delivery_summary.json").exists(),
            "selected_execution_rationale_available": (session_dir / "derived" / "planning" / "selected_execution_rationale.json").exists(),
            "release_evidence_available": (session_dir / "export" / "release_evidence_pack.json").exists(),
            "release_gate_available": (session_dir / "export" / "release_gate_decision.json").exists(),
            "status": self.status(),
        }

    def current_contact(self) -> dict[str, Any]:
        with self._lock:
            core = dict(self.latest_by_topic.get("core_state", {}))
            contact = dict(self.latest_by_topic.get("contact_state", {}))
            progress = dict(self.latest_by_topic.get("scan_progress", {}))
        return {
            "session_id": str(core.get("session_id", self._current_session_id)),
            "execution_state": str(core.get("execution_state", "BOOT")),
            "contact_mode": str(contact.get("mode", "NO_CONTACT")),
            "contact_confidence": float(contact.get("confidence", 0.0) or 0.0),
            "pressure_current": float(contact.get("pressure_current", 0.0) or 0.0),
            "recommended_action": str(contact.get("recommended_action", "IDLE")),
            "contact_stable": bool(contact.get("contact_stable", core.get("contact_stable", False))),
            "active_segment": int(progress.get("active_segment", core.get("active_segment", 0)) or 0),
        }

    def current_recovery(self) -> dict[str, Any]:
        with self._lock:
            core = dict(self.latest_by_topic.get("core_state", {}))
            safety = dict(self.latest_by_topic.get("safety_status", {}))
        return {
            "session_id": str(core.get("session_id", self._current_session_id)),
            "execution_state": str(core.get("execution_state", "BOOT")),
            "recovery_state": str(core.get("recovery_state", self._derive_recovery_state(core))),
            "recovery_reason": str(safety.get("recovery_reason", "")),
            "last_recovery_action": str(safety.get("last_recovery_action", "")),
            "active_interlocks": list(safety.get("active_interlocks", [])),
        }

    def current_integrity(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self.integrity_service.build(session_dir)

    def current_lineage(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "meta" / "lineage.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["lineage"]

    def current_resume_state(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "meta" / "resume_state.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["resume_state"]

    def current_recovery_report(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "export" / "recovery_report.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["recovery_report"]

    def current_operator_incidents(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "export" / "operator_incident_report.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["operator_incident_report"]

    def current_incidents(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "derived" / "incidents" / "session_incidents.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["session_incidents"]

    def current_resume_decision(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "meta" / "resume_decision.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["resume_decision"]

    def current_event_log_index(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "derived" / "events" / "event_log_index.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["event_log_index"]

    def current_recovery_timeline(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "derived" / "recovery" / "recovery_decision_timeline.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["recovery_decision_timeline"]

    def current_resume_attempts(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "derived" / "session" / "resume_attempts.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["resume_attempts"]

    def current_resume_outcomes(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "derived" / "session" / "resume_attempt_outcomes.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["resume_attempt_outcomes"]

    def current_command_policy(self) -> dict[str, Any]:
        session_dir = self._resolve_session_dir()
        if session_dir is not None:
            path = session_dir / "derived" / "session" / "command_state_policy.json"
            if path.exists():
                return self._read_json(path)
        return self.command_policy_service.catalog()

    def current_contract_kernel_diff(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / 'derived' / 'session' / 'contract_kernel_diff.json'
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)['contract_kernel_diff']

    def current_command_policy_snapshot(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / 'derived' / 'session' / 'command_policy_snapshot.json'
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)['command_policy_snapshot']

    def current_event_delivery_summary(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "derived" / "events" / "event_delivery_summary.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["event_delivery_summary"]

    def current_contract_consistency(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "derived" / "session" / "contract_consistency.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["contract_consistency"]


    def current_selected_execution_rationale(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / 'derived' / 'planning' / 'selected_execution_rationale.json'
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)['selected_execution_rationale']

    def current_release_gate_decision(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / 'export' / 'release_gate_decision.json'
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)['release_gate_decision']

    def current_release_evidence(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        path = session_dir / "export" / "release_evidence_pack.json"
        if path.exists():
            return self._read_json(path)
        return self.session_intelligence.build_all(session_dir)["release_evidence_pack"]

    def replay_events(
        self,
        *,
        topics: set[str] | None = None,
        session_id: str | None = None,
        since_ts_ns: int | None = None,
        until_ts_ns: int | None = None,
        delivery: str | None = None,
        category: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        resolved_page_size = max(1, int(page_size or limit or 100))
        payload = self.event_bus.replay_page(
            topics,
            page_size=resolved_page_size,
            session_id=session_id,
            since_ts_ns=since_ts_ns,
            until_ts_ns=until_ts_ns,
            delivery=delivery,
            category=category,
            cursor=cursor,
        )
        payload["session_id"] = session_id or self._current_session_id
        return payload

    def event_bus_stats(self) -> dict[str, Any]:
        return self.event_bus.stats()

    def event_dead_letters(self) -> dict[str, Any]:
        return self.event_bus.dead_letters()

    def event_delivery_audit(self) -> dict[str, Any]:
        return self.event_bus.delivery_audit()

    def current_report(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "export" / "session_report.json")

    def current_replay(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "replay" / "replay_index.json")

    def current_quality(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "derived" / "quality" / "quality_timeline.json")

    def current_frame_sync(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "derived" / "sync" / "frame_sync_index.json")

    def current_alarms(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "derived" / "alarms" / "alarm_timeline.json")

    def current_artifacts(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        manifest = self._read_manifest_if_available(session_dir)
        return {
            "session_id": manifest.get("session_id", session_dir.name),
            "artifacts": manifest.get("artifacts", {}),
            "artifact_registry": manifest.get("artifact_registry", {}),
            "processing_steps": manifest.get("processing_steps", []),
            "algorithm_registry": manifest.get("algorithm_registry", {}),
            "warnings": manifest.get("warnings", []),
        }

    def current_compare(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "export" / "session_compare.json")

    def current_qa_pack(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "export" / "qa_pack.json")

    def current_trends(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "export" / "session_trends.json")

    def current_diagnostics(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "export" / "diagnostics_pack.json")

    def current_annotations(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return {
            "session_id": self._read_manifest_if_available(session_dir).get("session_id", session_dir.name),
            "annotations": [entry.get("data", {}) for entry in self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")],
        }

    def current_readiness(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "meta" / "device_readiness.json")

    def current_profile(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "meta" / "xmate_profile.json")

    def current_patient_registration(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "meta" / "patient_registration.json")

    def current_scan_protocol(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        return self._read_json(session_dir / "derived" / "preview" / "scan_protocol.json")

    def current_command_trace(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        manifest = self._read_manifest_if_available(session_dir)
        rows = [entry.get("data", {}) for entry in self._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl")]
        return {
            "session_id": manifest.get("session_id", session_dir.name),
            "entries": rows,
            "summary": {
                "count": len(rows),
                "failed": sum(1 for row in rows if not bool(dict(row.get("reply", {})).get("ok", True))),
                "latest_command": rows[-1].get("command", "") if rows else "",
            },
        }

    def current_assessment(self) -> dict[str, Any]:
        session_dir = self._require_session_dir()
        manifest = self._read_manifest_if_available(session_dir)
        report = self._read_json(session_dir / "export" / "session_report.json")
        qa_pack = self._read_json_if_exists(session_dir / "export" / "qa_pack.json")
        frame_sync = self._read_json_if_exists(session_dir / "derived" / "sync" / "frame_sync_index.json")
        annotations = [entry.get("data", {}) for entry in self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")]
        quality_summary = dict(report.get("quality_summary", {}))
        usable_ratio = float(quality_summary.get("usable_sync_ratio", frame_sync.get("summary", {}).get("usable_ratio", 0.0) or 0.0))
        avg_quality = float(quality_summary.get("avg_quality_score", 0.0) or 0.0)
        confidence = round(min(1.0, max(0.0, (avg_quality * 0.65) + (usable_ratio * 0.35))), 4)
        manual_review = confidence < 0.82 or len(annotations) > 0
        evidence_frames: list[dict[str, Any]] = []
        for row in frame_sync.get("rows", []):
            if not bool(row.get("usable", True)):
                continue
            evidence_frames.append({
                "frame_id": row.get("frame_id", row.get("seq", len(evidence_frames))),
                "segment_id": row.get("segment_id", 0),
                "ts_ns": row.get("ts_ns", 0),
                "quality_score": row.get("quality_score", row.get("image_quality", 0.0)),
                "contact_confidence": row.get("contact_confidence", 0.0),
            })
            if len(evidence_frames) >= 8:
                break
        landmark_candidates = [
            annotation
            for annotation in annotations
            if str(annotation.get("kind", "")).lower() in {"landmark_hint", "anatomy_marker", "manual_review_note"}
        ][:10]
        open_issues = list(report.get("open_issues", []))
        return {
            "session_id": manifest.get("session_id", session_dir.name),
            "robot_model": manifest.get("robot_profile", {}).get("robot_model", ""),
            "summary": {
                "avg_quality_score": avg_quality,
                "usable_sync_ratio": usable_ratio,
                "annotation_count": len(annotations),
                "confidence": confidence,
            },
            "curve_candidate": {
                "status": "plugin_ready",
                "source": "session_report",
                "description": "Clinical scoliosis assessment remains plugin-driven; current workspace exposes evidence and review anchors.",
            },
            "cobb_candidate_deg": qa_pack.get("assessment", {}).get("cobb_candidate_deg") if isinstance(qa_pack.get("assessment"), dict) else None,
            "confidence": confidence,
            "requires_manual_review": manual_review,
            "landmark_candidates": landmark_candidates,
            "evidence_frames": evidence_frames,
            "open_issues": open_issues,
        }

    def _session_product_update_envelopes(self) -> list[dict[str, Any]]:
        session_dir = self._resolve_session_dir()
        return self.session_watcher.poll(session_dir, session_id=self._read_manifest_if_available(session_dir).get("session_id", self._current_session_id or (session_dir.name if session_dir else "")))

    def subscribe(
        self,
        topics: set[str] | None = None,
        *,
        include_snapshot: bool = True,
        categories: set[str] | None = None,
        deliveries: set[str] | None = None,
    ) -> EventSubscription:
        subscription = self.event_bus.subscribe(topics, categories=categories, deliveries=deliveries, subscriber_name="websocket_feed")
        if include_snapshot:
            for item in self.snapshot(topics):
                subscription.push(item)
        return subscription

    def unsubscribe(self, subscription: EventSubscription) -> None:
        self.event_bus.unsubscribe(subscription)

    def iter_events(self, topics: set[str] | None = None) -> Iterator[dict[str, Any]]:
        subscription = self.subscribe(topics)
        try:
            while not self._stop.is_set() and not subscription.closed:
                item = subscription.get(timeout=1.0)
                if item is None:
                    break
                yield item
        finally:
            self.unsubscribe(subscription)

    def _publish_event(self, item: dict[str, Any]) -> None:
        topic = str(item.get("topic", ""))
        category = "session" if topic.endswith("_updated") or topic in {"artifact_ready", "session_product_update"} else str(item.get("category", "runtime"))
        delivery = "event" if category == "session" else str(item.get("delivery", "telemetry"))
        self.topic_registry.ensure(topic, category=category, delivery=delivery)
        self.event_bus.publish(item, category=category, delivery=delivery)

    def camera_frame(self) -> str:
        self.phase += 0.1
        return _pixmap_to_base64("camera", self.phase)

    def ultrasound_frame(self) -> str:
        self.phase += 0.1
        return _pixmap_to_base64("ultrasound", self.phase)

    def _reply_dict(self, reply: ReplyEnvelope) -> dict[str, Any]:
        return {
            "ok": reply.ok,
            "message": reply.message,
            "request_id": reply.request_id,
            "data": dict(reply.data),
            "protocol_version": reply.protocol_version,
        }

    def _store_message(self, env: TelemetryEnvelope) -> None:
        payload = dict(env.data)
        payload["_ts_ns"] = env.ts_ns or now_ns()
        with self._lock:
            self.latest_by_topic[env.topic] = payload
        self.topic_registry.ensure(env.topic, category="runtime", delivery="telemetry")
        self.event_bus.publish(env.topic, {k: v for k, v in payload.items() if k != "_ts_ns"}, ts_ns=payload["_ts_ns"], session_id=str(payload.get("session_id", self._current_session_id)), category="runtime", delivery="telemetry", source="robot_core" if self.mode == "core" else "mock_core")

    def _store_messages(self, messages: list[TelemetryEnvelope]) -> None:
        for env in messages:
            self._store_message(env)

    def _prepare_session_tracking(self, command: str, payload: dict[str, Any]) -> None:
        if command != "lock_session":
            return
        session_dir = payload.get("session_dir")
        session_id = payload.get("session_id", "")
        if not isinstance(session_dir, str) or not session_dir:
            return
        self._current_session_dir = Path(session_dir)
        self._current_session_id = str(session_id)
        self._command_journal = JsonlRecorder(self._current_session_dir / "raw" / "ui" / "command_journal.jsonl", self._current_session_id or "headless")

    def _record_command_journal(self, command: str, payload: dict[str, Any], reply: ReplyEnvelope) -> None:
        if self._command_journal is None:
            return
        self._command_journal.append_event(
            {
                "ts_ns": now_ns(),
                "source": "headless",
                "command": command,
                "workflow_step": command,
                "auto_action": "",
                "payload_summary": summarize_command_payload(payload),
                "reply": {
                    "ok": reply.ok,
                    "message": reply.message,
                    "request_id": reply.request_id,
                    "data": dict(reply.data),
                },
            }
        )

    def _resolve_session_dir(self) -> Path | None:
        if self._current_session_dir is not None:
            return self._current_session_dir
        if self.runtime is not None and self.runtime.session_dir is not None:
            return self.runtime.session_dir
        return None

    def _require_session_dir(self) -> Path:
        session_dir = self._resolve_session_dir()
        if session_dir is None:
            raise FileNotFoundError("no active session")
        return session_dir

    def _clear_current_session(self) -> None:
        self._current_session_dir = None
        self._current_session_id = ""
        self._command_journal = None

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(path.name)
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _read_json_if_exists(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def _read_manifest_if_available(self, session_dir: Path | None = None) -> dict[str, Any]:
        session_dir = session_dir or self._resolve_session_dir()
        if session_dir is None:
            return {}
        manifest_path = session_dir / "meta" / "manifest.json"
        if manifest_path.exists():
            try:
                return json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {
            "session_id": self._current_session_id or session_dir.name,
            "artifacts": {},
            "artifact_registry": {},
            "processing_steps": [],
        }

    @staticmethod
    def _derive_recovery_state(core: dict[str, Any]) -> str:
        execution_state = str(core.get("execution_state", "BOOT"))
        if execution_state == "ESTOP":
            return "ESTOP_LATCHED"
        if execution_state == "FAULT":
            return "CONTROLLED_RETRACT"
        if execution_state == "PAUSED_HOLD":
            return "HOLDING"
        if execution_state in {"RETREATING", "SCAN_COMPLETE"}:
            return "RETRY_READY"
        return "IDLE"

    def _publish_session_product_updates(self) -> None:
        for event in self._session_product_update_envelopes():
            self._publish_event(event)

    def _mock_loop(self) -> None:
        assert self.runtime is not None
        while not self._stop.is_set():
            messages = self.runtime.tick()
            self._store_messages(messages)
            self._publish_session_product_updates()
            time.sleep(0.1)

    def _core_loop(self) -> None:
        while not self._stop.is_set():
            try:
                with socket.create_connection((self.telemetry_host, self.telemetry_port), timeout=1.0) as raw_sock:
                    raw_sock.settimeout(2.0)
                    assert self.ssl_context is not None
                    with self.ssl_context.wrap_socket(raw_sock, server_hostname=DEFAULT_TLS_SERVER_NAME) as tls_sock:
                        while not self._stop.is_set():
                            message_bytes = recv_length_prefixed_message(tls_sock)
                            self._store_message(parse_telemetry_payload(message_bytes))
                            self._publish_session_product_updates()
            except OSError:
                if not self._stop.is_set():
                    time.sleep(1.0)
            except Exception:
                if self._stop.is_set():
                    break
                time.sleep(1.0)
