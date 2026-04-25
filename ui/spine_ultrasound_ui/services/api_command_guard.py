from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from fastapi import HTTPException

from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.ipc_protocol import is_write_command
from spine_ultrasound_ui.services.runtime_command_catalog import is_retired_alias, retired_alias_rejection


@dataclass(frozen=True)
class ApiCommandHeaders:
    role: str | None = None
    actor: str | None = None
    workspace: str | None = None
    lease_id: str | None = None
    intent: str | None = None
    session_id: str | None = None
    api_token: str | None = None


class ApiCommandGuardService:
    """Normalizes write-command provenance and enforces profile-aware API policy."""

    def __init__(self, deployment_profile_service: DeploymentProfileService | None = None, env: dict[str, str] | None = None) -> None:
        self.deployment_profile_service = deployment_profile_service or DeploymentProfileService(env)
        self._env = env if env is not None else dict(os.environ)

    def normalize_payload(self, *, adapter: Any, command: str, payload: Any, headers: ApiCommandHeaders) -> dict[str, Any]:
        if payload is not None and not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be a JSON object")
        profile = self.deployment_profile_service.resolve(None)
        if is_retired_alias(command):
            raise HTTPException(status_code=410, detail=retired_alias_rejection(command))
        write_command = is_write_command(command)
        if write_command:
            raise HTTPException(status_code=403, detail='HTTP API is read-only evidence surface; use the desktop operator console for write commands')
        self._enforce_token(profile, headers.api_token)
        role = (headers.role or 'operator').strip().lower()
        self._enforce_role(adapter, role, command, profile, write_command=write_command)
        actor = (headers.actor or f'api-{role}').strip()
        workspace = (headers.workspace or role or 'operator').strip()
        intent = (headers.intent or command).strip()
        session_id = (headers.session_id or '').strip()
        lease_id = (headers.lease_id or '').strip()
        if profile.requires_strict_control_authority and not actor:
            raise HTTPException(status_code=400, detail='x-spine-actor is required in strict control profile')
        payload_dict = dict(payload or {})
        payload_dict.setdefault('_command_context', {
            'role': role,
            'actor_id': actor,
            'workspace': workspace,
            'lease_id': lease_id,
            'intent_reason': intent,
            'session_id': session_id,
            'source': 'http_api',
            'profile': profile.name,
        })
        return payload_dict

    def _enforce_token(self, profile, supplied: str | None) -> None:
        expected = str(self._env.get('SPINE_API_TOKEN', '')).strip()
        if profile.requires_api_token and expected and (supplied or '').strip() != expected:
            raise HTTPException(status_code=403, detail='missing or invalid API token for deployment profile')

    @staticmethod
    def _enforce_role(adapter: Any, role: str, command: str, profile, *, write_command: bool) -> None:
        role_catalog = getattr(adapter, 'role_matrix', None)
        if write_command:
            if role not in set(profile.allowed_write_roles):
                raise HTTPException(status_code=403, detail=f"role '{role}' is not allowed in profile '{profile.name}'")
            if role_catalog is not None and not role_catalog.can_issue_command(role, command):
                raise HTTPException(status_code=403, detail=f"role '{role}' is not allowed to issue write commands")
            if role_catalog is None and role != 'operator':
                raise HTTPException(status_code=403, detail=f"role '{role}' is not allowed to issue write commands")
            return
        if role_catalog is not None and not role_catalog.can_read_category(role, 'runtime'):
            raise HTTPException(status_code=403, detail=f"role '{role}' is not allowed to read runtime command contracts")
