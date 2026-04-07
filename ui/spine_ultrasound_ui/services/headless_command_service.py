from __future__ import annotations

from typing import Any, Callable

from spine_ultrasound_ui.services.command_audit_service import CommandAuditService
from spine_ultrasound_ui.services.command_dispatch_service import CommandDispatchService
from spine_ultrasound_ui.services.command_guard_service import CommandGuardService
from spine_ultrasound_ui.services.ipc_protocol import COMMANDS, ReplyEnvelope, is_write_command, validate_command_payload


class HeadlessCommandService:
    """Façade for command validation, authority gating, dispatch, and audit."""

    def __init__(
        self,
        *,
        mode: str,
        runtime: Any,
        ssl_context: Any,
        command_host: str,
        command_port: int,
        control_authority: Any,
        current_session_id: Callable[[], str],
        prepare_session_tracking: Callable[[str, dict[str, Any]], None],
        clear_current_session: Callable[[], None],
        remember_recent_command: Callable[[str, dict[str, Any], ReplyEnvelope], None],
        record_command_journal: Callable[[str, dict[str, Any], ReplyEnvelope], None],
        store_runtime_messages: Callable[[list[Any]], None],
        deployment_profile_snapshot: Callable[[], dict[str, Any]],
        control_plane_snapshot: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.mode = mode
        self.control_authority = control_authority
        self.current_session_id = current_session_id
        self.prepare_session_tracking = prepare_session_tracking
        self.clear_current_session = clear_current_session
        self._guard = CommandGuardService(
            control_authority=control_authority,
            current_session_id=current_session_id,
            deployment_profile_snapshot=deployment_profile_snapshot,
            backend_mode_snapshot=lambda: mode,
            control_plane_snapshot=control_plane_snapshot,
        )
        self._dispatch = CommandDispatchService(
            mode=mode,
            runtime=runtime,
            ssl_context=ssl_context,
            command_host=command_host,
            command_port=command_port,
            store_runtime_messages=store_runtime_messages,
        )
        self._audit = CommandAuditService(
            remember_recent_command=remember_recent_command,
            record_command_journal=record_command_journal,
        )

    def reply_dict(self, reply: ReplyEnvelope) -> dict[str, Any]:
        return {
            "ok": reply.ok,
            "message": reply.message,
            "request_id": reply.request_id,
            "data": dict(reply.data),
            "protocol_version": reply.protocol_version,
        }

    def recent_commands(self) -> dict[str, Any]:
        return self._audit.recent_commands(mode=self.mode)

    def _remember_and_return(self, command: str, payload: dict[str, Any], reply: ReplyEnvelope) -> dict[str, Any]:
        self._audit.remember_recent_command_local(command, payload, reply)
        self._audit.record_journal(command, payload, reply)
        return self.reply_dict(reply)

    def command(self, command: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        """Validate and dispatch a headless runtime command.

        Args:
            command: Canonical command name.
            payload: Optional payload mapping.

        Returns:
            Serialized reply envelope suitable for API delivery.

        Raises:
            ValueError: If the command is not registered.
        """
        if command not in COMMANDS:
            raise ValueError(f"unsupported command: {command}")
        requested_payload = dict(payload or {})
        validate_command_payload(command, requested_payload)
        if is_write_command(command):
            normalized_payload, blocked_reply = self._guard.guard_write_command(command, requested_payload)
            if blocked_reply is not None:
                return self._remember_and_return(command, normalized_payload, blocked_reply)
        else:
            normalized_payload = requested_payload
        self.prepare_session_tracking(command, normalized_payload)
        reply = self._dispatch.dispatch(command, normalized_payload)
        if reply.ok and command == "lock_session":
            self.control_authority.bind_session(str(normalized_payload.get("session_id", self.current_session_id())))
        if not reply.ok and command == "lock_session":
            self.clear_current_session()
        if command == "disconnect_robot" and reply.ok:
            self.control_authority.clear_session_binding()
            self.clear_current_session()
        return self._remember_and_return(command, normalized_payload, reply)
