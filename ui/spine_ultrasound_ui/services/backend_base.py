from __future__ import annotations

from typing import Optional

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope


class BackendBase:
    def status(self) -> dict:
        return {}

    def health(self) -> dict:
        return {}

    def link_snapshot(self) -> dict:
        return {}

    def start(self) -> None:
        raise NotImplementedError

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        raise NotImplementedError

    def send_command(self, command: str, payload: Optional[dict] = None, *, context: Optional[dict] = None) -> ReplyEnvelope:
        raise NotImplementedError

    def close(self) -> None:
        return None

    def resolve_final_verdict(self, plan=None, config: Optional[RuntimeConfig] = None, *, read_only: bool) -> dict:
        """Return the canonical authoritative runtime verdict surface.

        Args:
            plan: Optional scan plan used when ``read_only`` is ``False``.
            config: Optional runtime configuration snapshot used for compilation.
            read_only: Query the read-only runtime-owned verdict when ``True``;
                trigger compile-time validation when ``False``.

        Returns:
            Runtime-owned final verdict payload or an empty dictionary when the
            backend cannot currently provide one.
        """
        return {}

    def query_final_verdict_snapshot(self) -> dict:
        return self.resolve_final_verdict(read_only=True)

    def compile_final_verdict(self, plan=None, config: Optional[RuntimeConfig] = None) -> dict:
        return self.resolve_final_verdict(plan, config, read_only=False)

    def get_final_verdict(self, plan=None, config: Optional[RuntimeConfig] = None) -> dict:
        return self.compile_final_verdict(plan, config)
