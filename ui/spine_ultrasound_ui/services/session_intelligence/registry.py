from __future__ import annotations

from spine_ultrasound_ui.services.session_intelligence.product_contracts import SessionIntelligenceProductSpec


def _spec(
    product: str,
    output_artifact: str,
    dependencies: tuple[str, ...],
    retryable: bool,
    performance_budget_ms: int,
    owner_domain: str,
    *,
    materialization_phase: str = 'session_finalize',
    read_policy: str = 'materialized_only',
    stale_policy: str = 'refresh_via_session_finalize',
) -> SessionIntelligenceProductSpec:
    return SessionIntelligenceProductSpec(
        product=product,
        output_artifact=output_artifact,
        dependencies=dependencies,
        retryable=retryable,
        performance_budget_ms=performance_budget_ms,
        owner_domain=owner_domain,
        materialization_phase=materialization_phase,
        read_policy=read_policy,
        stale_policy=stale_policy,
    )


SESSION_INTELLIGENCE_REGISTRY: tuple[SessionIntelligenceProductSpec, ...] = (
    _spec('lineage', 'meta/lineage.json', ('meta/manifest.json', 'meta/scan_plan.json', 'export/session_report.json'), True, 1000, 'session-evidence'),
    _spec('resume_state', 'meta/resume_state.json', ('meta/manifest.json', 'meta/scan_plan.json', 'export/recovery_report.json', 'export/session_integrity.json'), True, 1000, 'session-evidence'),
    _spec('resume_decision', 'meta/resume_decision.json', ('meta/resume_state.json', 'export/recovery_report.json', 'derived/incidents/session_incidents.json'), True, 1000, 'session-evidence'),
    _spec('resume_attempts', 'derived/session/resume_attempts.json', ('meta/resume_decision.json',), True, 800, 'session-evidence'),
    _spec('resume_attempt_outcomes', 'derived/session/resume_attempt_outcomes.json', ('derived/session/resume_attempts.json',), True, 800, 'session-evidence'),
    _spec('command_state_policy', 'derived/session/command_state_policy.json', ('raw/ui/command_journal.jsonl',), True, 800, 'governance'),
    _spec('command_policy_snapshot', 'derived/session/command_policy_snapshot.json', ('derived/session/command_state_policy.json',), True, 800, 'governance'),
    _spec('contract_kernel_diff', 'derived/session/contract_kernel_diff.json', ('meta/manifest.json', 'derived/session/command_policy_snapshot.json'), True, 1000, 'governance'),
    _spec('recovery_report', 'export/recovery_report.json', ('raw/ui/command_journal.jsonl', 'derived/alarms/alarm_timeline.json', 'raw/ui/annotations.jsonl'), True, 1200, 'session-evidence'),
    _spec('recovery_decision_timeline', 'derived/recovery/recovery_decision_timeline.json', ('export/recovery_report.json', 'meta/resume_decision.json'), True, 1200, 'session-evidence'),
    _spec('operator_incident_report', 'export/operator_incident_report.json', ('derived/incidents/session_incidents.json', 'export/recovery_report.json'), True, 1200, 'session-evidence'),
    _spec('session_incidents', 'derived/incidents/session_incidents.json', ('raw/ui/annotations.jsonl', 'derived/alarms/alarm_timeline.json', 'derived/quality/quality_timeline.json'), True, 1000, 'session-evidence'),
    _spec('event_log_index', 'derived/events/event_log_index.json', ('raw/core/alarm_event.jsonl', 'raw/ui/annotations.jsonl', 'raw/ui/command_journal.jsonl'), True, 1200, 'eventing'),
    _spec('event_delivery_summary', 'derived/events/event_delivery_summary.json', ('derived/events/event_log_index.json',), True, 1200, 'eventing'),
    _spec('selected_execution_rationale', 'derived/planning/selected_execution_rationale.json', ('meta/scan_plan.json', 'meta/manifest.json'), True, 800, 'planning'),
    _spec('release_evidence_pack', 'export/release_evidence_pack.json', ('derived/session/contract_consistency.json', 'export/session_integrity.json', 'meta/resume_decision.json'), True, 1500, 'release'),
    _spec('release_gate_decision', 'export/release_gate_decision.json', ('export/release_evidence_pack.json', 'derived/events/event_delivery_summary.json', 'derived/session/command_policy_snapshot.json'), True, 1000, 'release'),
    _spec('contract_consistency', 'derived/session/contract_consistency.json', ('meta/manifest.json', 'derived/session/contract_kernel_diff.json'), True, 1000, 'governance'),
    _spec('control_plane_snapshot', 'derived/session/control_plane_snapshot.json', ('meta/manifest.json', 'export/release_gate_decision.json'), True, 1000, 'governance'),
    _spec('control_authority_snapshot', 'derived/session/control_authority_snapshot.json', ('meta/manifest.json',), True, 800, 'governance'),
    _spec('bridge_observability_report', 'derived/events/bridge_observability_report.json', ('derived/events/event_log_index.json',), True, 1000, 'eventing'),
    _spec('artifact_registry_snapshot', 'derived/session/artifact_registry_snapshot.json', ('meta/manifest.json',), True, 800, 'session-evidence'),
    _spec('session_evidence_seal', 'meta/session_evidence_seal.json', ('meta/manifest.json',), True, 800, 'release'),
)


def iter_product_specs() -> tuple[SessionIntelligenceProductSpec, ...]:
    return SESSION_INTELLIGENCE_REGISTRY
