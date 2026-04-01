from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.services.backend_errors import normalize_backend_exception
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope


class BackendErrorMapper:
    @staticmethod
    def reply_from_exception(
        exc: Exception,
        *,
        request_id: str = "",
        data: dict[str, Any] | None = None,
        command: str = "",
        context: str = "",
    ) -> ReplyEnvelope:
        normalized = normalize_backend_exception(exc, command=command, context=context)
        payload = {
            "error_type": normalized.error_type,
            "http_status": normalized.http_status,
            "retryable": normalized.retryable,
            **dict(normalized.data),
            **dict(data or {}),
        }
        return ReplyEnvelope(
            ok=False,
            message=normalized.message,
            request_id=request_id,
            data=payload,
        )
