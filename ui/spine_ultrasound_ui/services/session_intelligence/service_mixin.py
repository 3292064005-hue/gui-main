from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.session_intelligence.io_helpers import read_json, read_jsonl, write_json
from spine_ultrasound_ui.services.session_intelligence.lineage_recovery_helpers import (
    build_event_log_index,
    build_lineage,
    build_operator_incident_report,
    build_recovery_decision_timeline,
    build_recovery_report,
)
from spine_ultrasound_ui.services.session_intelligence.observability_helpers import (
    build_artifact_registry_snapshot,
    build_bridge_observability_report,
    build_control_authority_snapshot,
    build_control_plane_snapshot,
    build_event_delivery_summary,
    build_resume_attempts,
    build_resume_state,
)


class SessionIntelligenceServiceMixin:
    def _build_lineage(self, session_id: str, manifest: dict[str, Any], scan_plan: dict[str, Any], journal: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, Any]:
        return build_lineage(session_id, manifest, scan_plan, journal, report)

    def _build_recovery_report(self, session_id: str, journal: list[dict[str, Any]], annotations: list[dict[str, Any]], alarms: dict[str, Any]) -> dict[str, Any]:
        return build_recovery_report(session_id, journal, annotations, alarms)

    def _build_resume_state(self, session_id: str, manifest: dict[str, Any], scan_plan: dict[str, Any], journal: list[dict[str, Any]], recovery_report: dict[str, Any], integrity: dict[str, Any], incidents: dict[str, Any]) -> dict[str, Any]:
        return build_resume_state(session_id, manifest, scan_plan, journal, recovery_report, integrity, incidents)

    def _build_resume_attempts(self, session_id: str, journal: list[dict[str, Any]], resume_decision: dict[str, Any]) -> dict[str, Any]:
        return build_resume_attempts(session_id, journal, resume_decision)

    def _build_control_plane_snapshot(self, session_id: str, summary: dict[str, Any], release_gate_decision: dict[str, Any], contract_consistency: dict[str, Any], evidence_seal: dict[str, Any]) -> dict[str, Any]:
        return build_control_plane_snapshot(session_id, summary, release_gate_decision, contract_consistency, evidence_seal)

    def _build_control_authority_snapshot(self, session_id: str, summary: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
        return build_control_authority_snapshot(session_id, summary, manifest)

    def _build_bridge_observability_report(self, session_id: str, summary: dict[str, Any], event_delivery_summary: dict[str, Any]) -> dict[str, Any]:
        return build_bridge_observability_report(session_id, summary, event_delivery_summary)

    def _build_artifact_registry_snapshot(self, session_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
        return build_artifact_registry_snapshot(session_id, manifest)

    def _build_event_delivery_summary(self, session_id: str, event_log_index: dict[str, Any], resume_attempt_outcomes: dict[str, Any], contract_consistency: dict[str, Any]) -> dict[str, Any]:
        return build_event_delivery_summary(session_id, event_log_index, resume_attempt_outcomes, contract_consistency)

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        write_json(path, payload)

    def _build_recovery_decision_timeline(self, session_id: str, recovery_report: dict[str, Any], resume_decision: dict[str, Any]) -> dict[str, Any]:
        return build_recovery_decision_timeline(session_id, recovery_report, resume_decision)

    def _build_event_log_index(self, session_id: str, command_journal: list[dict[str, Any]], alarms: dict[str, Any], annotations: list[dict[str, Any]], recovery_report: dict[str, Any], resume_decision: dict[str, Any]) -> dict[str, Any]:
        return build_event_log_index(self, session_id, command_journal, alarms, annotations, recovery_report, resume_decision)

    def _build_operator_incident_report(self, session_id: str, annotations: list[dict[str, Any]], alarms: dict[str, Any]) -> dict[str, Any]:
        return build_operator_incident_report(session_id, annotations, alarms)

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return read_json(path)

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        return read_jsonl(path)
