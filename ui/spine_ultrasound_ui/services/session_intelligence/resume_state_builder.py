from __future__ import annotations

from typing import Any


class ResumeStateBuilder:
    """Build resume-state and resume-attempt artifacts."""

    def build_resume_state(self, service, *, session_id: str, manifest: dict[str, Any], scan_plan: dict[str, Any], command_journal: list[dict[str, Any]], recovery_report: dict[str, Any], integrity: dict[str, Any], incidents: dict[str, Any]) -> dict[str, Any]:
        """Build the canonical resume-state document.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            manifest: Session manifest payload.
            scan_plan: Frozen scan-plan payload.
            command_journal: Parsed command journal rows.
            recovery_report: Recovery-report payload.
            integrity: Integrity payload.
            incidents: Incident summary payload.

        Returns:
            Resume-state document.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_resume_state(session_id, manifest, scan_plan, command_journal, recovery_report, integrity, incidents)

    def build_resume_attempts(self, service, *, session_id: str, command_journal: list[dict[str, Any]], resume_decision: dict[str, Any]) -> list[dict[str, Any]]:
        """Build normalized resume attempts.

        Args:
            service: ``SessionIntelligenceService`` façade instance.
            session_id: Locked session identifier.
            command_journal: Parsed command journal rows.
            resume_decision: Resume decision payload.

        Returns:
            Ordered resume-attempt records.

        Raises:
            RuntimeError: Propagated from the façade helper.
        """
        return service._build_resume_attempts(session_id, command_journal, resume_decision)
