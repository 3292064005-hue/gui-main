from __future__ import annotations

import pytest
from fastapi import HTTPException

from spine_ultrasound_ui.services.api_command_guard import ApiCommandGuardService, ApiCommandHeaders
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService


class _RoleMatrix:
    def can_issue_command(self, role: str, command: str) -> bool:
        return role in {'operator', 'service'}


class _Adapter:
    read_only_mode = False
    role_matrix = _RoleMatrix()


def test_api_command_guard_blocks_missing_token_in_clinical_profile() -> None:
    guard = ApiCommandGuardService(DeploymentProfileService({'SPINE_DEPLOYMENT_PROFILE': 'clinical', 'SPINE_API_TOKEN': 'secret'}), {'SPINE_DEPLOYMENT_PROFILE': 'clinical', 'SPINE_API_TOKEN': 'secret'})
    with pytest.raises(HTTPException) as exc:
        guard.normalize_payload(adapter=_Adapter(), command='start_scan', payload={}, headers=ApiCommandHeaders(role='operator', actor='alice'))
    assert exc.value.status_code == 403


def test_api_command_guard_normalizes_context() -> None:
    guard = ApiCommandGuardService(DeploymentProfileService({'SPINE_DEPLOYMENT_PROFILE': 'research'}), {'SPINE_DEPLOYMENT_PROFILE': 'research'})
    payload = guard.normalize_payload(adapter=_Adapter(), command='start_scan', payload={'mode': 'auto'}, headers=ApiCommandHeaders(role='operator', actor='alice', workspace='desktop', lease_id='lease-1', intent='scan mainline', session_id='S1'))
    context = payload['_command_context']
    assert context['actor_id'] == 'alice'
    assert context['workspace'] == 'desktop'
    assert context['lease_id'] == 'lease-1'
    assert context['profile'] == 'research'
