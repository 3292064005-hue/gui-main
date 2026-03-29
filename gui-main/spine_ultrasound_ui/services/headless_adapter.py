from __future__ import annotations

import base64
import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any

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
        return protocol_schema()

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
            "status": self.status(),
        }

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
        events: list[dict[str, Any]] = []
        if session_dir is None:
            signature = "no-session"
            session_id = self._current_session_id or ""
            status = {
                "session_id": session_id,
                "signature": signature,
                "changed": self._last_product_signature != signature,
                "changed_topics": [],
            }
            if status["changed"]:
                self._last_product_signature = signature
                self._product_topic_signatures = {}
                events.append({"topic": "session_product_update", "ts_ns": now_ns(), "data": status})
            return events

        watched = {
            "manifest_updated": session_dir / "meta" / "manifest.json",
            "readiness_updated": session_dir / "meta" / "device_readiness.json",
            "profile_updated": session_dir / "meta" / "xmate_profile.json",
            "registration_updated": session_dir / "meta" / "patient_registration.json",
            "report_updated": session_dir / "export" / "session_report.json",
            "compare_updated": session_dir / "export" / "session_compare.json",
            "trends_updated": session_dir / "export" / "session_trends.json",
            "qa_pack_updated": session_dir / "export" / "qa_pack.json",
            "diagnostics_updated": session_dir / "export" / "diagnostics_pack.json",
            "replay_updated": session_dir / "replay" / "replay_index.json",
            "quality_updated": session_dir / "derived" / "quality" / "quality_timeline.json",
            "alarms_updated": session_dir / "derived" / "alarms" / "alarm_timeline.json",
            "frame_sync_updated": session_dir / "derived" / "sync" / "frame_sync_index.json",
            "scan_protocol_updated": session_dir / "derived" / "preview" / "scan_protocol.json",
            "annotations_updated": session_dir / "raw" / "ui" / "annotations.jsonl",
            "command_trace_updated": session_dir / "raw" / "ui" / "command_journal.jsonl",
        }
        changed_topics: list[str] = []
        signature_parts: list[str] = [str(session_dir)]
        for topic, watched_path in watched.items():
            signature = "missing"
            if watched_path.exists():
                stat = watched_path.stat()
                signature = f"{watched_path.name}:{stat.st_mtime_ns}:{stat.st_size}"
                signature_parts.append(signature)
            previous = self._product_topic_signatures.get(topic)
            if previous != signature:
                self._product_topic_signatures[topic] = signature
                if previous is not None:
                    changed_topics.append(topic)
                    events.append({
                        "topic": topic,
                        "ts_ns": now_ns(),
                        "data": {
                            "session_id": self._read_manifest_if_available(session_dir).get("session_id", session_dir.name),
                            "path": str(watched_path),
                        },
                    })
        signature = "|".join(signature_parts)
        if signature != self._last_product_signature:
            self._last_product_signature = signature
            manifest = self._read_manifest_if_available(session_dir)
            if changed_topics:
                changed_topics.append("artifact_ready")
                events.append({
                    "topic": "artifact_ready",
                    "ts_ns": now_ns(),
                    "data": {
                        "session_id": manifest.get("session_id", session_dir.name),
                        "changed_topics": changed_topics,
                    },
                })
            events.append({
                "topic": "session_product_update",
                "ts_ns": now_ns(),
                "data": {
                    "session_id": manifest.get("session_id", session_dir.name),
                    "signature": signature,
                    "changed": True,
                    "changed_topics": changed_topics,
                },
            })
        return events

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

    def _mock_loop(self) -> None:
        assert self.runtime is not None
        while not self._stop.is_set():
            messages = self.runtime.tick()
            self._store_messages(messages)
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
            except OSError:
                if not self._stop.is_set():
                    time.sleep(1.0)
            except Exception:
                if self._stop.is_set():
                    break
                time.sleep(1.0)
