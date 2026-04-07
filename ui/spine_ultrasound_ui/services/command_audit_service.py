from __future__ import annotations

from collections import deque
from typing import Any

from spine_ultrasound_ui.core.command_journal import summarize_command_payload
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.utils import now_ns

RECENT_COMMAND_HISTORY_LIMIT = 20
RECENT_COMMAND_VIEW_LIMIT = 12


class CommandAuditService:
    """Persist operator-visible command history and journals.

    Args:
        remember_recent_command: Callback used to update the broader runtime cache.
        record_command_journal: Callback used to persist the command journal.

    Returns:
        None.

    Raises:
        No exceptions are raised during construction.
    """

    def __init__(self, *, remember_recent_command: Any, record_command_journal: Any) -> None:
        self._remember_recent_command = remember_recent_command
        self._record_command_journal = record_command_journal
        self._recent_commands: deque[dict[str, Any]] = deque(maxlen=RECENT_COMMAND_HISTORY_LIMIT)

    def recent_commands(self, *, mode: str) -> dict[str, Any]:
        """Return a bounded operator-facing command history view.

        Args:
            mode: Current backend mode.

        Returns:
            Dictionary containing the recent command window and backend mode.

        Raises:
            No exceptions are raised.
        """
        items = list(self._recent_commands)
        return {"recent_commands": items[-RECENT_COMMAND_VIEW_LIMIT:], "backend_mode": mode}

    def remember_recent_command_local(self, command: str, payload: dict[str, Any], reply: ReplyEnvelope) -> None:
        """Store one bounded local command-history record.

        Args:
            command: Canonical command name.
            payload: Command payload.
            reply: Runtime reply envelope.

        Returns:
            None.

        Raises:
            No exceptions are raised.
        """
        context = dict((payload or {}).get("_command_context", {}))
        record = {
            "command": command,
            "payload": summarize_command_payload(payload),
            "ok": bool(reply.ok),
            "message": str(reply.message),
            "request_id": str(reply.request_id),
            "ts_ns": now_ns(),
            "actor_id": str(context.get("actor_id", "")),
            "workspace": str(context.get("workspace", "")),
            "lease_id": str(context.get("lease_id", "")),
            "session_id": str(context.get("session_id", "")),
            "intent": str(context.get("intent", "")),
            "profile": str(context.get("profile", "")),
        }
        self._recent_commands.append(record)
        self._remember_recent_command(command, payload, reply)

    def record_journal(self, command: str, payload: dict[str, Any], reply: ReplyEnvelope) -> None:
        """Persist a journal record through the configured callback.

        Args:
            command: Canonical command name.
            payload: Command payload.
            reply: Runtime reply envelope.

        Returns:
            None.

        Raises:
            Any exception raised by the journal callback is propagated.
        """
        self._record_command_journal(command, payload, reply)
