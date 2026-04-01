from __future__ import annotations

import pytest

pytest.importorskip('fastapi')
pytest.importorskip('httpx')

from fastapi.testclient import TestClient

import spine_ultrasound_ui.api_server as api_server


class _StubAdapter:
    read_only_mode = False
    def start(self) -> None: ...
    def stop(self) -> None: ...
    def status(self) -> dict: return {'backend_mode': 'mock', 'execution_state': 'AUTO_READY', 'protocol_version': 1, 'session_id': 'S1'}
    def health(self) -> dict: return {'backend_mode': 'mock', 'telemetry_stale': False, 'latest_telemetry_age_ms': 5}
    def snapshot(self, topics=None) -> list[dict]: return [{'topic': 'core_state', 'ts_ns': 1, 'data': {'execution_state': 'AUTO_READY'}}]
    def schema(self) -> dict: return {'api_version': 'v1', 'protocol_version': 1, 'commands': {}, 'telemetry_topics': {}, 'force_control': {'desired_contact_force_n': 10.0, 'stale_telemetry_ms': 250}}
    def topic_catalog(self) -> dict: return {'topics': []}
    def role_catalog(self) -> dict: return {'roles': {'operator': {}}}
    def command_policy_catalog(self) -> dict: return {'policies': []}
    def runtime_config(self) -> dict: return {'runtime_config': {'robot_model': 'xmate_er3'}}


def test_api_server_exposes_deployment_profile(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(api_server, 'adapter', _StubAdapter())
    with TestClient(api_server.app) as client:
        response = client.get('/api/v1/profile')
        assert response.status_code == 200
        body = response.json()
        assert body['deployment_profile']['name'] in {'dev', 'research', 'clinical', 'review'}
        assert body['runtime_config_present'] is True
