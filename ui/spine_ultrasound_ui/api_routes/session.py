from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, HTTPException


def _make_session_handler(adapter_getter: Callable[[], Any], adapter_method: str):
    async def _handler():
        adapter = adapter_getter()
        try:
            return getattr(adapter, adapter_method)()
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc

    _handler.__name__ = adapter_method
    return _handler


def build_session_router(adapter_getter: Callable[[], Any]) -> APIRouter:
    router = APIRouter()

    session_routes = {
        "/api/v1/sessions/current": "current_session",
        "/api/v1/sessions/current/report": "current_report",
        "/api/v1/sessions/current/replay": "current_replay",
        "/api/v1/sessions/current/quality": "current_quality",
        "/api/v1/sessions/current/frame-sync": "current_frame_sync",
        "/api/v1/sessions/current/alarms": "current_alarms",
        "/api/v1/sessions/current/artifacts": "current_artifacts",
        "/api/v1/sessions/current/compare": "current_compare",
        "/api/v1/sessions/current/qa-pack": "current_qa_pack",
        "/api/v1/sessions/current/trends": "current_trends",
        "/api/v1/sessions/current/diagnostics": "current_diagnostics",
        "/api/v1/sessions/current/annotations": "current_annotations",
        "/api/v1/sessions/current/readiness": "current_readiness",
        "/api/v1/sessions/current/profile": "current_profile",
        "/api/v1/sessions/current/patient-registration": "current_patient_registration",
        "/api/v1/sessions/current/scan-protocol": "current_scan_protocol",
        "/api/v1/sessions/current/command-trace": "current_command_trace",
        "/api/v1/sessions/current/assessment": "current_assessment",
        "/api/v1/sessions/current/contact": "current_contact",
        "/api/v1/sessions/current/recovery": "current_recovery",
        "/api/v1/sessions/current/integrity": "current_integrity",
        "/api/v1/sessions/current/lineage": "current_lineage",
        "/api/v1/sessions/current/resume-state": "current_resume_state",
        "/api/v1/sessions/current/recovery-report": "current_recovery_report",
        "/api/v1/sessions/current/operator-incidents": "current_operator_incidents",
        "/api/v1/sessions/current/incidents": "current_incidents",
        "/api/v1/sessions/current/resume-decision": "current_resume_decision",
        "/api/v1/sessions/current/event-log-index": "current_event_log_index",
        "/api/v1/sessions/current/recovery-timeline": "current_recovery_timeline",
        "/api/v1/sessions/current/resume-attempts": "current_resume_attempts",
        "/api/v1/sessions/current/resume-outcomes": "current_resume_outcomes",
        "/api/v1/sessions/current/command-policy-snapshot": "current_command_policy_snapshot",
        "/api/v1/sessions/current/contract-kernel-diff": "current_contract_kernel_diff",
        "/api/v1/sessions/current/contract-consistency": "current_contract_consistency",
        "/api/v1/sessions/current/event-delivery-summary": "current_event_delivery_summary",
        "/api/v1/sessions/current/release-evidence": "current_release_evidence",
        "/api/v1/sessions/current/selected-execution-rationale": "current_selected_execution_rationale",
        "/api/v1/sessions/current/release-gate": "current_release_gate_decision",
        "/api/v1/sessions/current/evidence-seal": "current_evidence_seal",
    }
    for path, method_name in session_routes.items():
        router.add_api_route(path, _make_session_handler(adapter_getter, method_name), methods=["GET"])

    @router.get("/api/v1/sessions/current/command-policy")
    async def get_current_session_command_policy():
        return adapter_getter().current_command_policy()

    return router
