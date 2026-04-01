from __future__ import annotations


def infer_source_stage(name: str) -> str:
    """Infer the producing stage for a session artifact.

    Args:
        name: Canonical artifact type name.

    Returns:
        Stable stage identifier used in the artifact registry.

    Raises:
        No exceptions are raised.
    """
    if name in {"scan_plan", "device_readiness"}:
        return "workflow_lock"
    if name in {"summary_json", "summary_text", "quality_feedback", "camera_index", "ultrasound_index", "command_journal", "annotations"}:
        return "capture"
    if name in {"quality_timeline", "alarm_timeline"}:
        return "preprocess"
    if name in {"frame_sync_index", "replay_index"}:
        return "reconstruction"
    if name in {
        "session_report", "session_compare", "session_trends", "diagnostics_pack", "qa_pack", "session_integrity",
        "lineage", "resume_state", "resume_decision", "resume_attempts", "resume_attempt_outcomes", "recovery_report",
        "operator_incident_report", "session_incidents", "event_log_index", "recovery_decision_timeline", "contract_consistency",
        "release_evidence_pack", "release_gate_decision", "command_state_policy", "event_delivery_summary",
        "selected_execution_rationale", "control_plane_snapshot", "control_authority_snapshot", "bridge_observability_report",
        "artifact_registry_snapshot", "session_evidence_seal",
    }:
        return "assessment"
    return "session_service"


_DEPENDENCY_MAP: dict[str, list[str]] = {
    "device_readiness": ["scan_plan"],
    "quality_timeline": ["quality_feedback"],
    "alarm_timeline": ["command_journal"],
    "frame_sync_index": ["quality_feedback", "camera_index", "ultrasound_index", "annotations"],
    "replay_index": ["alarm_timeline", "quality_timeline", "annotations", "frame_sync_index"],
    "session_report": ["summary_json", "replay_index", "quality_timeline", "alarm_timeline", "frame_sync_index"],
    "session_compare": ["session_report"],
    "session_trends": ["session_report", "diagnostics_pack"],
    "diagnostics_pack": ["command_journal", "alarm_timeline", "quality_timeline", "annotations"],
    "qa_pack": ["session_report", "replay_index", "quality_timeline", "alarm_timeline", "session_compare", "session_trends", "diagnostics_pack"],
    "session_integrity": ["scan_plan", "device_readiness", "xmate_profile", "patient_registration", "scan_protocol"],
    "lineage": ["scan_plan", "patient_registration", "command_journal", "session_report"],
    "resume_state": ["scan_plan", "command_journal", "session_integrity", "recovery_report"],
    "recovery_report": ["command_journal", "alarm_timeline", "annotations"],
    "operator_incident_report": ["annotations", "alarm_timeline"],
    "session_incidents": ["operator_incident_report", "recovery_report", "quality_timeline"],
    "resume_decision": ["resume_state", "session_incidents", "recovery_report", "session_integrity"],
    "event_log_index": ["command_journal", "alarm_timeline", "annotations", "recovery_report", "resume_decision"],
    "recovery_decision_timeline": ["recovery_report", "resume_decision"],
    "resume_attempts": ["resume_decision", "command_journal"],
    "resume_attempt_outcomes": ["resume_attempts", "resume_decision", "contract_consistency", "command_state_policy"],
    "command_state_policy": ["scan_plan"],
    "event_delivery_summary": ["event_log_index", "resume_attempt_outcomes", "contract_consistency"],
    "selected_execution_rationale": ["scan_plan"],
    "contract_consistency": ["scan_plan", "session_integrity", "diagnostics_pack", "resume_decision", "event_log_index"],
    "release_evidence_pack": ["contract_consistency", "session_integrity", "diagnostics_pack", "event_log_index", "recovery_decision_timeline", "session_report", "qa_pack"],
    "release_gate_decision": ["contract_consistency", "release_evidence_pack", "event_delivery_summary", "resume_attempt_outcomes", "selected_execution_rationale", "session_evidence_seal"],
    "control_plane_snapshot": ["summary_json", "release_gate_decision", "contract_consistency", "session_evidence_seal"],
    "control_authority_snapshot": ["summary_json", "scan_plan"],
    "bridge_observability_report": ["summary_json", "event_delivery_summary"],
    "artifact_registry_snapshot": ["scan_plan", "diagnostics_pack", "release_gate_decision"],
    "session_evidence_seal": ["control_plane_snapshot", "release_gate_decision", "artifact_registry_snapshot"],
}


def infer_dependencies(name: str) -> list[str]:
    """Return registry dependency names for a canonical artifact.

    Args:
        name: Canonical artifact type name.

    Returns:
        Ordered dependency names. Unknown artifacts return an empty list.

    Raises:
        No exceptions are raised.
    """
    return list(_DEPENDENCY_MAP.get(name, []))
