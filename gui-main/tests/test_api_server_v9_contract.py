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
    def snapshot(self, topics=None) -> list[dict]: return []
    def schema(self) -> dict: return {'api_version': 'v1', 'protocol_version': 1, 'commands': {}, 'telemetry_topics': {}, 'force_control': {'desired_contact_force_n': 10.0, 'stale_telemetry_ms': 250}}
    def topic_catalog(self) -> dict: return {'topics': []}
    def role_catalog(self) -> dict: return {'roles': {'operator': {}}}
    def command_policy_catalog(self) -> dict: return {'policies': []}
    def current_session(self) -> dict: return {'session_id': 'S1'}
    def current_selected_execution_rationale(self) -> dict: return {'session_id': 'S1', 'selected_plan_id': 'P1'}
    def current_release_gate_decision(self) -> dict: return {'session_id': 'S1', 'release_allowed': False, 'blocking_reasons': ['contract_alignment_failed']}


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(api_server, 'adapter', _StubAdapter())
    return TestClient(api_server.app)


def test_api_server_v9_selected_execution(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.get('/api/v1/sessions/current/selected-execution-rationale')
        assert response.status_code == 200
        assert response.json()['selected_plan_id'] == 'P1'


def test_api_server_v9_release_gate(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.get('/api/v1/sessions/current/release-gate')
        assert response.status_code == 200
        body = response.json()
        assert body['release_allowed'] is False
        assert body['blocking_reasons'] == ['contract_alignment_failed']
