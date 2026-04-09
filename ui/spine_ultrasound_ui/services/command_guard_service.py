from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope, is_write_command
from spine_ultrasound_ui.services.runtime_command_catalog import command_capability_claim


class CommandGuardService:
    """Apply command-level validation and authority/deployment gating."""

    def __init__(self, *, control_authority: Any, current_session_id: Any, deployment_profile_snapshot: Any, backend_mode_snapshot: Any, control_plane_snapshot: Any | None = None) -> None:
        self._control_authority = control_authority
        self._current_session_id = current_session_id
        self._deployment_profile_snapshot = deployment_profile_snapshot
        self._backend_mode_snapshot = backend_mode_snapshot
        self._control_plane_snapshot = control_plane_snapshot

    def _guard_with_authority(self, command: str, payload: dict[str, Any], *, require_lease: bool) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
        profile = self._deployment_profile_snapshot()
        try:
            authority_decision = self._control_authority.guard_command(
                command,
                payload,
                current_session_id=self._current_session_id(),
                source="headless",
                require_lease=require_lease,
            )
        except TypeError:
            authority_decision = self._control_authority.guard_command(
                command,
                payload,
                current_session_id=self._current_session_id(),
                source="headless",
            )
        normalized_payload = dict(authority_decision.get("normalized_payload", payload))
        return normalized_payload, authority_decision, profile

    def guard_command(self, command: str, payload: dict[str, Any]) -> tuple[dict[str, Any], ReplyEnvelope | None]:
        """Validate capability/ownership requirements and profile restrictions.

        Write commands require an active lease and must satisfy deployment write
        gates. Read-contract commands that still carry a non-runtime capability
        claim are checked through the authority surface without mutating lease
        ownership.
        """
        requires_lease = is_write_command(command)
        normalized_payload, authority_decision, profile = self._guard_with_authority(
            command,
            payload,
            require_lease=requires_lease,
        )
        if not authority_decision.get("allowed", False):
            return normalized_payload, ReplyEnvelope(
                ok=False,
                message=str(authority_decision.get("message", "控制权检查失败")),
                data={"control_authority": authority_decision.get("authority", {})},
            )
        if not requires_lease:
            return normalized_payload, None
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
        backend_mode = str(self._backend_mode_snapshot() or "")
        if profile.get("requires_live_sdk", False):
            if backend_mode != "core":
                return normalized_payload, ReplyEnvelope(
                    ok=False,
                    message="当前部署 profile 要求 live SDK / core backend，禁止在 mock/api-only 运行面执行写命令。",
                    data={"deployment_profile": profile, "backend_mode": backend_mode},
                )
            control_plane_snapshot = dict(self._control_plane_snapshot() or {}) if callable(self._control_plane_snapshot) else {}
            runtime_doctor = dict(control_plane_snapshot.get("runtime_doctor", {}))
            runtime_doctor_state = str(runtime_doctor.get("summary_state", "unknown"))
            blockers = [dict(item) for item in control_plane_snapshot.get("blockers", []) or []]
            runtime_blockers = [
                item
                for item in blockers
                if str(item.get("section", "")) in {"runtime_doctor", "vendor_boundary", "hardware_lifecycle", "rt_kernel", "mainline_executor"}
            ]
            if runtime_doctor_state == "blocked" or runtime_blockers:
                blocker = runtime_blockers[0] if runtime_blockers else {
                    "section": "runtime_doctor",
                    "name": runtime_doctor.get("summary_label", "runtime_doctor_blocked"),
                    "detail": runtime_doctor.get("detail", "运行主线治理阻塞"),
                }
                return normalized_payload, ReplyEnvelope(
                    ok=False,
                    message="当前部署 profile 要求 live SDK/mainline ready；runtime doctor 仍存在阻塞，禁止执行写命令。",
                    data={
                        "deployment_profile": profile,
                        "backend_mode": backend_mode,
                        "runtime_doctor": runtime_doctor,
                        "blocking_issue": blocker,
                    },
                )
        return normalized_payload, None

    def guard_write_command(self, command: str, payload: dict[str, Any]) -> tuple[dict[str, Any], ReplyEnvelope | None]:
        """Backward-compatible wrapper for write-command gating."""
        return self.guard_command(command, payload)
