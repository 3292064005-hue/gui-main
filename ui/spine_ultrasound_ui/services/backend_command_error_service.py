from __future__ import annotations

from typing import Any

from .backend_error_mapper import BackendErrorMapper
from .backend_errors import BackendOperationError, normalize_backend_exception
from .ipc_protocol import ReplyEnvelope


class BackendCommandErrorService:
    """Normalize command-path exceptions into typed backend replies."""

    @staticmethod
    def build_reply(exc: Exception, *, command: str, context: str, data: dict[str, Any] | None = None) -> tuple[BackendOperationError, ReplyEnvelope]:
        normalized = normalize_backend_exception(exc, command=command, context=context)
        reply = BackendErrorMapper.reply_from_exception(normalized, data=data, command=command, context=context)
        return normalized, reply
