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
    def current_command_policy_snapshot(self) -> dict: return {'policy_version': 'command_state_policy_v2', 'decision_count': 3, 'decisions': {'start_scan': {'allowed': True}}}
    def current_contract_kernel_diff(self) -> dict: return {'session_id': 'S1', 'summary': {'consistent': True, 'diff_count': 0, 'checked_object_count': 3}, 'checks': {'policy_snapshot_coverage': True}, 'diffs': []}
    def current_session(self) -> dict: return {'session_id': 'S1', 'contract_kernel_diff_available': True, 'command_policy_snapshot_available': True}


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(api_server, 'adapter', _StubAdapter())
    return TestClient(api_server.app)


def test_api_server_v11_contract_kernel_diff(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.get('/api/v1/sessions/current/contract-kernel-diff')
        assert response.status_code == 200
        body = response.json()
        assert body['summary']['consistent'] is True
