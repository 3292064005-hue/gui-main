from __future__ import annotations

from typing import Any


class ReleaseArtifactBuilder:
    """Build control-plane and artifact-registry release products."""

    def build_control_plane_snapshot(self, service, *, session_id: str, summary: dict[str, Any], release_gate_decision: dict[str, Any], contract_consistency: dict[str, Any], evidence_seal: dict[str, Any]) -> dict[str, Any]:
        """Build the control-plane snapshot.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            summary: Summary payload.
            release_gate_decision: Release gate payload.
            contract_consistency: Contract consistency payload.
            evidence_seal: Evidence-seal payload.

        Returns:
            Control-plane snapshot document.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_control_plane_snapshot(session_id, summary, release_gate_decision, contract_consistency, evidence_seal)

    def build_control_authority_snapshot(self, service, *, session_id: str, summary: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
        """Build the control-authority snapshot.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            summary: Summary payload.
            manifest: Session manifest payload.

        Returns:
            Control-authority snapshot document.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_control_authority_snapshot(session_id, summary, manifest)

    def build_artifact_registry_snapshot(self, service, *, session_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        """Build the artifact-registry snapshot.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            manifest: Session manifest payload.

        Returns:
            Artifact-registry snapshot document.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_artifact_registry_snapshot(session_id, manifest)
