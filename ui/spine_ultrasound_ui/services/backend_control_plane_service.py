from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.control_plane_raw_facts_service import ControlPlaneRawFactsService


class BackendControlPlaneService(ControlPlaneRawFactsService):
    """Backward-compatible façade over the raw control-plane fact builder."""

    def build(
        self,
        *,
        local_config: RuntimeConfig,
        runtime_config: dict[str, Any] | None = None,
        schema: dict[str, Any] | None = None,
        status: dict[str, Any] | None = None,
        health: dict[str, Any] | None = None,
        topic_catalog: dict[str, Any] | None = None,
        recent_commands: list[dict[str, Any]] | None = None,
        control_authority: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        return super().build(
            local_config=local_config,
            runtime_config=runtime_config,
            schema=schema,
            status=status,
            health=health,
            topic_catalog=topic_catalog,
            recent_commands=recent_commands,
            control_authority=control_authority,
        )
