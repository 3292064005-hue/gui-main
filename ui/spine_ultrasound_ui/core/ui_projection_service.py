from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.core.view_state_factory import ViewStateFactory
from spine_ultrasound_ui.models import RuntimeConfig, WorkflowArtifacts
from spine_ultrasound_ui.services.runtime_governance_query_surface import RuntimeGovernanceQuerySurface
from spine_ultrasound_ui.utils import now_text

class UiProjectionService:
    def __init__(self, view_factory: ViewStateFactory, governance_projection: RuntimeGovernanceQuerySurface | None = None):
        self.view_factory = view_factory
        self.governance_projection = governance_projection or RuntimeGovernanceQuerySurface()

    def build_status_payload(self, *, telemetry, config: RuntimeConfig, workflow_artifacts: WorkflowArtifacts, current_experiment, persistence: dict[str, Any], sdk_runtime: dict[str, Any], model_report: dict[str, Any], config_report: dict[str, Any], backend_link: dict[str, Any], bridge_observability: dict[str, Any], session_governance: dict[str, Any], deployment_profile: dict[str, Any], control_plane_snapshot: dict[str, Any]) -> dict[str, Any]:
        governance_projection = self.governance_projection.build_projection(
            backend_link=backend_link,
            control_plane_snapshot=control_plane_snapshot,
            model_report=model_report,
            sdk_runtime=sdk_runtime,
        )
        payload = self.view_factory.build(telemetry, config, workflow_artifacts, current_experiment, sdk_runtime=sdk_runtime, model_report=model_report, config_report=config_report, backend_link=backend_link, bridge_observability=bridge_observability, control_plane_snapshot={**dict(control_plane_snapshot), "authoritative_projection": governance_projection}).to_dict()
        payload["persistence"] = persistence
        payload["config_report"] = dict(config_report)
        payload["session_governance"] = dict(session_governance)
        payload["backend_link"] = dict(backend_link)
        payload["control_authority"] = dict(governance_projection.get("control_authority", control_plane_snapshot.get("ownership_state", {})))
        payload["final_verdict"] = dict(governance_projection.get("final_verdict", {}))
        payload["authoritative_projection"] = dict(governance_projection)
        payload["bridge_observability"] = dict(bridge_observability)
        payload["deployment_profile"] = dict(deployment_profile)
        payload["control_plane_snapshot"] = dict(control_plane_snapshot)
        return payload

    def build_governance_payload(self, *, status_payload: dict[str, Any]) -> dict[str, Any]:
        payload = dict(status_payload)
        payload["generated_at"] = now_text()
        return payload
