from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope


class CommandGuardService:
    """Apply command-level validation and authority/deployment gating."""

    def __init__(self, *, control_authority: Any, current_session_id: Any, deployment_profile_snapshot: Any) -> None:
        self._control_authority = control_authority
        self._current_session_id = current_session_id
        self._deployment_profile_snapshot = deployment_profile_snapshot

    def guard_write_command(self, command: str, payload: dict[str, Any]) -> tuple[dict[str, Any], ReplyEnvelope | None]:
        """Validate authority and deployment restrictions for a write command.

        Args:
            command: Canonical command name.
            payload: Requested command payload.

        Returns:
            A tuple of normalized payload and optional early reply. When the
            reply is not ``None`` the caller must return it directly.
        """
        profile = self._deployment_profile_snapshot()
        authority_decision = self._control_authority.guard_command(
            command,
            payload,
            current_session_id=self._current_session_id(),
            source="headless",
        )
        normalized_payload = dict(authority_decision.get("normalized_payload", payload))
        allowed_roles = set(profile.get("allowed_write_roles", []))
        context = dict(normalized_payload.get("_command_context", {}))
        role = str(context.get("role", "")).strip().lower()
        if profile.get("review_only") or not profile.get("allows_write_commands", True):
            return normalized_payload, ReplyEnvelope(
                ok=False,
                message="当前部署 profile 为只读，禁止写命令。",
                data={"deployment_profile": profile},
            )
        if allowed_roles and role and role not in allowed_roles:
            return normalized_payload, ReplyEnvelope(
                ok=False,
                message=f"当前部署 profile 不允许角色 {role} 执行写命令。",
                data={"deployment_profile": profile},
            )
        if not authority_decision.get("allowed", False):
            return normalized_payload, ReplyEnvelope(
                ok=False,
                message=str(authority_decision.get("message", "控制权检查失败")),
                data={"control_authority": authority_decision.get("authority", {})},
            )
        return normalized_payload, None
