from __future__ import annotations

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("httpx")

from fastapi.testclient import TestClient

import spine_ultrasound_ui.api_server as api_server
from spine_ultrasound_ui.services.backend_control_plane_service import BackendControlPlaneService
from spine_ultrasound_ui.services.backend_link_service import BackendLinkMetrics, BackendLinkService


class _StubContainer:
    def __init__(self, runtime_adapter: "_StubAdapter") -> None:
        self.runtime_adapter = runtime_adapter
        self.deployment_profile_service = None
        self.command_guard_service = None



class _StubAdapter:
    def __init__(self) -> None:
        self._runtime_config = {"pressure_target": 8.0}

    def start(self) -> None:
        pass

    def stop(self) -> None:
        pass

    def status(self) -> dict:
        return {
            "backend_mode": "mock",
            "execution_state": "AUTO_READY",
            "protocol_version": 1,
            "session_id": "S1",
            "command_endpoint": "127.0.0.1:5656",
            "telemetry_endpoint": "127.0.0.1:5657",
        }

    def health(self) -> dict:
        return {
            "backend_mode": "mock",
            "adapter_running": True,
            "telemetry_stale": False,
            "latest_telemetry_age_ms": 12,
            "execution_state": "AUTO_READY",
        }

    def snapshot(self, topics=None) -> list[dict]:
        payload = [{"topic": "core_state", "ts_ns": 1, "data": {"execution_state": "AUTO_READY"}}]
        return payload if topics is None else [item for item in payload if item["topic"] in topics]

    def schema(self) -> dict:
        return {
            "api_version": "v1",
            "protocol_version": 1,
            "commands": {},
            "telemetry_topics": {},
            "force_control": {"desired_contact_force_n": 8.0, "stale_telemetry_ms": 250},
        }

    def runtime_config(self) -> dict:
        return {"runtime_config": dict(self._runtime_config)}

    def set_runtime_config(self, payload: dict) -> dict:
        self._runtime_config = dict(payload)
        return {"runtime_config": dict(self._runtime_config), "backend_mode": "mock"}

    def topic_catalog(self) -> dict:
        return {"topics": [{"name": "core_state"}, {"name": "robot_state"}, {"name": "safety_status"}, {"name": "scan_progress"}, {"name": "contact_state"}]}

    def recent_commands(self) -> dict:
        return {"recent_commands": [{"command": "connect_robot", "ok": True, "message": "connected"}]}

    def control_plane_status(self) -> dict:
        return {
            "status": self.status(),
            "health": self.health(),
            "schema": self.schema(),
            "runtime_config": self.runtime_config(),
            "topics": self.topic_catalog(),
            "recent_commands": self.recent_commands(),
        }

    def camera_frame(self) -> str:
        return "camera"

    def ultrasound_frame(self) -> str:
        return "ultrasound"


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    runtime_container = _StubContainer(_StubAdapter())
    app = api_server.create_app(runtime_container=runtime_container, allowed_origins=["http://localhost:3000"])
    return TestClient(app)


def test_backend_link_service_reports_ready_state() -> None:
    service = BackendLinkService()
    metrics = BackendLinkMetrics(
        commands_sent=5,
        commands_failed=0,
        telemetry_connected=True,
        camera_connected=True,
        ultrasound_connected=True,
        rest_reachable=True,
        using_websocket_telemetry=True,
        using_websocket_media=True,
    )
    snapshot = service.build_snapshot(
        mode="api",
        http_base="127.0.0.1:8000",
        ws_base="ws://127.0.0.1:8000",
        status={"backend_mode": "mock"},
        health={"adapter_running": True, "telemetry_stale": False, "latest_telemetry_age_ms": 12},
        metrics=metrics,
    )
    assert snapshot["summary_state"] == "ready"
    assert snapshot["command_success_rate"] == 100
    assert snapshot["telemetry_connected"] is True


def test_backend_link_service_reports_blocked_state() -> None:
    service = BackendLinkService()
    snapshot = service.build_snapshot(
        mode="api",
        http_base="http://127.0.0.1:8000",
        ws_base="ws://127.0.0.1:8000",
        status={},
        health={"adapter_running": False, "telemetry_stale": True},
        metrics=BackendLinkMetrics(commands_sent=2, commands_failed=1, rest_reachable=False, telemetry_connected=False),
    )
    assert snapshot["summary_state"] == "blocked"
    blocker_names = {item["name"] for item in snapshot["blockers"]}
    assert "REST 网关不可达" in blocker_names
    assert "遥测通道未连通" in blocker_names


def test_api_server_runtime_config_roundtrip(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch) as client:
        post_resp = client.post("/api/v1/runtime-config", json={"pressure_target": 9.5, "rt_mode": "cartesianImpedance"})
        assert post_resp.status_code == 200
        get_resp = client.get("/api/v1/runtime-config")
        assert get_resp.status_code == 200
        assert get_resp.json()["runtime_config"]["pressure_target"] == 9.5


def test_api_server_backend_link_state(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/backend/link-state")
        assert response.status_code == 200
        body = response.json()
        assert body["status"]["backend_mode"] == "mock"
        assert body["health"]["adapter_running"] is True
        assert body["topics"]["topics"][0]["name"] == "core_state"


def test_backend_control_plane_service_detects_config_drift() -> None:
    service = BackendControlPlaneService()
    from spine_ultrasound_ui.models import RuntimeConfig

    result = service.build(
        local_config=RuntimeConfig(pressure_target=8.0),
        runtime_config={"runtime_config": {"pressure_target": 9.5, "rt_mode": "cartesianImpedance"}},
        schema={"protocol_version": 1},
        status={"protocol_version": 1},
        health={"protocol_version": 1},
        topic_catalog={"topics": [{"name": "core_state"}, {"name": "robot_state"}, {"name": "safety_status"}, {"name": "scan_progress"}, {"name": "contact_state"}]},
        recent_commands=[{"command": "start_scan", "ok": True, "message": "started"}],
    )
    assert result["summary_state"] == "blocked"
    assert result["config_sync"]["summary_label"] == "配置漂移"


def test_api_server_control_plane_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    with _client(monkeypatch) as client:
        response = client.get("/api/v1/control-plane")
        assert response.status_code == 200
        body = response.json()
        assert body["runtime_config"]["runtime_config"]["pressure_target"] == 8.0
        assert body["recent_commands"]["recent_commands"][0]["command"] == "connect_robot"
        assert body["topics"]["topics"][0]["name"] == "core_state"


def test_backend_link_snapshot_includes_control_plane() -> None:
    service = BackendLinkService()
    metrics = BackendLinkMetrics(
        commands_sent=4,
        commands_failed=0,
        telemetry_connected=True,
        camera_connected=True,
        ultrasound_connected=True,
        rest_reachable=True,
        using_websocket_telemetry=True,
        using_websocket_media=True,
    )
    control_plane = BackendControlPlaneService().build(
        local_config=__import__("spine_ultrasound_ui.models", fromlist=["RuntimeConfig"]).RuntimeConfig(),
        runtime_config={"runtime_config": __import__("spine_ultrasound_ui.models", fromlist=["RuntimeConfig"]).RuntimeConfig().to_dict()},
        schema={"protocol_version": 1},
        status={"protocol_version": 1},
        health={"protocol_version": 1},
        topic_catalog={"topics": [{"name": "core_state"}, {"name": "robot_state"}, {"name": "safety_status"}, {"name": "scan_progress"}, {"name": "contact_state"}]},
        recent_commands=[{"command": "connect_robot", "ok": True, "message": "ok"}],
    )
    snapshot = service.build_snapshot(
        mode="api",
        http_base="http://127.0.0.1:8000",
        ws_base="ws://127.0.0.1:8000",
        status={"backend_mode": "mock", "protocol_version": 1},
        health={"adapter_running": True, "telemetry_stale": False, "latest_telemetry_age_ms": 12, "protocol_version": 1},
        metrics=metrics,
        control_plane=control_plane,
    )
    assert snapshot["control_plane"]["summary_label"] == "控制面一致"
    assert snapshot["summary_state"] == "ready"



def test_control_plane_endpoint_exposes_projection_and_authoritative_envelope(monkeypatch: pytest.MonkeyPatch) -> None:
    from spine_ultrasound_ui.services.headless_control_plane_aggregator import HeadlessControlPlaneAggregator
    from spine_ultrasound_ui.models import RuntimeConfig

    aggregator = HeadlessControlPlaneAggregator()
    result = aggregator.build(
        local_config=RuntimeConfig(),
        runtime_config={"runtime_config": RuntimeConfig().to_dict()},
        schema={"protocol_version": 1},
        status={"protocol_version": 1, "backend_mode": "mock", "execution_state": "AUTO_READY"},
        health={"protocol_version": 1, "adapter_running": True, "telemetry_stale": False, "latest_telemetry_age_ms": 10},
        topic_catalog={"topics": [{"name": "core_state"}, {"name": "robot_state"}, {"name": "safety_status"}, {"name": "scan_progress"}, {"name": "contact_state"}]},
        recent_commands=[{"command": "connect_robot", "ok": True, "message": "ok"}],
        control_authority={"summary_state": "ready", "owner": {"actor_id": "tester", "workspace": "desktop", "role": "operator", "session_id": ""}},
    )
    assert "authoritative_runtime_envelope" in result
    assert result["authoritative_runtime_envelope"]["control_authority"]["owner"]["actor_id"] == "tester"
    assert "projection_revision" in result
    assert "projection_partitions" in result


def test_robot_core_link_snapshot_does_not_backfill_applied_runtime_config(tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    from spine_ultrasound_ui.services import robot_core_client as robot_core_client_module
    from spine_ultrasound_ui.services.robot_core_client import RobotCoreClientBackend

    monkeypatch.setattr(robot_core_client_module, "create_client_ssl_context", lambda cert_path=None: object())
    backend = RobotCoreClientBackend(tmp_path)
    backend._telemetry_connected = True
    backend._refresh_authoritative_runtime_snapshot = lambda **kwargs: None  # type: ignore[assignment]
    backend._authoritative_envelope = {
        "authority_source": "cpp_robot_core",
        "protocol_version": 1,
        "control_authority": {
            "summary_state": "degraded",
            "owner": {"actor_id": "runtime", "workspace": "runtime", "role": "runtime", "session_id": ""},
        },
    }
    snapshot = backend.link_snapshot()
    assert snapshot["control_plane"]["runtime_config_applied"] == {}
    assert snapshot["control_plane"]["runtime_config"] == {}
    assert snapshot["control_plane"]["config_sync"]["missing_remote_fields"]


def test_authoritative_contract_service_tolerates_invalid_numeric_fields() -> None:
    from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService

    service = BackendAuthoritativeContractService()
    envelope = service.normalize_payload(
        {
            "protocol_version": "not-an-int",
            "session_freeze": {"locked_at_ns": "bad", "active_segment": "oops"},
            "control_authority": {"owner": {"actor_id": "tester", "workspace": "desktop", "role": "operator"}},
        },
        authority_source="unit-test",
    )
    assert envelope["protocol_version"] == 1
    assert envelope["session_freeze"]["locked_at_ns"] == 0
    assert envelope["session_freeze"]["active_segment"] == 0


def test_authoritative_contract_service_marks_synthesized_payload_as_degraded() -> None:
    from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService

    service = BackendAuthoritativeContractService()
    envelope = service.normalize_payload(
        {
            'control_plane': {
                'control_authority': {
                    'summary_state': 'ready',
                    'owner': {'actor_id': 'tester', 'workspace': 'desktop', 'role': 'operator', 'session_id': ''},
                },
                'runtime_config': {'runtime_config': {'pressure_target': 8.0}},
            },
            'accepted': True,
            'reason': 'ok',
        },
        authority_source='unit-test',
    )
    assert envelope['authoritative_runtime_envelope_present'] is False
    assert envelope['synthesized'] is True
    assert envelope['summary_state'] == 'degraded'
    assert envelope['envelope_origin'] == 'payload_control_plane_synthesized'


def test_authoritative_contract_service_prefers_published_authoritative_envelope() -> None:
    from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService

    service = BackendAuthoritativeContractService()
    envelope = service.normalize_payload(
        {
            'authoritative_runtime_envelope': {
                'authority_source': 'cpp_robot_core',
                'protocol_version': 2,
                'control_authority': {
                    'summary_state': 'ready',
                    'owner': {'actor_id': 'runtime', 'workspace': 'runtime', 'role': 'runtime', 'session_id': ''},
                },
                'runtime_config_applied': {'pressure_target': 8.0},
                'final_verdict': {'accepted': True, 'reason': 'ok'},
            }
        },
        authority_source='unit-test',
    )
    assert envelope['authoritative_runtime_envelope_present'] is True
    assert envelope['synthesized'] is False
    assert envelope['summary_state'] == 'ready'
    assert envelope['envelope_origin'] == 'authoritative_runtime_envelope'



def test_robot_core_client_link_snapshot_keeps_authoritative_and_projected_verdicts_separate(tmp_path):
    from spine_ultrasound_ui.services.robot_core_client import RobotCoreClientBackend
    import spine_ultrasound_ui.services.robot_core_client as robot_core_client_module

    robot_core_client_module.create_client_ssl_context = lambda cert_path=None: object()
    backend = RobotCoreClientBackend(tmp_path)
    backend._authoritative_envelope = {}
    backend._last_final_verdict = {'accepted': True, 'source': 'projection'}
    backend._refresh_authoritative_runtime_snapshot = lambda **kwargs: None
    snapshot = backend.link_snapshot()
    assert snapshot['authoritative_runtime_envelope'] == {}
    assert snapshot['final_verdict'] == {}
    assert snapshot['projected_final_verdict']['source'] == 'projection'
