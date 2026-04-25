from __future__ import annotations

import json
from typing import Any

import httpx

from spine_ultrasound_ui.utils import now_ns

from .api_bridge_backend_helpers import remember_backend_error
from .backend_errors import normalize_backend_exception
from .ipc_protocol import ReplyEnvelope


class ApiAuthorityProjectionReader:
    """Own status, health, control-plane, and authoritative-envelope reads."""

    def __init__(self, host: Any) -> None:
        self._host = host

    def health_loop(self) -> None:
        """Continuously refresh read-only authority and control-plane projections.

        Returns:
            None. The loop exits when the host stop event is set.

        Raises:
            No exceptions escape the loop; transport/JSON/runtime errors are
            normalized into link metrics and operator logs.

        Boundary behaviour:
            This reader performs GET-only evidence refreshes and never mutates
            runtime control authority, leases, sessions, or configuration.
        """
        host = self._host
        while not host._stop.is_set():
            try:
                status_resp = host._client.get("/api/v1/status")
                status_resp.raise_for_status()
                health_resp = host._client.get("/api/v1/health")
                health_resp.raise_for_status()
                control_resp = host._client.get("/api/v1/control-plane")
                control_resp.raise_for_status()
                envelope_resp = host._client.get("/api/v1/authoritative-runtime-envelope")
                envelope_resp.raise_for_status()
                status = status_resp.json()
                health = health_resp.json()
                control_plane = control_resp.json()
                authoritative_envelope = host._authoritative_service.normalize_authoritative_runtime_envelope(
                    envelope_resp.json() if envelope_resp.content else {},
                    authority_source="api_bridge",
                    desired_runtime_config=host.config,
                    envelope_origin="api_bridge_health_loop",
                )
                if not authoritative_envelope:
                    authoritative_envelope = host._authoritative_service.build_unavailable_authoritative_runtime_envelope(
                        authority_source="api_bridge",
                        detail="headless API did not return a runtime-published authoritative envelope",
                        desired_runtime_config=host.config,
                        envelope_origin="api_bridge_health_loop_missing_envelope",
                    )
                with host._lock:
                    host._status_cache = status
                    host._health_cache = health
                    host._control_plane_cache = dict(control_plane)
                    host._control_authority_cache = dict(authoritative_envelope.get("control_authority", {}))
                    host._runtime_config_cache = dict(control_plane.get("runtime_config", {}))
                    host._schema_cache = dict(control_plane.get("schema", {}))
                    host._topic_catalog_cache = dict(control_plane.get("topics", {}))
                    host._recent_commands_cache = list(control_plane.get("recent_commands", {}).get("recent_commands", []))
                    host._last_final_verdict = dict(authoritative_envelope.get("final_verdict", {}))
                    host._authoritative_envelope = authoritative_envelope
                    host._metrics.rest_reachable = True
                    host._metrics.last_status_poll_ns = now_ns()
                host._projection_cache.update_partition("status", status)
                host._projection_cache.update_partition("health", health)
                host._projection_cache.update_partition("schema", host._schema_cache)
                host._projection_cache.update_partition("topics", host._topic_catalog_cache)
                host._projection_cache.update_partition("recent_commands", {"recent_commands": host._recent_commands_cache})
                host._projection_cache.update_partition("control_plane", control_plane)
                host._projection_cache.update_partition("control_authority", authoritative_envelope.get("control_authority", {}))
                host._projection_cache.update_partition("authoritative_runtime_envelope", authoritative_envelope)
                if not host._using_websocket:
                    host._telemetry_client.pull_snapshot_once()
            except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
                normalized = normalize_backend_exception(exc, context="health-loop")
                with host._lock:
                    host._metrics.rest_reachable = False
                    host._health_cache = {"adapter_running": False, "telemetry_stale": True}
                remember_backend_error(host._last_errors, f"health: {normalized.error_type}: {normalized.message}")
                host._log("WARN", f"API 健康检查失败：{normalized.error_type}: {normalized.message}")
            host._stop.wait(host.health_poll_interval_s)

    def capture_reply_contracts(self, reply: ReplyEnvelope) -> None:
        """Capture authoritative contract fields from one command reply.

        Args:
            reply: Runtime reply envelope returned by the transport client.

        Returns:
            None.

        Boundary behaviour:
            This method updates only cached read projections. It does not
            translate commands or mutate runtime authority.
        """
        host = self._host
        authoritative_envelope = host._authoritative_service.normalize_authoritative_runtime_envelope(
            reply.data,
            authority_source="api_bridge",
            desired_runtime_config=host.config,
            allow_direct_payload=True,
        )
        verdict = host._authoritative_service.extract_final_verdict(reply.data)
        if not verdict:
            verdict = dict(authoritative_envelope.get("final_verdict", {}))
        if verdict:
            with host._lock:
                host._last_final_verdict = dict(verdict)
        if authoritative_envelope:
            with host._lock:
                host._authoritative_envelope = authoritative_envelope
                host._control_authority_cache = dict(authoritative_envelope.get("control_authority", {}))
            host._projection_cache.update_partition("authoritative_runtime_envelope", authoritative_envelope)
            host._projection_cache.update_partition("control_authority", authoritative_envelope.get("control_authority", {}))
