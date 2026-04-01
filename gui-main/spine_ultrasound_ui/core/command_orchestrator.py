from __future__ import annotations

import os
import socket
from typing import Any

from spine_ultrasound_ui.core.session_service import SessionService
from spine_ultrasound_ui.services.backend_base import BackendBase
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.utils import now_ns

class CommandOrchestrator:
    def __init__(self, backend: BackendBase, session_service: SessionService) -> None:
        self.backend = backend
        self.session_service = session_service
        self.actor_id = os.getenv("SPINE_ACTOR_ID", f"desktop-{socket.gethostname()}")
        self.workspace = os.getenv("SPINE_WORKSPACE", "desktop")
        self.role = os.getenv("SPINE_ROLE", "operator")

    def execute(self, command: str, payload: dict[str, Any] | None = None, *, workflow_step: str, auto_action: str = "", intent_reason: str | None = None, source: str = "desktop") -> ReplyEnvelope:
        request_payload = dict(payload or {})
        context = {
            "actor_id": self.actor_id,
            "workspace": self.workspace,
            "role": self.role,
            "session_id": getattr(self.session_service.current_experiment, "session_id", "") if self.session_service.current_experiment else "",
            "intent_reason": intent_reason or workflow_step or command,
            "source": source,
        }
        try:
            reply = self.backend.send_command(command, request_payload, context=context)
        except TypeError:
            request_payload.setdefault("_command_context", dict(context))
            reply = self.backend.send_command(command, request_payload)
        self.session_service.record_command_journal(
            source=source,
            command=command,
            payload=request_payload,
            reply={
                "ok": reply.ok,
                "message": reply.message,
                "request_id": reply.request_id,
                "data": dict(reply.data),
                "ts_ns": now_ns(),
            },
            workflow_step=workflow_step,
            auto_action=auto_action,
        )
        return reply
