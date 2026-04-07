from __future__ import annotations

from typing import Any


class LineageBuilder:
    """Build lineage payloads via the existing façade helper methods."""

    def build(self, service, *, session_id: str, manifest: dict[str, Any], scan_plan: dict[str, Any], command_journal: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, Any]:
        """Delegate lineage generation to the canonical service implementation.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            manifest: Session manifest payload.
            scan_plan: Frozen scan-plan payload.
            command_journal: Parsed command journal rows.
            report: Session report payload.

        Returns:
            Materialized lineage document.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_lineage(session_id, manifest, scan_plan, command_journal, report)
