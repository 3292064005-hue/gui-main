from __future__ import annotations

from pathlib import Path
from typing import Any


class SessionIntelligenceProductBuilder:
    """Build session-intelligence products from already loaded inputs."""

    def build(self, service, session_dir: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        manifest = inputs["manifest"]
        scan_plan = inputs["scan_plan"]
        command_journal = inputs["command_journal"]
        annotations = inputs["annotations"]
        alarms = inputs["alarms"]
        quality = inputs["quality"]
        report = inputs["report"]
        summary = inputs["summary"]
        evidence_seal = inputs["evidence_seal"]
        integrity = inputs["integrity"]
        session_id = inputs["session_id"]

        lineage = service.lineage_builder.build(service, session_id=session_id, manifest=manifest, scan_plan=scan_plan, command_journal=command_journal, report=report)
        recovery_report = service.recovery_builder.build_recovery_report(service, session_id=session_id, command_journal=command_journal, annotations=annotations, alarms=alarms)
        incidents = service.incident_classifier.classify(
            session_id=session_id,
            annotations=annotations,
            alarms=alarms,
            recovery_report=recovery_report,
            quality=quality,
        )
        resume_state = service.resume_state_builder.build_resume_state(service, session_id=session_id, manifest=manifest, scan_plan=scan_plan, command_journal=command_journal, recovery_report=recovery_report, integrity=integrity, incidents=incidents)
        resume_decision = service.resume_service.evaluate(
            session_id=session_id,
            manifest=manifest,
            resume_state=resume_state,
            recovery_report=recovery_report,
            incidents=incidents,
            integrity=integrity,
        )
        operator_incident_report = service.recovery_builder.build_operator_incident_report(service, session_id=session_id, annotations=annotations, alarms=alarms)
        event_log_index = service.incident_report_builder.build_event_log_index(service, session_id=session_id, command_journal=command_journal, alarms=alarms, annotations=annotations, recovery_report=recovery_report, resume_decision=resume_decision)
        recovery_decision_timeline = service.incident_report_builder.build_recovery_timeline(service, session_id=session_id, recovery_report=recovery_report, resume_decision=resume_decision)
        resume_attempts = service.resume_state_builder.build_resume_attempts(service, session_id=session_id, command_journal=command_journal, resume_decision=resume_decision)
        command_state_policy = service.command_policy.catalog()
        contract_consistency = service.contract_consistency.build(session_dir)
        selected_execution_rationale = service.selected_execution_rationale.build(session_dir)
        release_evidence_pack = service.release_evidence.build(session_dir)
        resume_attempt_outcomes = service.resume_execution.evaluate_attempt_outcomes(
            session_id=session_id,
            resume_decision=resume_decision,
            resume_attempts=resume_attempts,
            contract_consistency=contract_consistency,
            command_policy_catalog=command_state_policy,
        )
        command_policy_snapshot = service.command_policy_snapshot.build(
            session_id=session_id,
            manifest=manifest,
            scan_plan=scan_plan,
            recovery_report=recovery_report,
            resume_decision=resume_decision,
            resume_attempts=resume_attempts,
        )
        contract_kernel_diff = service.contract_kernel_diff.build(session_dir)
        event_delivery_summary = service._build_event_delivery_summary(session_id, event_log_index, resume_attempt_outcomes, contract_consistency)
        release_gate_decision = service.release_gate.build(session_dir)
        control_plane_snapshot = service.release_artifact_builder.build_control_plane_snapshot(service, session_id=session_id, summary=summary, release_gate_decision=release_gate_decision, contract_consistency=contract_consistency, evidence_seal=evidence_seal)
        control_authority_snapshot = service.release_artifact_builder.build_control_authority_snapshot(service, session_id=session_id, summary=summary, manifest=manifest)
        bridge_observability_report = service.incident_report_builder.build_bridge_observability(service, session_id=session_id, summary=summary, event_delivery_summary=event_delivery_summary)
        artifact_registry_snapshot = service.release_artifact_builder.build_artifact_registry_snapshot(service, session_id=session_id, manifest=manifest)
        evidence_seal_snapshot = evidence_seal or service.evidence_seal.build(session_dir, manifest=manifest)
        return {
            "lineage": lineage,
            "resume_state": resume_state,
            "resume_decision": resume_decision,
            "recovery_report": recovery_report,
            "recovery_decision_timeline": recovery_decision_timeline,
            "operator_incident_report": operator_incident_report,
            "session_incidents": incidents,
            "event_log_index": event_log_index,
            "event_delivery_summary": event_delivery_summary,
            "selected_execution_rationale": selected_execution_rationale,
            "release_gate_decision": release_gate_decision,
            "control_plane_snapshot": control_plane_snapshot,
            "control_authority_snapshot": control_authority_snapshot,
            "bridge_observability_report": bridge_observability_report,
            "artifact_registry_snapshot": artifact_registry_snapshot,
            "session_evidence_seal": evidence_seal_snapshot,
            "resume_attempts": resume_attempts,
            "resume_attempt_outcomes": resume_attempt_outcomes,
            "command_state_policy": command_state_policy,
            "command_policy_snapshot": command_policy_snapshot,
            "contract_kernel_diff": contract_kernel_diff,
            "contract_consistency": contract_consistency,
            "release_evidence_pack": release_evidence_pack,
        }
