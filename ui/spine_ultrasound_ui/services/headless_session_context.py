from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.core.command_journal import summarize_command_payload
from spine_ultrasound_ui.core.session_recorders import JsonlRecorder
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.utils import now_ns


class HeadlessSessionContext:
    def __init__(self) -> None:
        self.current_session_dir: Path | None = None
        self.current_session_id = ""
        self.command_journal: JsonlRecorder | None = None

    def prepare_session_tracking(self, command: str, payload: dict[str, Any]) -> None:
        if command != "lock_session":
            return
        session_dir = payload.get("session_dir")
        session_id = payload.get("session_id", "")
        if not isinstance(session_dir, str) or not session_dir:
            return
        self.current_session_dir = Path(session_dir)
        self.current_session_id = str(session_id)
        self.command_journal = JsonlRecorder(self.current_session_dir / "raw" / "ui" / "command_journal.jsonl", self.current_session_id or "headless")

    def record_command_journal(self, command: str, payload: dict[str, Any], reply: ReplyEnvelope) -> None:
        if self.command_journal is None:
            return
        self.command_journal.append_event(
            {
                "ts_ns": now_ns(),
                "source": "headless",
                "command": command,
                "workflow_step": command,
                "auto_action": "",
                "payload_summary": summarize_command_payload(payload),
                "reply": {
                    "ok": reply.ok,
                    "message": reply.message,
                    "request_id": reply.request_id,
                    "data": dict(reply.data),
                },
            }
        )

    def resolve_session_dir(self, runtime_session_dir: Path | None = None) -> Path | None:
        if self.current_session_dir is not None:
            return self.current_session_dir
        return runtime_session_dir

    def require_session_dir(self, runtime_session_dir: Path | None = None) -> Path:
        session_dir = self.resolve_session_dir(runtime_session_dir)
        if session_dir is None:
            raise FileNotFoundError("no active session")
        return session_dir

    def clear_current_session(self) -> None:
        self.current_session_dir = None
        self.current_session_id = ""
        self.command_journal = None

    @staticmethod
    def read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            raise FileNotFoundError(path.name)
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def read_json_if_exists(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def read_manifest_if_available(self, session_dir: Path | None = None) -> dict[str, Any]:
        session_dir = session_dir or self.current_session_dir
        if session_dir is None:
            return {}
        manifest_path = session_dir / "meta" / "manifest.json"
        if manifest_path.exists():
            try:
                return json.loads(manifest_path.read_text(encoding="utf-8"))
            except Exception:
                return {}
        return {
            "session_id": self.current_session_id or session_dir.name,
            "artifacts": {},
            "artifact_registry": {},
            "processing_steps": [],
        }

    @staticmethod
    def derive_recovery_state(core: dict[str, Any]) -> str:
        execution_state = str(core.get("execution_state", "BOOT"))
        if execution_state == "ESTOP":
            return "ESTOP_LATCHED"
        if execution_state == "FAULT":
            return "CONTROLLED_RETRACT"
        if execution_state == "PAUSED_HOLD":
            return "HOLDING"
        if execution_state in {"RETREATING", "SCAN_COMPLETE"}:
            return "RETRY_READY"
        return "IDLE"
