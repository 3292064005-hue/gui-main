from __future__ import annotations

"""Assemble backend control-plane projections from authoritative runtime facts."""

from typing import Any


class BackendControlPlaneProjectionService:
    """Merge control-plane caches with authoritative runtime envelopes.

    This service keeps link-snapshot assembly out of transport façades so both
    API and direct-core backends consume the same merge rules.
    """

    def build(self, *, control_plane: dict[str, Any], authoritative_envelope: dict[str, Any], projection_cache: Any, control_authority: dict[str, Any] | None = None) -> dict[str, Any]:
        """Build a merged control-plane payload.

        Args:
            control_plane: Backend-specific control-plane cache.
            authoritative_envelope: Runtime-owned authoritative envelope.
            projection_cache: Projection cache used to surface revision metadata.
            control_authority: Optional cached authority payload used only when
                the authoritative envelope is still incomplete.

        Returns:
            A merged control-plane dictionary suitable for link snapshots.

        Raises:
            No exceptions are raised.
        """
        merged = dict(control_plane or {})
        if control_authority:
            merged.setdefault("control_authority", dict(control_authority))
        if authoritative_envelope:
            merged["authoritative_runtime_envelope"] = dict(authoritative_envelope)
            merged.setdefault("control_authority", dict(authoritative_envelope.get("control_authority", {})))
            merged["runtime_config_applied"] = dict(authoritative_envelope.get("runtime_config_applied", {}))
            merged["final_verdict"] = dict(authoritative_envelope.get("final_verdict", {}))
            merged["session_freeze"] = dict(authoritative_envelope.get("session_freeze", {}))
            merged["plan_digest"] = dict(authoritative_envelope.get("plan_digest", {}))
            merged["write_capabilities"] = dict(authoritative_envelope.get("write_capabilities", {}))
        projection_snapshot = projection_cache.snapshot()
        merged["projection_revision"] = projection_snapshot["revision"]
        merged["projection_partitions"] = projection_snapshot["partitions"]
        return merged
