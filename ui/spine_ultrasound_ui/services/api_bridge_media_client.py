from __future__ import annotations

from typing import Any

from .api_bridge_backend_helpers import decode_pixmap_payload, remember_backend_error
from .backend_errors import normalize_backend_exception

try:  # pragma: no cover
    from websockets.sync.client import connect as ws_connect
    from websockets.exceptions import WebSocketException
except ImportError:  # pragma: no cover
    ws_connect = None  # type: ignore
    WebSocketException = RuntimeError  # type: ignore

INITIAL_WS_RECONNECT_DELAY_S = 0.25
MAX_WS_RECONNECT_DELAY_S = 2.0


class ApiMediaClient:
    """Own monitor-only camera and ultrasound WebSocket media streams."""

    def __init__(self, host: Any) -> None:
        self._host = host

    def media_ws_loop(self, channel: str, signal: Any) -> None:
        """Stream one monitor-only media channel.

        Args:
            channel: API channel name, for example ``camera`` or ``ultrasound``.
            signal: Qt signal receiving decoded pixmaps.

        Raises:
            No exceptions escape; disconnects are logged and retried.

        Boundary behaviour:
            Media streams are monitor-only evidence projections and never issue
            runtime write commands.
        """
        assert ws_connect is not None
        host = self._host
        url = f"{host.ws_base}/ws/{channel}"
        metric_name = f"{channel}_connected"
        reconnect_delay_s = INITIAL_WS_RECONNECT_DELAY_S
        while not host._stop.is_set():
            try:
                with ws_connect(url, open_timeout=host.request_timeout_s, close_timeout=1.0) as ws:
                    with host._lock:
                        setattr(host._metrics, metric_name, True)
                    reconnect_delay_s = INITIAL_WS_RECONNECT_DELAY_S
                    host._log("INFO", f"已连接 {channel} WebSocket。")
                    for raw in ws:
                        if host._stop.is_set():
                            break
                        pixmap = decode_pixmap_payload(raw)
                        if pixmap is not None:
                            signal.emit(pixmap)
            except (WebSocketException, OSError, RuntimeError, ValueError, TypeError) as exc:
                normalized = normalize_backend_exception(exc, context=f"{channel}-ws")
                with host._lock:
                    setattr(host._metrics, metric_name, False)
                    host._metrics.reconnect_count += 1
                remember_backend_error(host._last_errors, f"{channel}-ws: {normalized.error_type}: {normalized.message}")
                host._log("WARN", f"{channel} WebSocket 断开：{normalized.error_type}: {normalized.message}")
                host._stop.wait(reconnect_delay_s)
                reconnect_delay_s = min(MAX_WS_RECONNECT_DELAY_S, reconnect_delay_s * 2.0)
