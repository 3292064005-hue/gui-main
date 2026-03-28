from __future__ import annotations

from typing import Optional

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope


class BackendBase:
    def start(self) -> None:
        raise NotImplementedError

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        raise NotImplementedError

    def send_command(self, command: str, payload: Optional[dict] = None) -> ReplyEnvelope:
        raise NotImplementedError

    def close(self) -> None:
        return None
