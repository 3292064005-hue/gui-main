from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.utils import now_text


def build_lineage(session_id: str, manifest: dict[str, Any], scan_plan: dict[str, Any], journal: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, Any]:
    steps: list[dict[str, Any]] = [
        {
            "kind": "registration",
            "artifact": "meta/patient_registration.json",
            "registration_hash": str(manifest.get("patient_registration_hash", "")),
            "registration_version": str(manifest.get("registration_version", "")),
        },
        {
            "kind": "plan",
            "artifact": "meta/scan_plan.json",
            "plan_id": str(scan_plan.get("plan_id", "")),
            "plan_kind": str(scan_plan.get("plan_kind", manifest.get("scan_protocol", {}).get("plan_kind", "preview"))),
            "plan_hash": str(manifest.get("scan_plan_hash", "")),
            "planner_version": str(manifest.get("planner_version", "")),
            "registration_hash": str(scan_plan.get("registration_hash", manifest.get("patient_registration_hash", ""))),
        },
    ]
    for entry in journal:
        data = dict(entry.get("data", {}))
        command = str(data.get("command", ""))
        if command in {"load_scan_plan", "start_procedure", "pause_scan", "resume_scan", "safe_retreat", "stop_scan"}:
            steps.append(
                {
                    "kind": "workflow_command",
                    "command": command,
                    "request_id": str(dict(data.get("reply", {})).get("request_id", "")),
                    "ok": bool(dict(data.get("reply", {})).get("ok", False)),
                    "ts_ns": int(data.get("ts_ns", 0) or 0),
                }
            )
    if report:
        steps.append({"kind": "assessment", "artifact": "export/session_report.json", "quality_summary": dict(report.get("quality_summary", {}))})
    return {"generated_at": now_text(), "session_id": session_id, "lineage": steps}


def build_recovery_report(session_id: str, journal: list[dict[str, Any]], annotations: list[dict[str, Any]], alarms: dict[str, Any]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for entry in journal:
        data = dict(entry.get("data", {}))
        command = str(data.get("command", ""))
        if command in {"pause_scan", "resume_scan", "safe_retreat", "emergency_stop"}:
            events.append({
                "kind": "command", "topic": "command_trace", "command": command,
                "ts_ns": int(data.get("ts_ns", 0) or 0), "ok": bool(dict(data.get("reply", {})).get("ok", False)),
                "message": str(dict(data.get("reply", {})).get("message", "")), "auto_action": str(data.get("auto_action", "")),
            })
    for alarm in alarms.get("events", []):
        if str(alarm.get("auto_action", "")) or str(alarm.get("severity", "")).upper().startswith("FATAL"):
            events.append({
                "kind": "alarm", "topic": "alarm_event", "severity": str(alarm.get("severity", "WARN")),
                "source": str(alarm.get("source", "robot_core")), "message": str(alarm.get("message", "")),
                "ts_ns": int(alarm.get("ts_ns", alarm.get("event_ts_ns", 0)) or 0), "auto_action": str(alarm.get("auto_action", "")),
            })
    for entry in annotations:
        data = dict(entry.get("data", {}))
        if str(data.get("kind", "")).lower() in {"alarm", "workflow_failure", "quality_issue"}:
            events.append({
                "kind": "annotation", "topic": "annotation", "severity": str(data.get("severity", "INFO")),
                "message": str(data.get("message", "")), "ts_ns": int(data.get("ts_ns", 0) or 0),
            })
    events.sort(key=lambda item: int(item.get("ts_ns", 0)))
    summary = {
        "event_count": len(events),
        "hold_count": sum(1 for event in events if event.get("command") == "pause_scan" or event.get("auto_action") == "hold"),
        "retreat_count": sum(1 for event in events if "retreat" in str(event.get("command", event.get("auto_action", "")))),
        "estop_count": sum(1 for event in events if str(event.get("command", "")) == "emergency_stop" or str(event.get("severity", "")).upper().startswith("FATAL")),
        "latest_recovery_state": "ESTOP_LATCHED" if any(str(event.get("severity", "")).upper().startswith("FATAL") for event in events) else ("CONTROLLED_RETRACT" if any("retreat" in str(event.get("command", event.get("auto_action", ""))) for event in events) else ("HOLDING" if any(event.get("command") == "pause_scan" or event.get("auto_action") == "hold" for event in events) else "IDLE")),
    }
    return {"generated_at": now_text(), "session_id": session_id, "summary": summary, "events": events}


def build_recovery_decision_timeline(session_id: str, recovery_report: dict[str, Any], resume_decision: dict[str, Any]) -> dict[str, Any]:
    timeline: list[dict[str, Any]] = []
    for event in recovery_report.get("events", []):
        timeline.append({
            "ts_ns": int(event.get("ts_ns", 0) or 0),
            "decision": str(event.get("auto_action") or event.get("command") or event.get("kind", "observe")),
            "reason": str(event.get("message") or event.get("severity") or event.get("kind", "")),
        })
    if resume_decision:
        timeline.append({
            "ts_ns": int(max((item.get("ts_ns", 0) for item in recovery_report.get("events", [])), default=0) or 0),
            "decision": str(resume_decision.get("resume_mode", resume_decision.get("mode", "manual_review"))),
            "reason": ",".join(resume_decision.get("blocking_reasons", [])) or str(resume_decision.get("risk_level", "low")),
        })
    timeline.sort(key=lambda item: int(item.get("ts_ns", 0)))
    return {"generated_at": now_text(), "session_id": session_id, "timeline": timeline, "summary": {"decision_count": len(timeline), "final_resume_mode": str(resume_decision.get("resume_mode", resume_decision.get("mode", "manual_review")))}}


def build_event_log_index(service, session_id: str, command_journal: list[dict[str, Any]], alarms: dict[str, Any], annotations: list[dict[str, Any]], recovery_report: dict[str, Any], resume_decision: dict[str, Any]) -> dict[str, Any]:
    events: list[dict[str, Any]] = []
    for entry in command_journal:
        data = dict(entry.get("data", {}))
        events.append({"topic": "command_trace", "ts_ns": int(data.get("ts_ns", 0) or 0), "request_id": str(dict(data.get("reply", {})).get("request_id", "")), "causation_id": str(data.get("command", "")), "payload": {"command": str(data.get("command", "")), "ok": bool(dict(data.get("reply", {})).get("ok", False))}})
    for alarm in alarms.get("events", []):
        events.append({"topic": "alarm_event", "ts_ns": int(alarm.get("ts_ns", alarm.get("event_ts_ns", 0)) or 0), "payload": {"severity": str(alarm.get("severity", "WARN")), "message": str(alarm.get("message", ""))}})
    for entry in annotations:
        data = dict(entry.get("data", {}))
        events.append({"topic": "annotation", "ts_ns": int(data.get("ts_ns", 0) or 0), "payload": {"kind": str(data.get("kind", "annotation")), "message": str(data.get("message", ""))}})
    for event in recovery_report.get("events", []):
        events.append({"topic": "recovery_event", "ts_ns": int(event.get("ts_ns", 0) or 0), "payload": {"kind": str(event.get("kind", "")), "message": str(event.get("message", event.get("command", "")))}})
    if resume_decision:
        events.append({"topic": "resume_decision", "ts_ns": int(max((item.get("ts_ns", 0) for item in recovery_report.get("events", [])), default=0) or 0), "payload": {"mode": str(resume_decision.get("resume_mode", resume_decision.get("mode", "manual_review"))), "allowed": bool(resume_decision.get("resume_allowed", False))}})
    return service.event_indexer.build(session_id=session_id, events=events)


def build_operator_incident_report(session_id: str, annotations: list[dict[str, Any]], alarms: dict[str, Any]) -> dict[str, Any]:
    incidents: list[dict[str, Any]] = []
    for entry in annotations:
        data = dict(entry.get("data", {}))
        if str(data.get("severity", "INFO")).upper() not in {"WARN", "ERROR", "FATAL_FAULT"}:
            continue
        incidents.append({"kind": str(data.get("kind", "annotation")), "message": str(data.get("message", "")), "severity": str(data.get("severity", "WARN")), "segment_id": int(data.get("segment_id", 0) or 0), "ts_ns": int(data.get("ts_ns", 0) or 0)})
    for event in alarms.get("events", []):
        incidents.append({"kind": "alarm_event", "message": str(event.get("message", "")), "severity": str(event.get("severity", "WARN")), "segment_id": int(event.get("segment_id", 0) or 0), "ts_ns": int(event.get("ts_ns", event.get("event_ts_ns", 0)) or 0), "source": str(event.get("source", "robot_core"))})
    incidents.sort(key=lambda item: int(item.get("ts_ns", 0)))
    return {"generated_at": now_text(), "session_id": session_id, "count": len(incidents), "incidents": incidents[-200:]}
