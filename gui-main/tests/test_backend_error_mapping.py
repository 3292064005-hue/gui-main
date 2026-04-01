from __future__ import annotations

from pathlib import Path

import httpx
from fastapi.testclient import TestClient

import spine_ultrasound_ui.api_server as api_server
from spine_ultrasound_ui.services.backend_error_mapper import BackendErrorMapper
from spine_ultrasound_ui.services.backend_errors import InvalidPayloadError, normalize_backend_exception
from spine_ultrasound_ui.services.robot_core_client import RobotCoreClientBackend
from spine_ultrasound_ui.services.api_bridge_backend import ApiBridgeBackend


class _StopFailingAdapter:
    def __init__(self) -> None:
        self.started = 0
        self.closed = 0

    def start(self) -> None:
        self.started += 1

    def stop(self) -> None:
        raise RuntimeError("stop cleanup failed")

    def close(self) -> None:
        self.closed += 1

    def status(self) -> dict:
        return {"backend_mode": "mock"}

    def health(self) -> dict:
        return {"adapter_running": True, "telemetry_stale": False}

    def schema(self) -> dict:
        return {"protocol_version": 1}

    def snapshot(self, topics=None):
        return []


class _TransportRaisingClient:
    def post(self, *args, **kwargs):
        raise httpx.ReadTimeout("deadline exceeded")

    def put(self, *args, **kwargs):
        raise httpx.ReadTimeout("deadline exceeded")

    def get(self, *args, **kwargs):
        raise httpx.ConnectError("socket down")

    def close(self) -> None:
        return None


def test_backend_error_mapper_exposes_typed_metadata() -> None:
    reply = BackendErrorMapper.reply_from_exception(httpx.ReadTimeout("deadline exceeded"), command="start_scan", context="api-command")
    assert reply.ok is False
    assert reply.data["error_type"] == "transport_timeout"
    assert reply.data["retryable"] is True
    assert reply.data["command"] == "start_scan"


def test_normalize_backend_exception_maps_invalid_payload() -> None:
    normalized = normalize_backend_exception(ValueError("payload schema mismatch"), command="load_scan_plan")
    assert normalized.error_type == "schema_mismatch"
    assert normalized.http_status == 422


def test_api_bridge_backend_returns_typed_transport_error(tmp_path: Path) -> None:
    backend = ApiBridgeBackend(tmp_path)
    backend._client = _TransportRaisingClient()  # type: ignore[assignment]
    reply = backend.send_command("start_scan", {})
    assert reply.ok is False
    assert reply.data["error_type"] == "transport_timeout"
    assert reply.data["command"] == "start_scan"


def test_robot_core_client_returns_typed_transport_error(tmp_path: Path, monkeypatch) -> None:
    import spine_ultrasound_ui.services.robot_core_client as module

    monkeypatch.setattr(module, "create_client_ssl_context", lambda cert_path=None: object())
    monkeypatch.setattr(module, "send_tls_command", lambda *args, **kwargs: (_ for _ in ()).throw(TimeoutError("tls timeout")))
    backend = RobotCoreClientBackend(tmp_path)
    reply = backend.send_command("start_scan", {})
    assert reply.ok is False
    assert reply.data["error_type"] == "transport_timeout"
    assert reply.data["command"] == "start_scan"


def test_api_server_lifespan_attempts_close_after_stop_failure() -> None:
    adapter = _StopFailingAdapter()
    app = api_server.create_app(adapter_getter=lambda: adapter, allowed_origins=["http://localhost:3000"])
    with TestClient(app) as client:
        response = client.get("/api/v1/status")
        assert response.status_code == 200
    assert adapter.started == 1
    assert adapter.closed == 1
