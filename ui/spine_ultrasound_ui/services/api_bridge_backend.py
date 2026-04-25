from __future__ import annotations

import json
import os
import socket
import threading
from collections import deque
from pathlib import Path
from typing import Any, Optional
import httpx
from PySide6.QtCore import QObject, Signal
from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils import ensure_dir, now_ns, now_text

from .api_bridge_backend_helpers import build_command_headers, decode_pixmap_payload, remember_backend_error
from .api_bridge_lease_service import ApiBridgeLeaseService
from .api_bridge_verdict_service import ApiBridgeVerdictService
from .api_bridge_media_client import ApiMediaClient
from .api_bridge_telemetry_client import ApiTelemetryClient
from .api_bridge_authority_projection_reader import ApiAuthorityProjectionReader
from .api_bridge_transport_client import ApiBridgeTransportClient
from .backend_authoritative_contract_service import BackendAuthoritativeContractService
from .backend_command_error_service import BackendCommandErrorService
from .backend_error_mapper import BackendErrorMapper  # explicit authority edge for backend error normalization
from .backend_base import BackendBase
from .backend_capability_matrix_service import BackendCapabilityMatrixService
from .backend_control_plane_projection_service import BackendControlPlaneProjectionService
from .backend_control_plane_service import BackendControlPlaneService
from .backend_errors import BackendOperationError, normalize_backend_exception
from .backend_link_service import BackendLinkMetrics, BackendLinkService
from .backend_projection_cache import BackendProjectionCache
from .ipc_protocol import ReplyEnvelope, TelemetryEnvelope

try:  # pragma: no cover
    from websockets.sync.client import connect as ws_connect
    from websockets.exceptions import WebSocketException
except ImportError:  # pragma: no cover
    ws_connect = None  # type: ignore
    WebSocketException = RuntimeError  # type: ignore


ERROR_HISTORY_LIMIT = 8
INITIAL_WS_RECONNECT_DELAY_S = 0.25
MAX_WS_RECONNECT_DELAY_S = 2.0


class ApiBridgeBackend(QObject, BackendBase):
    """Qt-facing façade that composes read-only API bridge collaborators."""
    READ_ONLY_TRANSPORT_INVARIANT = "effective_include_lease = False; headless HTTP API is read-only; lease headers suppressed"
    COMMAND_ERROR_SERVICE_CONTRACT = "BackendCommandErrorService.build_reply"
    telemetry_received = Signal(object)
    log_generated = Signal(str, str)
    camera_pixmap_ready = Signal(QPixmap)
    ultrasound_pixmap_ready = Signal(QPixmap)
    reconstruction_pixmap_ready = Signal(QPixmap)
    def __init__(
        self,
        root_dir: Path,
        base_url: str = "http://127.0.0.1:8000",
        *,
        request_timeout_s: float = 4.0,
        health_poll_interval_s: float = 1.0,
        snapshot_poll_interval_s: float = 0.5,
        deployment_profile: str = "dev",
    ) -> None:
        """Create the API bridge backend and initialize read-only caches/transports."""
        super().__init__()
        self.root_dir = ensure_dir(root_dir)
        self.config = RuntimeConfig()
        self.link_service = BackendLinkService()
        self.base_url = self.link_service.normalize_http_base(base_url)
        self.ws_base = self.link_service.infer_ws_base(self.base_url)
        self.request_timeout_s = float(request_timeout_s)
        self.health_poll_interval_s = float(health_poll_interval_s)
        self.snapshot_poll_interval_s = float(snapshot_poll_interval_s)
        self._client = httpx.Client(base_url=self.base_url, timeout=self.request_timeout_s)
        self._stop = threading.Event()
        self._threads: list[threading.Thread] = []
        self._lock = threading.Lock()
        self._status_cache: dict[str, Any] = {}
        self._health_cache: dict[str, Any] = {}
        self._runtime_config_cache: dict[str, Any] = {}
        self._schema_cache: dict[str, Any] = {}
        self._topic_catalog_cache: dict[str, Any] = {}
        self._recent_commands_cache: list[dict[str, Any]] = []
        self._control_plane_cache: dict[str, Any] = {}
        self._control_authority_cache: dict[str, Any] = {}
        self._authoritative_envelope: dict[str, Any] = {}
        self._last_errors: deque[str] = deque(maxlen=ERROR_HISTORY_LIMIT)
        self._last_final_verdict: dict[str, Any] = {}
        self._control_plane_service = BackendControlPlaneService()
        self._projection_service = BackendControlPlaneProjectionService()
        self._authoritative_service = BackendAuthoritativeContractService()
        self._projection_cache = BackendProjectionCache()
        self._metrics = BackendLinkMetrics(using_websocket_telemetry=ws_connect is not None, using_websocket_media=ws_connect is not None)
        self._deployment_profile = str(deployment_profile or "dev").strip().lower()
        self._actor_id = os.getenv("SPINE_ACTOR_ID", f"desktop-{socket.gethostname()}")
        self._workspace = os.getenv("SPINE_WORKSPACE", "desktop")
        self._role = os.getenv("SPINE_ROLE", "operator")
        self._lease_id = ""
        self._lease_service = ApiBridgeLeaseService(self)
        self._verdict_service = ApiBridgeVerdictService(self)
        self._using_websocket = ws_connect is not None
        self._transport_client = ApiBridgeTransportClient(self)
        self._authority_reader = ApiAuthorityProjectionReader(self)
        self._telemetry_client = ApiTelemetryClient(self)
        self._media_client = ApiMediaClient(self)

    def _lease_allowed(self) -> bool:
        """Return whether the API bridge may mutate control-lease state."""
        return False

    def start(self) -> None:
        """Start delegated polling/streaming loops and refresh local runtime-config state."""
        if self._threads:
            return
        self._stop.clear()
        self._spawn(self._authority_reader.health_loop, "api-health-loop")
        if self._using_websocket:
            self._spawn(self._telemetry_client.telemetry_ws_loop, "api-telemetry-ws")
            self._spawn(lambda: self._media_client.media_ws_loop("camera", self.camera_pixmap_ready), "api-camera-ws")
            self._spawn(lambda: self._media_client.media_ws_loop("ultrasound", self.ultrasound_pixmap_ready), "api-ultrasound-ws")
        else:
            self._spawn(self._telemetry_client.snapshot_poll_loop, "api-snapshot-poll")
            self._log("WARN", "websockets 依赖不可用，已退回 REST 快照轮询模式。")
        self._log("INFO", "headless HTTP API is read-only; startup skips all lease mutation paths.")
        self._transport_client.push_runtime_config()
        self._log("INFO", f"ApiBridgeBackend 已启动，HTTP {self.base_url} / WS {self.ws_base}")

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        """Update desired runtime config and refresh read-only API runtime state."""
        self.config = config
        self._projection_cache.update_partition("desired_runtime_config", config.to_dict())
        self._transport_client.push_runtime_config()

    def send_command(self, command: str, payload: Optional[dict] = None, *, context: Optional[dict] = None) -> ReplyEnvelope:
        """Delegate command transport to ``ApiBridgeTransportClient``."""
        return self._transport_client.send_command(command, payload, context=context)

    def capability_matrix(self) -> dict[str, dict[str, Any]]:
        """Return the explicit capability contract for the API bridge surface."""
        return BackendCapabilityMatrixService.build({
            "camera": "monitor_only",
            "ultrasound": "monitor_only",
            "reconstruction": "monitor_only",
            "recording": "monitor_only",
        })

    def status(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._status_cache)
    def health(self) -> dict[str, Any]:
        with self._lock:
            return dict(self._health_cache)
    def link_snapshot(self) -> dict[str, Any]:
        """Build the canonical backend-link snapshot consumed by the desktop UI."""
        with self._lock:
            status = dict(self._status_cache)
            health = dict(self._health_cache)
            metrics = BackendLinkMetrics(**self._metrics.__dict__)
            errors = list(self._last_errors)
            control_plane = dict(self._control_plane_cache)
            authoritative_envelope = dict(self._authoritative_envelope)
            control_authority = dict(self._control_authority_cache)
        control_plane = self._projection_service.build(
            control_plane=control_plane,
            authoritative_envelope=authoritative_envelope,
            projection_cache=self._projection_cache,
            control_authority=control_authority,
        )
        snapshot = self.link_service.build_snapshot(
            mode="api",
            http_base=self.base_url,
            ws_base=self.ws_base,
            status=status,
            health=health,
            metrics=metrics,
            extra_errors=errors,
            control_plane=control_plane,
            local_runtime_config=self.config.to_dict(),
            authoritative_runtime_envelope=authoritative_envelope,
        )
        snapshot["media_capabilities"] = self.media_capabilities()
        snapshot["capability_matrix"] = self.capability_matrix()
        return snapshot
    def resolve_authoritative_runtime_envelope(self) -> dict[str, Any]:
        """Return the canonical runtime-owned authoritative envelope for read consumers."""
        with self._lock:
            envelope = dict(self._authoritative_envelope)
        if envelope:
            return envelope
        return self._authoritative_service.build_unavailable_authoritative_runtime_envelope(
            authority_source="api_bridge",
            detail="api bridge has not received a runtime-published authoritative envelope",
            desired_runtime_config=self.config,
            envelope_origin="api_bridge_cache_empty",
        )

    def resolve_control_authority(self) -> dict[str, Any]:
        """Return the canonical control-authority snapshot for read consumers."""
        return dict(self.resolve_authoritative_runtime_envelope().get("control_authority", {}))
    def acquire_control_lease(self, *, force: bool = False) -> dict[str, Any]:
        """Return the current runtime-published control-authority snapshot.

        The API bridge is read-only and must not acquire a lease. This method
        is retained only as a compatibility shim for callers that still expect a
        dictionary result.
        """
        return dict(self._lease_service.acquire_control_lease(force=force))
    def renew_control_lease(self, *, ttl_s: int | None = None) -> dict[str, Any]:
        """Return the current runtime-published control-authority snapshot.

        The API bridge is read-only and must not renew a lease. This method is
        retained only as a compatibility shim.
        """
        return dict(self._lease_service.renew_control_lease(ttl_s=ttl_s))
    def release_control_lease(self, *, reason: str = "") -> dict[str, Any]:
        """Return the current runtime-published control-authority snapshot.

        The API bridge is read-only and must not release a lease. This method
        is retained only as a compatibility shim.
        """
        return dict(self._lease_service.release_control_lease(reason=reason))
    def resolve_final_verdict(self, plan=None, config: RuntimeConfig | None = None, *, read_only: bool) -> dict[str, Any]:
        """Resolve the authoritative runtime final verdict through the canonical backend API."""
        return self._verdict_service.resolve_final_verdict(plan, config, read_only=read_only)
    def query_final_verdict_snapshot(self) -> dict[str, Any]:
        """Compatibility wrapper for the read-only final-verdict snapshot API."""
        return self.resolve_final_verdict(read_only=True)
    def compile_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict[str, Any]:
        """Compatibility wrapper for compile-time final-verdict resolution."""
        return self.resolve_final_verdict(plan, config, read_only=False)
    def get_final_verdict(self, plan=None, config: RuntimeConfig | None = None) -> dict[str, Any]:
        return self.compile_final_verdict(plan, config)
    def close(self) -> None:
        """Stop background loops and close the delegated HTTP client."""
        self._stop.set()
        for thread in list(self._threads):
            if thread.is_alive():
                thread.join(timeout=1.0)
        self._threads.clear()
        self._transport_client.close()

    def _spawn(self, target, name: str) -> None:
        thread = threading.Thread(target=target, name=name, daemon=True)
        self._threads.append(thread)
        thread.start()
    def _log(self, level: str, message: str) -> None:
        try:
            self.log_generated.emit(level, f"[{now_text()}] {message}")
        except RuntimeError:
            pass
