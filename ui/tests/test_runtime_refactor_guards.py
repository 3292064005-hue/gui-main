from __future__ import annotations

import threading

from fastapi.testclient import TestClient

import spine_ultrasound_ui.api_server as api_server
from spine_ultrasound_ui.services.backend_projection_cache import BackendProjectionCache
from spine_ultrasound_ui.services.control_authority_service import ControlAuthorityService


class _StubAdapter:
    def __init__(self) -> None:
        self.started = 0
        self.stopped = 0

    def start(self) -> None:
        self.started += 1

    def stop(self) -> None:
        self.stopped += 1

    def status(self) -> dict:
        return {"backend_mode": "mock"}

    def health(self) -> dict:
        return {"adapter_running": True, "telemetry_stale": False}

    def snapshot(self, topics=None):
        return []

    def schema(self) -> dict:
        return {"protocol_version": 1}


class _StubContainer:
    def __init__(self, runtime_adapter: _StubAdapter) -> None:
        self.runtime_adapter = runtime_adapter
        self.deployment_profile_service = None
        self.command_guard_service = None


def test_control_authority_service_linearizes_conflicting_acquire() -> None:
    service = ControlAuthorityService(strict_mode=True, auto_issue_implicit_lease=False)
    barrier = threading.Barrier(2)
    results: list[dict] = []

    def _acquire(actor_id: str) -> None:
        barrier.wait()
        results.append(service.acquire(actor_id=actor_id, role="operator", workspace="desktop", session_id="S1"))

    threads = [threading.Thread(target=_acquire, args=(actor,)) for actor in ("alice", "bob")]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    ok_count = sum(1 for item in results if item["ok"])
    assert ok_count == 1
    snapshot = service.snapshot()
    assert snapshot["has_owner"] is True
    assert snapshot["owner"]["actor_id"] in {"alice", "bob"}


def test_backend_projection_cache_snapshot_is_coherent() -> None:
    cache = BackendProjectionCache()
    cache.update_partition("control_authority", {"summary_state": "ready"})
    cache.update_partition("status", {"backend_mode": "mock"})
    snapshot = cache.snapshot()
    assert snapshot["revision"] == 2
    assert set(snapshot["partitions"]) == {"control_authority", "status"}
    assert snapshot["payloads"]["control_authority"]["summary_state"] == "ready"


def test_create_app_uses_app_local_runtime_container() -> None:
    stub_adapter = _StubAdapter()
    runtime_container = _StubContainer(stub_adapter)
    app = api_server.create_app(runtime_container=runtime_container, allowed_origins=["http://localhost:3000"])
    assert app.state.runtime_container is runtime_container
    with TestClient(app) as client:
        response = client.get("/api/v1/status")
        assert response.status_code == 200
        assert response.json()["backend_mode"] == "mock"
    assert stub_adapter.started == 1
    assert stub_adapter.stopped == 1


def test_create_app_keeps_runtime_containers_isolated_per_instance() -> None:
    first_adapter = _StubAdapter()
    second_adapter = _StubAdapter()
    first_app = api_server.create_app(runtime_container=_StubContainer(first_adapter), allowed_origins=["http://localhost:3000"])
    second_app = api_server.create_app(runtime_container=_StubContainer(second_adapter), allowed_origins=["http://localhost:3000"])

    with TestClient(first_app) as first_client:
        response = first_client.get("/api/v1/status")
        assert response.status_code == 200
        assert response.json()["backend_mode"] == "mock"
    with TestClient(second_app) as second_client:
        response = second_client.get("/api/v1/status")
        assert response.status_code == 200
        assert response.json()["backend_mode"] == "mock"

    assert first_adapter.started == 1
    assert first_adapter.stopped == 1
    assert second_adapter.started == 1
    assert second_adapter.stopped == 1


def test_api_server_settings_from_env_falls_back_on_invalid_ports() -> None:
    settings = api_server.ApiServerSettings.from_env({
        "ROBOT_CORE_COMMAND_PORT": "not-a-port",
        "ROBOT_CORE_TELEMETRY_PORT": "70000",
    })
    assert settings.command_port == 5656
    assert settings.telemetry_port == 5657
