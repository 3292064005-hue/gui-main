from __future__ import annotations

import base64
import json
import os
import socket
import threading
import time
from pathlib import Path
from typing import Any

from PySide6.QtCore import QBuffer, QByteArray, QIODevice
from PySide6.QtGui import QGuiApplication

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


def _ensure_qt_app() -> None:
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    if QGuiApplication.instance() is None:
        QGuiApplication([])


def _pixmap_to_base64(mode: str, phase: float) -> str:
    _ensure_qt_app()
    pixmap = generate_demo_pixmap(720, 360, mode, phase)
    if pixmap.isNull():
        return ""
    byte_array = QByteArray()
    buffer = QBuffer(byte_array)
    buffer.open(QIODevice.WriteOnly)
    pixmap.save(buffer, "PNG")
    return base64.b64encode(bytes(byte_array)).decode("ascii")


class HeadlessAdapter:
    def __init__(self, mode: str, command_host: str, command_port: int, telemetry_host: str, telemetry_port: int):
        self.mode = mode
        self.command_host = command_host
        self.command_port = command_port
        self.telemetry_host = telemetry_host
        self.telemetry_port = telemetry_port
        self.runtime = MockCoreRuntime() if mode == "mock" else None
        self.ssl_context = create_client_ssl_context() if mode == "core" else None
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self.latest_by_topic: dict[str, dict[str, Any]] = {}
        self.phase = 0.0
        self._current_session_dir: Path | None = None
        self._current_session_id = ""
        self._command_journal: JsonlRecorder | None = None

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
        return {
            "backend_mode": self.mode,
            "command_endpoint": f"{self.command_host}:{self.command_port}",
            "telemetry_endpoint": f"{self.telemetry_host}:{self.telemetry_port}",
            "execution_state": core.get("execution_state", "BOOT"),
            "powered": robot.get("powered", False),
            "safe_to_scan": safety.get("safe_to_scan", False),
            "protocol_version": PROTOCOL_VERSION,
            "session_id": core.get("session_id", self._current_session_id),
            "topics": topics,
        }

    def health(self) -> dict[str, Any]:
        with self._lock:
            latest_ts_ns = max((int(data.get("_ts_ns", 0)) for data in self.latest_by_topic.values()), default=0)
            topics = sorted(self.latest_by_topic.keys())
        force_control = protocol_schema()["force_control"]
        latest_age_ms = max(0, int((now_ns() - latest_ts_ns) / 1_000_000)) if latest_ts_ns else None
        stale_threshold_ms = int(force_control.get("stale_telemetry_ms", 250))
        return {
            "backend_mode": self.mode,
            "adapter_running": self._thread is not None and self._thread.is_alive(),
            "protocol_version": PROTOCOL_VERSION,
            "topics": topics,
            "latest_telemetry_age_ms": latest_age_ms,
            "telemetry_stale": latest_age_ms is None or latest_age_ms > stale_threshold_ms,
            "stale_threshold_ms": stale_threshold_ms,
        }

    def snapshot(self, topics: set[str] | None = None) -> list[dict[str, Any]]:
        with self._lock:
            return [
                {"topic": topic, "ts_ns": data.get("_ts_ns", now_ns()), "data": {k: v for k, v in data.items() if k != "_ts_ns"}}
                for topic, data in self.latest_by_topic.items()
                if topics is None or topic in topics
            ]

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
        manifest = self._read_json(session_dir / "meta" / "manifest.json")
        return {
            "session_id": manifest.get("session_id", self._current_session_id),
            "session_dir": str(session_dir),
            "artifacts": manifest.get("artifacts", {}),
            "report_available": (session_dir / "export" / "session_report.json").exists(),
            "replay_available": (session_dir / "replay" / "replay_index.json").exists(),
            "status": self.status(),
        }

    def current_report(self) -> dict[str, Any]:
        session_dir = self._resolve_session_dir()
        if session_dir is None:
            raise FileNotFoundError("no active session")
        return self._read_json(session_dir / "export" / "session_report.json")

    def current_replay(self) -> dict[str, Any]:
        session_dir = self._resolve_session_dir()
        if session_dir is None:
            raise FileNotFoundError("no active session")
        return self._read_json(session_dir / "replay" / "replay_index.json")

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

    def _clear_current_session(self) -> None:
        self._current_session_dir = None
        self._current_session_id = ""
        self._command_journal = None

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(path.name)
        return json.loads(path.read_text(encoding="utf-8"))

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
