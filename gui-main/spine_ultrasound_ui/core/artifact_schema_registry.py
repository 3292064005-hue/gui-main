from __future__ import annotations

from typing import Final


ARTIFACT_SCHEMA_HINTS: Final[dict[str, str]] = {
    "summary_json": "summary.schema.json",
    "session_report": "session_report.schema.json",
    "replay_index": "replay_index.schema.json",
    "quality_timeline": "quality_timeline.schema.json",
    "alarm_timeline": "alarm_event.schema.json",
    "qa_pack": "qa_pack.schema.json",
    "session_compare": "session_compare.schema.json",
    "session_trends": "session_trends.schema.json",
    "diagnostics_pack": "diagnostics_pack.schema.json",
    "device_readiness": "device_readiness.schema.json",
    "xmate_profile": "xmate_profile.schema.json",
    "patient_registration": "patient_registration.schema.json",
    "scan_protocol": "scan_protocol.schema.json",
    "frame_sync_index": "frame_sync_index.schema.json",
    "session_integrity": "artifact_registry.schema.json",
    "lineage": "session/lineage.schema.json",
    "resume_state": "session/resume_state.schema.json",
    "recovery_report": "session/recovery_report.schema.json",
    "operator_incident_report": "session/operator_incident_report.schema.json",
    "session_incidents": "session/session_incidents.schema.json",
    "resume_decision": "session/resume_decision.schema.json",
    "event_log_index": "session/event_log_index_v1.schema.json",
    "event_delivery_summary": "session/event_delivery_summary_v1.schema.json",
    "selected_execution_rationale": "session/selected_execution_rationale_v1.schema.json",
    "release_gate_decision": "runtime/release_gate_decision_v1.schema.json",
    "recovery_decision_timeline": "session/recovery_timeline_v1.schema.json",
    "resume_attempts": "session/resume_attempts_v1.schema.json",
    "resume_attempt_outcomes": "session/resume_attempt_outcomes_v1.schema.json",
    "contract_consistency": "session/contract_consistency_v1.schema.json",
    "release_evidence_pack": "session/release_evidence_pack_v1.schema.json",
    "command_state_policy": "runtime/command_state_policy_v1.schema.json",
    "command_policy_snapshot": "session/command_policy_snapshot_v1.schema.json",
    "contract_kernel_diff": "session/contract_kernel_diff_v1.schema.json",
    "session_evidence_seal": "session/session_evidence_seal_v1.schema.json",
    "postprocess_stage_manifest": "session/postprocess_stage_manifest_v1.schema.json",
    "session_intelligence_manifest": "session/session_intelligence_manifest_v1.schema.json",
}


def schema_for_artifact(name: str) -> str:
    """Return the schema hint registered for an artifact type.

    Args:
        name: Canonical artifact type registered in the manifest.

    Returns:
        Schema path hint or an empty string when no hint is registered.

    Raises:
        No exceptions are raised.
    """
    return ARTIFACT_SCHEMA_HINTS.get(name, "")
