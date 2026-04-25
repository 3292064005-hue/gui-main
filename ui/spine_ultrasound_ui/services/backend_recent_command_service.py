from __future__ import annotations

"""Bounded recent-command tracking for backend façades."""

from collections import deque
from typing import Any

from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.services.runtime_command_catalog import canonical_command_name, command_alias_kind


class BackendRecentCommandService:
    """Track recent backend commands and keep projection-cache state aligned.

    Args:
        projection_cache: Cache updated whenever the recent-command window changes.
        limit: Maximum number of entries retained in memory.
    """

    def __init__(self, *, projection_cache: Any, limit: int) -> None:
        self._projection_cache = projection_cache
        self._items: deque[dict[str, Any]] = deque(maxlen=max(1, int(limit)))

    def remember(self, command: str, reply: ReplyEnvelope) -> dict[str, Any]:
        """Store one compatibility-friendly recent-command entry.

        Args:
            command: Requested command name.
            reply: Runtime reply envelope.

        Returns:
            The normalized entry stored in the bounded history.

        Raises:
            No exceptions are raised.
        """
        reply_data = dict(getattr(reply, "data", {}) or {})
        canonical = str(reply_data.get("canonical_command") or canonical_command_name(command) or command)
        entry = {
            "requested_command": command,
            "command": canonical,
            "canonical_command": canonical,
            "alias_kind": str(reply_data.get("alias_kind") or command_alias_kind(command) or "canonical"),
            "deprecated_alias": bool(reply_data.get("deprecated_alias", False)) or str(reply_data.get("alias_kind", "")).strip() == "deprecated_alias",
            "shim_only_alias": bool(reply_data.get("shim_only_alias", False)) or str(reply_data.get("alias_kind", "")).strip() == "shim_only",
            "ok": bool(reply.ok),
            "message": str(reply.message),
        }
        self._items.append(entry)
        self._projection_cache.update_partition("recent_commands", list(self._items))
        return dict(entry)

    def snapshot(self) -> list[dict[str, Any]]:
        """Return the current bounded recent-command window."""
        return list(self._items)
