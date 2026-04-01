from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.services.core_transport import send_tls_command
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope


class CommandDispatchService:
    """Dispatch commands to the configured runtime transport."""

    def __init__(
        self,
        *,
        mode: str,
        runtime: Any,
        ssl_context: Any,
        command_host: str,
        command_port: int,
        store_runtime_messages: Any,
    ) -> None:
        self._mode = mode
        self._runtime = runtime
        self._ssl_context = ssl_context
        self._command_host = command_host
        self._command_port = command_port
        self._store_runtime_messages = store_runtime_messages

    def dispatch(self, command: str, payload: dict[str, Any]) -> ReplyEnvelope:
        """Dispatch a command through mock or TLS transport."""
        if self._mode == "mock":
            reply = self._runtime.handle_command(command, payload)
            self._store_runtime_messages(self._runtime.telemetry_snapshot())
            return reply
        return send_tls_command(self._command_host, self._command_port, self._ssl_context, command, payload)
