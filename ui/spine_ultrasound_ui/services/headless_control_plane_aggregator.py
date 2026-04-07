from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.backend_authoritative_contract_service import BackendAuthoritativeContractService
from spine_ultrasound_ui.services.backend_control_plane_service import BackendControlPlaneService
from spine_ultrasound_ui.services.control_plane_snapshot_service import ControlPlaneSnapshotService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService


class HeadlessControlPlaneAggregator:
    """Compatibility façade for headless control-plane assembly.

    The public build signature is preserved. Internally the aggregator now emits
    a normalized authoritative runtime envelope so all backend surfaces consume
    the same authority/freeze/verdict facts.
    """

    def __init__(
        self,
        backend_control_plane_service: BackendControlPlaneService | None = None,
        deployment_profile_service: DeploymentProfileService | None = None,
        control_plane_snapshot_service: ControlPlaneSnapshotService | None = None,
        authoritative_contract_service: BackendAuthoritativeContractService | None = None,
    ) -> None:
        self.backend_control_plane_service = backend_control_plane_service or BackendControlPlaneService()
        self.deployment_profile_service = deployment_profile_service or DeploymentProfileService()
        self.control_plane_snapshot_service = control_plane_snapshot_service or ControlPlaneSnapshotService()
        self.authoritative_contract_service = authoritative_contract_service or BackendAuthoritativeContractService()

    def build(
        self,
        *,
        local_config: RuntimeConfig,
        runtime_config: dict[str, Any],
        schema: dict[str, Any],
        status: dict[str, Any],
        health: dict[str, Any],
        topic_catalog: dict[str, Any],
        recent_commands: list[dict[str, Any]],
        control_authority: dict[str, Any],
        session_governance: dict[str, Any] | None = None,
        evidence_seal: dict[str, Any] | None = None,
        authoritative_runtime_envelope: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Build the headless control-plane summary.

        Args:
            local_config: Desktop/headless desired runtime config.
            runtime_config: Runtime config payload from the adapter surface.
            schema: Protocol/schema metadata payload.
            status: Status payload.
            health: Health payload.
            topic_catalog: Topic catalog payload.
            recent_commands: Recent command window.
            control_authority: Current control-authority snapshot.
            session_governance: Optional session-governance payload.
            evidence_seal: Optional evidence seal payload.
            authoritative_runtime_envelope: Optional pre-built authoritative
                runtime envelope. When absent, it is derived from the other
                inputs using the shared normalization service.
        """
        deployment_profile = self.deployment_profile_service.build_snapshot(local_config)
        normalized_authoritative_envelope = self.authoritative_contract_service.normalize_payload(
            authoritative_runtime_envelope
            or {
                "control_authority": control_authority,
                "runtime_config": runtime_config,
            },
            authority_source="headless_control_plane",
            desired_runtime_config=local_config,
            fallback_control_authority=control_authority,
        )
        canonical_authority = dict(normalized_authoritative_envelope.get("control_authority", control_authority))
        applied_runtime_config = dict(normalized_authoritative_envelope.get("runtime_config_applied", runtime_config))
        control_plane = self.backend_control_plane_service.build(
            local_config=local_config,
            runtime_config=applied_runtime_config,
            schema=schema,
            status=status,
            health=health,
            topic_catalog=topic_catalog,
            recent_commands=recent_commands,
            control_authority=canonical_authority,
        )
        control_plane["authoritative_runtime_envelope"] = normalized_authoritative_envelope
        control_plane["runtime_config_applied"] = applied_runtime_config
        control_plane["final_verdict"] = dict(normalized_authoritative_envelope.get("final_verdict", {}))
        control_plane["session_freeze"] = dict(normalized_authoritative_envelope.get("session_freeze", {}))
        control_plane["plan_digest"] = dict(normalized_authoritative_envelope.get("plan_digest", {}))
        backend_link = {
            "summary_state": control_plane.get("summary_state", "unknown"),
            "summary_label": control_plane.get("summary_label", "control plane"),
            "detail": control_plane.get("detail", ""),
            "blockers": control_plane.get("blockers", []),
            "warnings": control_plane.get("warnings", []),
            "telemetry_stale": bool(health.get("telemetry_stale", False)),
            "latest_telemetry_age_ms": health.get("latest_telemetry_age_ms"),
            "control_plane": control_plane,
        }
        unified = self.control_plane_snapshot_service.build(
            backend_link=backend_link,
            control_authority=canonical_authority,
            deployment_profile=deployment_profile,
            bridge_observability={
                "summary_state": "blocked" if bool(health.get("telemetry_stale", False)) else "ready",
                "summary_label": "bridge observability" if not bool(health.get("telemetry_stale", False)) else "bridge stale",
                "detail": f"latest_telemetry_age_ms={health.get('latest_telemetry_age_ms', 'unknown')}",
            },
            session_governance=session_governance,
            evidence_seal=evidence_seal,
            release_mode=deployment_profile.get("name", "dev"),
        )
        control_plane.setdefault("projection_revision", unified.get("projection_revision"))
        control_plane.setdefault("projection_partitions", unified.get("projection_partitions", {}))
        return {**control_plane, "deployment_profile": deployment_profile, "unified_snapshot": unified, "control_plane_snapshot": unified}
