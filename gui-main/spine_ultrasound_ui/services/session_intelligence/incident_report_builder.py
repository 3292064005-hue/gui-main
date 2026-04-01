from __future__ import annotations

from typing import Any


class IncidentReportBuilder:
    """Build event-delivery and observability products."""

    def build_event_log_index(self, service, *, session_id: str, command_journal: list[dict[str, Any]], alarms: dict[str, Any], annotations: list[dict[str, Any]], recovery_report: dict[str, Any], resume_decision: dict[str, Any]) -> dict[str, Any]:
        """Build the event log index.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            command_journal: Parsed command journal rows.
            alarms: Alarm timeline payload.
            annotations: Parsed annotation rows.
            recovery_report: Recovery-report payload.
            resume_decision: Resume decision payload.

        Returns:
            Event-log index document.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_event_log_index(session_id, command_journal, alarms, annotations, recovery_report, resume_decision)

    def build_recovery_timeline(self, service, *, session_id: str, recovery_report: dict[str, Any], resume_decision: dict[str, Any]) -> dict[str, Any]:
        """Build the recovery decision timeline.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            recovery_report: Recovery-report payload.
            resume_decision: Resume decision payload.

        Returns:
            Recovery-timeline document.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_recovery_decision_timeline(session_id, recovery_report, resume_decision)

    def build_bridge_observability(self, service, *, session_id: str, summary: dict[str, Any], event_delivery_summary: dict[str, Any]) -> dict[str, Any]:
        """Build bridge-observability output.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            summary: Summary payload.
            event_delivery_summary: Event-delivery summary payload.

        Returns:
            Bridge-observability report.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_bridge_observability_report(session_id, summary, event_delivery_summary)
