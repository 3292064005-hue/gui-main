from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import spine_ultrasound_ui.api_server as api_server
from spine_ultrasound_ui.services.api_command_guard import ApiCommandGuardService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService

pytest.importorskip('fastapi')
pytest.importorskip('httpx')


class _RoleMatrix:
    def can_issue_command(self, role: str, command: str) -> bool:
        return role in {'operator', 'service'}


class _Adapter:
    read_only_mode = False
    role_matrix = _RoleMatrix()

    def start(self):
        pass

    def stop(self):
        pass

    def command(self, command: str, payload: dict):
        return {'ok': True, 'message': 'ok', 'request_id': 'req-1', 'data': payload, 'protocol_version': 1}


def test_api_server_rejects_missing_token_for_clinical_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_server, 'adapter', _Adapter())
    monkeypatch.setattr(api_server, 'api_command_guard_service', ApiCommandGuardService(DeploymentProfileService({'SPINE_DEPLOYMENT_PROFILE': 'clinical', 'SPINE_API_TOKEN': 'secret'}), {'SPINE_DEPLOYMENT_PROFILE': 'clinical', 'SPINE_API_TOKEN': 'secret'}))
    with TestClient(api_server.app) as client:
        response = client.post('/api/v1/commands/start_scan', json={})
        assert response.status_code == 403


def test_api_server_accepts_token_for_clinical_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api_server, 'adapter', _Adapter())
    monkeypatch.setattr(api_server, 'api_command_guard_service', ApiCommandGuardService(DeploymentProfileService({'SPINE_DEPLOYMENT_PROFILE': 'clinical', 'SPINE_API_TOKEN': 'secret'}), {'SPINE_DEPLOYMENT_PROFILE': 'clinical', 'SPINE_API_TOKEN': 'secret'}))
    with TestClient(api_server.app) as client:
        response = client.post('/api/v1/commands/start_scan', json={}, headers={'x-spine-api-token': 'secret', 'x-spine-actor': 'alice'})
        assert response.status_code == 200
        body = response.json()
        assert body['data']['_command_context']['profile'] == 'clinical'
