from __future__ import annotations

"""Read-only governance query surface.

This surface keeps governance-projection reads out of broader control-plane and
UI façades so consumers depend on a dedicated runtime-query interface rather
than a generic service object with mixed responsibilities.
"""

from typing import Any, Mapping

from spine_ultrasound_ui.services.runtime_governance_projection_service import RuntimeGovernanceProjectionService


class RuntimeGovernanceQuerySurface:
    """Dedicated read-only surface for runtime governance projections."""

    def __init__(self, projection_service: RuntimeGovernanceProjectionService | None = None) -> None:
        self._projection_service = projection_service or RuntimeGovernanceProjectionService()

    def build_projection(
        self,
        *,
        backend_link: Mapping[str, Any] | None = None,
        control_plane_snapshot: Mapping[str, Any] | None = None,
        model_report: Mapping[str, Any] | None = None,
        sdk_runtime: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the canonical governance projection for read consumers."""
        return self._projection_service.build_projection(
            backend_link=backend_link,
            control_plane_snapshot=control_plane_snapshot,
            model_report=model_report,
            sdk_runtime=sdk_runtime,
        )

    def resolve_control_authority(
        self,
        *,
        backend_link: Mapping[str, Any] | None = None,
        control_plane_snapshot: Mapping[str, Any] | None = None,
        authoritative_runtime_envelope: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve the canonical control-authority snapshot for read consumers."""
        return self._projection_service.resolve_control_authority(
            backend_link=backend_link,
            control_plane_snapshot=control_plane_snapshot,
            authoritative_runtime_envelope=authoritative_runtime_envelope,
        )

    def resolve_final_verdict(
        self,
        *,
        backend_link: Mapping[str, Any] | None = None,
        control_plane_snapshot: Mapping[str, Any] | None = None,
        model_report: Mapping[str, Any] | None = None,
        sdk_runtime: Mapping[str, Any] | None = None,
        authoritative_runtime_envelope: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Resolve the canonical final verdict for read consumers."""
        return self._projection_service.resolve_final_verdict(
            backend_link=backend_link,
            control_plane_snapshot=control_plane_snapshot,
            model_report=model_report,
            sdk_runtime=sdk_runtime,
            authoritative_runtime_envelope=authoritative_runtime_envelope,
        )
