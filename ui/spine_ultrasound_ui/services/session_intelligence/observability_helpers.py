from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text


def build_resume_state(session_id: str, manifest: dict[str, Any], scan_plan: dict[str, Any], journal: list[dict[str, Any]], recovery_report: dict[str, Any], integrity: dict[str, Any], incidents: dict[str, Any]) -> dict[str, Any]:
    last_successful_segment = 0
    last_successful_waypoint = 0
    for entry in journal:
        data = dict(entry.get("data", {}))
        reply = dict(data.get("reply", {}))
        if not bool(reply.get("ok", False)):
            continue
        command = str(data.get("command", ""))
        if command in {"start_procedure", "resume_scan"}:
            last_successful_segment = max(last_successful_segment, 1)
            last_successful_waypoint = max(last_successful_waypoint, 1)
    blocking_reasons: list[str] = []
    if not bool(integrity.get("summary", {}).get("integrity_ok", False)):
        blocking_reasons.append("artifact_integrity_failed")
    if recovery_report.get("summary", {}).get("latest_recovery_state", "IDLE") == "ESTOP_LATCHED":
        blocking_reasons.append("estop_latched")
    if int(incidents.get("summary", {}).get("hold_count", 0)) > 2:
        blocking_reasons.append("repeated_holds")
    return {
        "generated_at": now_text(),
        "session_id": session_id,
        "resume_ready": not blocking_reasons and bool(integrity.get("summary", {}).get("integrity_ok", False)),
        "plan_hash": str(manifest.get("scan_plan_hash", "")),
        "plan_id": str(scan_plan.get("plan_id", "")),
        "last_successful_segment": last_successful_segment,
        "last_successful_waypoint": last_successful_waypoint,
        "recovery_state": str(recovery_report.get("summary", {}).get("latest_recovery_state", "IDLE")),
        "artifact_integrity_ok": bool(integrity.get("summary", {}).get("integrity_ok", False)),
        "blocking_reasons": blocking_reasons,
    }


def build_resume_attempts(session_id: str, journal: list[dict[str, Any]], resume_decision: dict[str, Any]) -> dict[str, Any]:
    attempts: list[dict[str, Any]] = []
    for entry in journal:
        data = dict(entry.get("data", {}))
        command = str(data.get("command", ""))
        if command not in {"resume_scan", "start_procedure"}:
            continue
        reply = dict(data.get("reply", {}))
        outcome = "success" if bool(reply.get("ok", False)) else ("blocked" if command == "resume_scan" else "failed")
        attempts.append({
            "command": command, "ts_ns": int(data.get("ts_ns", 0) or 0), "ok": bool(reply.get("ok", False)),
            "request_id": str(reply.get("request_id", "")), "message": str(reply.get("message", "")),
            "resume_mode": str(resume_decision.get("resume_mode", "")) if command == "resume_scan" else "initial_start",
            "command_sequence": list(resume_decision.get("command_sequence", [])) if command == "resume_scan" else [],
            "resume_token": str(resume_decision.get("resume_token", "")) if command == "resume_scan" else "",
            "outcome": outcome,
        })
    attempts.sort(key=lambda item: int(item.get("ts_ns", 0)))
    return {"generated_at": now_text(), "session_id": session_id, "summary": {"attempt_count": len(attempts), "success_count": sum(1 for attempt in attempts if attempt.get("ok", False)), "failure_count": sum(1 for attempt in attempts if not attempt.get("ok", False)), "latest_mode": attempts[-1].get("resume_mode", "") if attempts else "", "latest_outcome": attempts[-1].get("outcome", "") if attempts else ""}, "attempts": attempts}


def build_control_plane_snapshot(session_id: str, summary: dict[str, Any], release_gate_decision: dict[str, Any], contract_consistency: dict[str, Any], evidence_seal: dict[str, Any]) -> dict[str, Any]:
    payload = dict(summary.get('control_plane_snapshot', {}))
    payload.setdefault('session_id', session_id)
    payload.setdefault('release_gate', {'release_allowed': bool(release_gate_decision.get('release_allowed', False)), 'blocking_reasons': list(release_gate_decision.get('blocking_reasons', []))})
    payload.setdefault('contract_summary', dict(contract_consistency.get('summary', {})))
    payload.setdefault('evidence_seal_state', {'summary_state': 'ready' if bool(evidence_seal) else 'degraded', 'summary_label': 'session evidence seal' if bool(evidence_seal) else 'session evidence seal missing', 'detail': str(evidence_seal.get('seal_digest', '')) if evidence_seal else 'missing'})
    return payload


def build_control_authority_snapshot(session_id: str, summary: dict[str, Any], manifest: dict[str, Any]) -> dict[str, Any]:
    payload = dict(summary.get('control_authority', {}) or manifest.get('control_authority', {}))
    payload.setdefault('session_id', session_id)
    payload.setdefault('owner', dict(payload.get('owner', {})))
    payload.setdefault('active_lease', dict(payload.get('active_lease', {})))
    payload.setdefault('owner_provenance', dict(payload.get('owner_provenance', {})))
    return payload


def build_bridge_observability_report(session_id: str, summary: dict[str, Any], event_delivery_summary: dict[str, Any]) -> dict[str, Any]:
    payload = dict(summary.get('bridge_observability', {}))
    payload.setdefault('session_id', session_id)
    payload['event_delivery_summary'] = dict(event_delivery_summary.get('summary', {}))
    payload.setdefault('command_lifecycle', ['issued', 'accepted', 'state transition observed', 'telemetry confirmed', 'stability window passed', 'committed'])
    return payload


def build_artifact_registry_snapshot(session_id: str, manifest: dict[str, Any]) -> dict[str, Any]:
    registry = dict(manifest.get('artifact_registry', {}))
    return {'generated_at': now_text(), 'session_id': session_id, 'artifact_count': len(registry), 'artifact_registry': registry}


def build_event_delivery_summary(session_id: str, event_log_index: dict[str, Any], resume_attempt_outcomes: dict[str, Any], contract_consistency: dict[str, Any]) -> dict[str, Any]:
    summary = dict(event_log_index.get('summary', {}))
    continuity = list(summary.get('continuity_gaps', []))
    outcome_summary = dict(resume_attempt_outcomes.get('summary', {}))
    contract_summary = dict(contract_consistency.get('summary', {}))
    return {'generated_at': now_text(), 'session_id': session_id, 'summary': {'event_count': int(summary.get('count', 0) or 0), 'continuity_gap_count': len(continuity), 'dead_letter_count': 0, 'resume_failure_count': int(outcome_summary.get('failed_attempt_count', 0) or 0), 'contract_consistent': bool(contract_summary.get('consistent', False))}, 'continuity_gaps': continuity, 'delivery_classes': {'persisted': int(summary.get('count', 0) or 0)}, 'resume_outcome_summary': outcome_summary, 'contract_consistency_summary': contract_summary}
