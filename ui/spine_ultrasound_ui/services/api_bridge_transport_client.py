from __future__ import annotations

import json
from typing import Any, Optional

import httpx

from spine_ultrasound_ui.utils import now_ns

from .api_bridge_backend_helpers import build_command_headers, remember_backend_error
from .backend_command_error_service import BackendCommandErrorService
from .backend_errors import normalize_backend_exception
from .ipc_protocol import ReplyEnvelope


class ApiBridgeTransportClient:
    """Own the API bridge HTTP transport and command-reply normalization."""

    def __init__(self, host: Any) -> None:
        self._host = host

    def send_command(self, command: str, payload: Optional[dict] = None, *, context: Optional[dict] = None) -> ReplyEnvelope:
        """Send one command through the read-only HTTP surface.

        Args:
            command: Canonical runtime command name.
            payload: Optional command payload.
            context: Optional provenance fields used only for diagnostics.

        Returns:
            Normalized reply envelope.

        Raises:
            No transport exceptions escape; failures are converted into
            ``ReplyEnvelope`` instances with typed error metadata.

        Boundary behaviour:
            The headless HTTP API is permanently read-only. Lease headers are
            always suppressed and the method does not acquire, renew, or release
            runtime control authority.
        """
        host = self._host
        request_payload = dict(payload or {})
        command_context = dict(context or {})
        include_lease = bool(command_context.get("include_lease", True))
        effective_include_lease = False
        started_ns = now_ns()
        with host._lock:
            host._metrics.commands_sent += 1
            host._metrics.last_command = command
        if include_lease and not effective_include_lease:
            host._log("INFO", "headless HTTP API is read-only; lease headers suppressed for this command.")
        try:
            response = host._client.post(
                f"/api/v1/commands/{command}",
                json=request_payload,
                headers=build_command_headers(
                    intent=str(command_context.get("intent_reason") or command),
                    actor_id=str(command_context.get("actor_id") or host._actor_id),
                    workspace=str(command_context.get("workspace") or host._workspace),
                    role=str(command_context.get("role") or host._role),
                    session_id=str(command_context.get("session_id") or ""),
                    lease_id=host._lease_id,
                    include_lease=effective_include_lease,
                ),
            )
            latency_ms = int((now_ns() - started_ns) / 1_000_000)
            with host._lock:
                host._metrics.last_command_latency_ms = latency_ms
            body = response.json() if response.content else {}
            if response.status_code >= 400:
                detail = body.get("detail") if isinstance(body, dict) else None
                message = str(detail or f"HTTP {response.status_code}")
                with host._lock:
                    host._metrics.commands_failed += 1
                    host._metrics.last_error = message
                remember_backend_error(host._last_errors, f"{command}: {message}")
                host._log("WARN", f"API {command}: {message}")
                _, failed = BackendCommandErrorService.build_reply(
                    RuntimeError(message),
                    command=command,
                    context="api-command",
                    data={"http_status": response.status_code, "command": command},
                )
                return failed
            reply = ReplyEnvelope(
                ok=bool(body.get("ok", False)),
                message=str(body.get("message", "")),
                request_id=str(body.get("request_id", "")),
                data=dict(body.get("data", {})),
                protocol_version=int(body.get("protocol_version", 1)),
            )
            host._authority_reader.capture_reply_contracts(reply)
            if not reply.ok:
                with host._lock:
                    host._metrics.commands_failed += 1
                    host._metrics.last_error = reply.message
                if include_lease and ("控制权" in reply.message or "lease" in reply.message.lower()):
                    host._log("WARN", "runtime reported lease/control-authority issue; API bridge remains read-only and will not auto-mutate lease state.")
                remember_backend_error(host._last_errors, f"{command}: {reply.message}")
            host._log("INFO" if reply.ok else "WARN", f"API {command}: {reply.message or ('OK' if reply.ok else 'FAILED')}")
            return reply
        except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
            normalized, failed = BackendCommandErrorService.build_reply(exc, command=command, context="api-command", data={"command": command})
            with host._lock:
                host._metrics.commands_failed += 1
                host._metrics.last_error = normalized.message
            remember_backend_error(host._last_errors, f"{command}: {normalized.error_type}: {normalized.message}")
            host._log("ERROR", f"API {command} 失败：{normalized.error_type}: {normalized.message}")
            return failed

    def push_runtime_config(self) -> None:
        """Refresh applied runtime configuration through the read-only API.

        The method issues only a GET request and updates local projection caches.
        Runtime configuration mutation through the API bridge is not allowed.
        """
        host = self._host
        try:
            response = host._client.get("/api/v1/runtime-config")
            response.raise_for_status()
            body = response.json() if response.content else {}
            with host._lock:
                host._runtime_config_cache = dict(body)
            host._projection_cache.update_partition("runtime_config", body)
            host._projection_cache.update_partition("desired_runtime_config", host.config.to_dict())
            host._log("INFO", "headless API 为只读证据面；已刷新运行配置快照，未发起任何写入。")
        except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
            normalized = normalize_backend_exception(exc, context="runtime-config")
            remember_backend_error(host._last_errors, f"runtime-config: {normalized.error_type}: {normalized.message}")
            host._log("WARN", f"运行配置快照刷新失败：{normalized.error_type}: {normalized.message}")

    def close(self) -> None:
        """Close the owned HTTP client without touching runtime authority state."""
        self._host._client.close()
