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
    def command_policy_catalog(self) -> dict: return {'policies': [{'command': 'start_scan', 'allowed_states': ['CONTACT_STABLE'], 'role_write_gate': ['operator']}]}
    def event_dead_letters(self) -> dict: return {'entries': [{'topic': 'release_evidence_updated'}], 'summary': {'dead_letter_count': 1}}
    def replay_events(self, **kwargs) -> dict: return {'session_id': kwargs.get('session_id', 'S1'), 'events': [{'topic': 'event_log_index_updated'}], 'summary': {'count': 1}, 'next_cursor': None}
    def event_bus_stats(self) -> dict: return {'published_events': 4, 'pending_ack_count': 1}
    def current_session(self) -> dict: return {'session_id': 'S1'}
    def current_resume_attempts(self) -> dict: return {'session_id': 'S1', 'summary': {'attempt_count': 2}, 'attempts': []}
    def current_resume_outcomes(self) -> dict: return {'session_id': 'S1', 'summary': {'attempt_count': 2}, 'outcomes': []}
    def current_command_policy(self) -> dict: return self.command_policy_catalog()
    def current_contract_consistency(self) -> dict: return {'session_id': 'S1', 'summary': {'consistent': True}, 'mismatches': []}
    def current_release_evidence(self) -> dict: return {'session_id': 'S1', 'release_candidate': True, 'open_gaps': []}


def _client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(api_server, 'adapter', _StubAdapter())
    return TestClient(api_server.app)


def test_api_server_v7_command_policy(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.get('/api/v1/command-policies')
        assert response.status_code == 200
        body = response.json()
        assert body['policies'][0]['command'] == 'start_scan'


def test_api_server_v7_dead_letters(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.get('/api/v1/events/dead-letters')
        assert response.status_code == 200
        body = response.json()
        assert body['summary']['dead_letter_count'] == 1


def test_api_server_v7_resume_outcomes(monkeypatch: pytest.MonkeyPatch):
    with _client(monkeypatch) as client:
        response = client.get('/api/v1/sessions/current/resume-outcomes')
        assert response.status_code == 200
        body = response.json()
        assert body['summary']['attempt_count'] == 2
