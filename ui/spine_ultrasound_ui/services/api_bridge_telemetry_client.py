from __future__ import annotations

import json
from typing import Any

import httpx

from spine_ultrasound_ui.utils import now_ns

from .api_bridge_backend_helpers import remember_backend_error
from .backend_errors import normalize_backend_exception
from .ipc_protocol import TelemetryEnvelope

try:  # pragma: no cover
    from websockets.sync.client import connect as ws_connect
    from websockets.exceptions import WebSocketException
except ImportError:  # pragma: no cover
    ws_connect = None  # type: ignore
    WebSocketException = RuntimeError  # type: ignore

INITIAL_WS_RECONNECT_DELAY_S = 0.25
MAX_WS_RECONNECT_DELAY_S = 2.0


class ApiTelemetryClient:
    """Own telemetry streaming and REST snapshot fallback for the API bridge."""

    def __init__(self, host: Any) -> None:
        self._host = host

    def snapshot_poll_loop(self) -> None:
        """Poll REST telemetry snapshots until the host stops."""
        host = self._host
        while not host._stop.is_set():
            self.pull_snapshot_once()
            host._stop.wait(host.snapshot_poll_interval_s)

    def pull_snapshot_once(self) -> None:
        """Pull one telemetry snapshot batch through REST.

        Raises:
            No exceptions escape. Errors are normalized into metrics and logs.

        Boundary behaviour:
            Snapshot polling updates telemetry projections only; it never issues
            control commands or lease mutations.
        """
        host = self._host
        try:
            response = host._client.get("/api/v1/telemetry/snapshot")
            response.raise_for_status()
            items = response.json() if response.content else []
            if items:
                with host._lock:
                    host._metrics.telemetry_connected = True
                for item in items if isinstance(items, list) else []:
                    self.emit_snapshot_item(item)
            else:
                with host._lock:
                    host._metrics.telemetry_connected = False
        except (httpx.HTTPError, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
            normalized = normalize_backend_exception(exc, context="snapshot-poll")
            with host._lock:
                host._metrics.telemetry_connected = False
            remember_backend_error(host._last_errors, f"snapshot: {normalized.error_type}: {normalized.message}")
            host._log("WARN", f"遥测快照拉取失败：{normalized.error_type}: {normalized.message}")

    def telemetry_ws_loop(self) -> None:
        """Consume telemetry WebSocket messages and publish Qt-safe envelopes."""
        assert ws_connect is not None
        host = self._host
        url = f"{host.ws_base}/ws/telemetry"
        reconnect_delay_s = INITIAL_WS_RECONNECT_DELAY_S
        while not host._stop.is_set():
            try:
                with ws_connect(url, open_timeout=host.request_timeout_s, close_timeout=1.0) as ws:
                    with host._lock:
                        host._metrics.telemetry_connected = True
                    reconnect_delay_s = INITIAL_WS_RECONNECT_DELAY_S
                    host._log("INFO", "已连接 headless telemetry WebSocket。")
                    for raw in ws:
                        if host._stop.is_set():
                            break
                        self.emit_snapshot_item(json.loads(raw))
            except (WebSocketException, json.JSONDecodeError, OSError, RuntimeError, ValueError, TypeError) as exc:
                normalized = normalize_backend_exception(exc, context="telemetry-ws")
                with host._lock:
                    host._metrics.telemetry_connected = False
                    host._metrics.reconnect_count += 1
                remember_backend_error(host._last_errors, f"telemetry-ws: {normalized.error_type}: {normalized.message}")
                host._log("WARN", f"telemetry WebSocket 断开：{normalized.error_type}: {normalized.message}")
                host._stop.wait(reconnect_delay_s)
                reconnect_delay_s = min(MAX_WS_RECONNECT_DELAY_S, reconnect_delay_s * 2.0)

    def emit_snapshot_item(self, item: dict[str, Any]) -> None:
        """Publish one telemetry item into projection cache and Qt signal."""
        host = self._host
        topic = str(item.get("topic", ""))
        if not topic:
            return
        env = TelemetryEnvelope(topic=topic, data=dict(item.get("data", {})), ts_ns=int(item.get("ts_ns", now_ns()) or now_ns()))
        host._projection_cache.update_partition(f"topic:{topic}", {"topic": topic, "data": env.data, "ts_ns": env.ts_ns})
        host.telemetry_received.emit(env)
