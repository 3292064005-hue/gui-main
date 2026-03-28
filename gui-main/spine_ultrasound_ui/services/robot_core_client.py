from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Optional

from PySide6.QtCore import QObject, Signal

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils import ensure_dir, now_text

from .backend_base import BackendBase
from .core_transport import parse_telemetry_payload, send_tls_command
from .ipc_protocol import ReplyEnvelope, TelemetryEnvelope
from .protobuf_transport import DEFAULT_TLS_SERVER_NAME, create_client_ssl_context, recv_length_prefixed_message


class RobotCoreClientBackend(QObject, BackendBase):
    telemetry_received = Signal(object)
    log_generated = Signal(str, str)

    def __init__(
        self,
        root_dir: Path,
        command_host: str = "127.0.0.1",
        command_port: int = 5656,
        telemetry_host: str = "127.0.0.1",
        telemetry_port: int = 5657,
    ):
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.command_host = command_host
        self.command_port = command_port
        self.telemetry_host = telemetry_host
        self.telemetry_port = telemetry_port
        self.config = RuntimeConfig()
        self._telemetry_thread: Optional[threading.Thread] = None
        self._telemetry_stop = threading.Event()
        self._ssl_context = create_client_ssl_context()

    def start(self) -> None:
        self._start_telemetry_loop()
        self._log(
            "INFO",
            (
                f"RobotCoreClientBackend 已启动，命令通道 {self.command_host}:{self.command_port} "
                f"(TLS/Protobuf)，遥测通道 {self.telemetry_host}:{self.telemetry_port} (TLS/Protobuf)"
            ),
        )

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        self.config = config
        self._log("INFO", "运行时配置已同步到 AppController。")

    def send_command(self, command: str, payload: Optional[dict] = None) -> ReplyEnvelope:
        try:
            reply = send_tls_command(
                self.command_host,
                self.command_port,
                self._ssl_context,
                command,
                payload,
            )
            self._log("INFO", f"{command}: {reply.message or ('OK' if reply.ok else 'FAILED')}")
            return reply
        except Exception as exc:
            self._log("ERROR", f"{command}: {exc}")
            return ReplyEnvelope(ok=False, message=str(exc), data={})

    def close(self) -> None:
        self._telemetry_stop.set()
        thread = self._telemetry_thread
        if thread and thread.is_alive():
            thread.join(timeout=1.5)

    def _start_telemetry_loop(self) -> None:
        if self._telemetry_thread and self._telemetry_thread.is_alive():
            return
        self._telemetry_stop.clear()
        self._telemetry_thread = threading.Thread(target=self._telemetry_loop, daemon=True)
        self._telemetry_thread.start()

    def _telemetry_loop(self) -> None:
        while not self._telemetry_stop.is_set():
            try:
                with socket.create_connection((self.telemetry_host, self.telemetry_port), timeout=1.0) as raw_sock:
                    raw_sock.settimeout(2.0)
                    with self._ssl_context.wrap_socket(raw_sock, server_hostname=DEFAULT_TLS_SERVER_NAME) as tls_sock:
                        self._log("INFO", "已连接 robot_core 遥测通道。")
                        while not self._telemetry_stop.is_set():
                            message_bytes = recv_length_prefixed_message(tls_sock)
                            self.telemetry_received.emit(parse_telemetry_payload(message_bytes))
            except OSError:
                if not self._telemetry_stop.is_set():
                    time.sleep(1.0)
            except Exception as exc:
                if self._telemetry_stop.is_set():
                    break
                self._log("WARN", f"遥测通道异常：{exc}")
                time.sleep(1.0)

    def _log(self, level: str, message: str) -> None:
        try:
            self.log_generated.emit(level, f"[{now_text()}] {message}")
        except RuntimeError:
            pass
