from __future__ import annotations

from typing import Any


class RecoveryReportBuilder:
    """Materialize recovery and operator-incident artifacts."""

    def build_recovery_report(self, service, *, session_id: str, command_journal: list[dict[str, Any]], annotations: list[dict[str, Any]], alarms: dict[str, Any]) -> dict[str, Any]:
        """Build the recovery report.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            command_journal: Parsed command journal rows.
            annotations: Parsed annotation rows.
            alarms: Alarm timeline payload.

        Returns:
            Recovery-report document.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_recovery_report(session_id, command_journal, annotations, alarms)

    def build_operator_incident_report(self, service, *, session_id: str, annotations: list[dict[str, Any]], alarms: dict[str, Any]) -> dict[str, Any]:
        """Build the operator incident report.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            annotations: Parsed annotation rows.
            alarms: Alarm timeline payload.

        Returns:
            Operator incident report.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_operator_incident_report(session_id, annotations, alarms)
