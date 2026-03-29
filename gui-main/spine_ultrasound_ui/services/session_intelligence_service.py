from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.command_state_policy import CommandStatePolicyService
from spine_ultrasound_ui.services.command_policy_snapshot_service import CommandPolicySnapshotService
from spine_ultrasound_ui.services.contract_kernel_diff_service import ContractKernelDiffService
from spine_ultrasound_ui.services.contract_consistency_service import ContractConsistencyService
from spine_ultrasound_ui.services.event_log_indexer import EventLogIndexer
from spine_ultrasound_ui.services.release_evidence_pack_service import ReleaseEvidencePackService
from spine_ultrasound_ui.services.release_gate_decision_service import ReleaseGateDecisionService
from spine_ultrasound_ui.services.selected_execution_rationale_service import SelectedExecutionRationaleService
from spine_ultrasound_ui.services.incident_classifier import IncidentClassifier
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.resume_execution_service import ResumeExecutionService
from spine_ultrasound_ui.services.session_resume_service import SessionResumeService
from spine_ultrasound_ui.utils import now_text


class SessionIntelligenceService:
    def __init__(self) -> None:
        self.integrity = SessionIntegrityService()
        self.incident_classifier = IncidentClassifier()
        self.resume_service = SessionResumeService()
        self.event_indexer = EventLogIndexer()
        self.contract_consistency = ContractConsistencyService()
        self.release_evidence = ReleaseEvidencePackService()
        self.release_gate = ReleaseGateDecisionService()
        self.selected_execution_rationale = SelectedExecutionRationaleService()
        self.command_policy = CommandStatePolicyService()
        self.command_policy_snapshot = CommandPolicySnapshotService(self.command_policy)
        self.contract_kernel_diff = ContractKernelDiffService()
        self.resume_execution = ResumeExecutionService()

    def build_all(self, session_dir: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / "meta" / "manifest.json")
        scan_plan = self._read_json(session_dir / "meta" / "scan_plan.json")
        command_journal = self._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl")
        annotations = self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
        alarms = self._read_json(session_dir / "derived" / "alarms" / "alarm_timeline.json")
        quality = self._read_json(session_dir / "derived" / "quality" / "quality_timeline.json")
        report = self._read_json(session_dir / "export" / "session_report.json")
        integrity = self.integrity.build(session_dir)
        session_id = str(manifest.get("session_id", session_dir.name))

        lineage = self._build_lineage(session_id, manifest, scan_plan, command_journal, report)
        recovery_report = self._build_recovery_report(session_id, command_journal, annotations, alarms)
        incidents = self.incident_classifier.classify(
            session_id=session_id,
            annotations=annotations,
            alarms=alarms,
            recovery_report=recovery_report,
            quality=quality,
        )
        resume_state = self._build_resume_state(session_id, manifest, scan_plan, command_journal, recovery_report, integrity, incidents)
        resume_decision = self.resume_service.evaluate(
            session_id=session_id,
            manifest=manifest,
            resume_state=resume_state,
            recovery_report=recovery_report,
            incidents=incidents,
            integrity=integrity,
        )
        operator_incident_report = self._build_operator_incident_report(session_id, annotations, alarms)
        event_log_index = self._build_event_log_index(session_id, command_journal, alarms, annotations, recovery_report, resume_decision)
        recovery_decision_timeline = self._build_recovery_decision_timeline(session_id, recovery_report, resume_decision)
        resume_attempts = self._build_resume_attempts(session_id, command_journal, resume_decision)
        command_state_policy = self.command_policy.catalog()
        self._write_json(session_dir / 'derived' / 'events' / 'event_log_index.json', event_log_index)
        self._write_json(session_dir / 'derived' / 'recovery' / 'recovery_decision_timeline.json', recovery_decision_timeline)
        self._write_json(session_dir / 'meta' / 'resume_decision.json', resume_decision)
        contract_consistency = self.contract_consistency.build(session_dir)
        self._write_json(session_dir / 'derived' / 'session' / 'contract_consistency.json', contract_consistency)
        selected_execution_rationale = self.selected_execution_rationale.build(session_dir)
        self._write_json(session_dir / 'derived' / 'planning' / 'selected_execution_rationale.json', selected_execution_rationale)
        release_evidence_pack = self.release_evidence.build(session_dir)
        resume_attempt_outcomes = self.resume_execution.evaluate_attempt_outcomes(
            session_id=session_id,
            resume_decision=resume_decision,
            resume_attempts=resume_attempts,
            contract_consistency=contract_consistency,
            command_policy_catalog=command_state_policy,
        )
        command_policy_snapshot = self.command_policy_snapshot.build(
            session_id=session_id,
            manifest=manifest,
            scan_plan=scan_plan,
            recovery_report=recovery_report,
            resume_decision=resume_decision,
            resume_attempts=resume_attempts,
        )
        self._write_json(session_dir / 'derived' / 'session' / 'command_policy_snapshot.json', command_policy_snapshot)
        contract_kernel_diff = self.contract_kernel_diff.build(session_dir)
        self._write_json(session_dir / 'derived' / 'session' / 'contract_kernel_diff.json', contract_kernel_diff)
        event_delivery_summary = self._build_event_delivery_summary(session_id, event_log_index, resume_attempt_outcomes, contract_consistency)
        self._write_json(session_dir / 'derived' / 'events' / 'event_delivery_summary.json', event_delivery_summary)
        release_gate_decision = self.release_gate.build(session_dir)
        self._write_json(session_dir / 'export' / 'release_gate_decision.json', release_gate_decision)
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
            "resume_attempts": resume_attempts,
            "resume_attempt_outcomes": resume_attempt_outcomes,
            "command_state_policy": command_state_policy,
            "command_policy_snapshot": command_policy_snapshot,
            "contract_kernel_diff": contract_kernel_diff,
            "contract_consistency": contract_consistency,
            "release_evidence_pack": release_evidence_pack,
        }

    def _build_lineage(self, session_id: str, manifest: dict[str, Any], scan_plan: dict[str, Any], journal: list[dict[str, Any]], report: dict[str, Any]) -> dict[str, Any]:
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
            if command in {"load_scan_plan", "start_scan", "pause_scan", "resume_scan", "safe_retreat"}:
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
            steps.append(
                {
                    "kind": "assessment",
                    "artifact": "export/session_report.json",
                    "quality_summary": dict(report.get("quality_summary", {})),
                }
            )
        return {
            "generated_at": now_text(),
            "session_id": session_id,
            "lineage": steps,
        }

    def _build_recovery_report(self, session_id: str, journal: list[dict[str, Any]], annotations: list[dict[str, Any]], alarms: dict[str, Any]) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        for entry in journal:
            data = dict(entry.get("data", {}))
            command = str(data.get("command", ""))
            if command in {"pause_scan", "resume_scan", "safe_retreat", "emergency_stop"}:
                events.append(
                    {
                        "kind": "command",
                        "topic": "command_trace",
                        "command": command,
                        "ts_ns": int(data.get("ts_ns", 0) or 0),
                        "ok": bool(dict(data.get("reply", {})).get("ok", False)),
                        "message": str(dict(data.get("reply", {})).get("message", "")),
                        "auto_action": str(data.get("auto_action", "")),
                    }
                )
        for alarm in alarms.get("events", []):
            if str(alarm.get("auto_action", "")) or str(alarm.get("severity", "")).upper().startswith("FATAL"):
                events.append(
                    {
                        "kind": "alarm",
                        "topic": "alarm_event",
                        "severity": str(alarm.get("severity", "WARN")),
                        "source": str(alarm.get("source", "robot_core")),
                        "message": str(alarm.get("message", "")),
                        "ts_ns": int(alarm.get("ts_ns", alarm.get("event_ts_ns", 0)) or 0),
                        "auto_action": str(alarm.get("auto_action", "")),
                    }
                )
        for entry in annotations:
            data = dict(entry.get("data", {}))
            if str(data.get("kind", "")).lower() in {"alarm", "workflow_failure", "quality_issue"}:
                events.append(
                    {
                        "kind": "annotation",
                        "topic": "annotation",
                        "severity": str(data.get("severity", "INFO")),
                        "message": str(data.get("message", "")),
                        "ts_ns": int(data.get("ts_ns", 0) or 0),
                    }
                )
        events.sort(key=lambda item: int(item.get("ts_ns", 0)))
        summary = {
            "event_count": len(events),
            "hold_count": sum(1 for event in events if event.get("command") == "pause_scan" or event.get("auto_action") == "hold"),
            "retreat_count": sum(1 for event in events if "retreat" in str(event.get("command", event.get("auto_action", "")))),
            "estop_count": sum(1 for event in events if str(event.get("command", "")) == "emergency_stop" or str(event.get("severity", "")).upper().startswith("FATAL")),
            "latest_recovery_state": "ESTOP_LATCHED" if any(str(event.get("severity", "")).upper().startswith("FATAL") for event in events) else ("CONTROLLED_RETRACT" if any("retreat" in str(event.get("command", event.get("auto_action", ""))) for event in events) else ("HOLDING" if any(event.get("command") == "pause_scan" or event.get("auto_action") == "hold" for event in events) else "IDLE")),
        }
        return {
            "generated_at": now_text(),
            "session_id": session_id,
            "summary": summary,
            "events": events,
        }

    def _build_resume_state(self, session_id: str, manifest: dict[str, Any], scan_plan: dict[str, Any], journal: list[dict[str, Any]], recovery_report: dict[str, Any], integrity: dict[str, Any], incidents: dict[str, Any]) -> dict[str, Any]:
        last_successful_segment = 0
        last_successful_waypoint = 0
        for entry in journal:
            data = dict(entry.get("data", {}))
            reply = dict(data.get("reply", {}))
            if not bool(reply.get("ok", False)):
                continue
            command = str(data.get("command", ""))
            if command in {"start_scan", "resume_scan"}:
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


    def _build_resume_attempts(self, session_id: str, journal: list[dict[str, Any]], resume_decision: dict[str, Any]) -> dict[str, Any]:
        attempts: list[dict[str, Any]] = []
        for entry in journal:
            data = dict(entry.get("data", {}))
            command = str(data.get("command", ""))
            if command not in {"resume_scan", "start_scan"}:
                continue
            reply = dict(data.get("reply", {}))
            outcome = "success" if bool(reply.get("ok", False)) else ("blocked" if command == "resume_scan" else "failed")
            attempts.append({
                "command": command,
                "ts_ns": int(data.get("ts_ns", 0) or 0),
                "ok": bool(reply.get("ok", False)),
                "request_id": str(reply.get("request_id", "")),
                "message": str(reply.get("message", "")),
                "resume_mode": str(resume_decision.get("resume_mode", "")) if command == "resume_scan" else "initial_start",
                "command_sequence": list(resume_decision.get("command_sequence", [])) if command == "resume_scan" else [],
                "resume_token": str(resume_decision.get("resume_token", "")) if command == "resume_scan" else "",
                "outcome": outcome,
            })
        attempts.sort(key=lambda item: int(item.get("ts_ns", 0)))
        return {
            "generated_at": now_text(),
            "session_id": session_id,
            "summary": {
                "attempt_count": len(attempts),
                "success_count": sum(1 for attempt in attempts if attempt.get("ok", False)),
                "failure_count": sum(1 for attempt in attempts if not attempt.get("ok", False)),
                "latest_mode": attempts[-1].get("resume_mode", "") if attempts else "",
                "latest_outcome": attempts[-1].get("outcome", "") if attempts else "",
            },
            "attempts": attempts,
        }

    def _build_event_delivery_summary(self, session_id: str, event_log_index: dict[str, Any], resume_attempt_outcomes: dict[str, Any], contract_consistency: dict[str, Any]) -> dict[str, Any]:
        summary = dict(event_log_index.get('summary', {}))
        continuity = list(summary.get('continuity_gaps', []))
        outcome_summary = dict(resume_attempt_outcomes.get('summary', {}))
        contract_summary = dict(contract_consistency.get('summary', {}))
        return {
            'generated_at': now_text(),
            'session_id': session_id,
            'summary': {
                'event_count': int(summary.get('count', 0) or 0),
                'continuity_gap_count': len(continuity),
                'dead_letter_count': 0,
                'resume_failure_count': int(outcome_summary.get('failed_attempt_count', 0) or 0),
                'contract_consistent': bool(contract_summary.get('consistent', False)),
            },
            'continuity_gaps': continuity,
            'delivery_classes': {'persisted': int(summary.get('count', 0) or 0)},
            'resume_outcome_summary': outcome_summary,
            'contract_consistency_summary': contract_summary,
        }

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def _build_recovery_decision_timeline(self, session_id: str, recovery_report: dict[str, Any], resume_decision: dict[str, Any]) -> dict[str, Any]:
        timeline: list[dict[str, Any]] = []
        for event in recovery_report.get("events", []):
            entry = {
                "ts_ns": int(event.get("ts_ns", 0) or 0),
                "decision": str(event.get("auto_action") or event.get("command") or event.get("kind", "observe")),
                "reason": str(event.get("message") or event.get("severity") or event.get("kind", "")),
            }
            timeline.append(entry)
        if resume_decision:
            timeline.append({
                "ts_ns": int(max((item.get("ts_ns", 0) for item in recovery_report.get("events", [])), default=0) or 0),
                "decision": str(resume_decision.get("resume_mode", resume_decision.get("mode", "manual_review"))),
                "reason": ",".join(resume_decision.get("blocking_reasons", [])) or str(resume_decision.get("risk_level", "low")),
            })
        timeline.sort(key=lambda item: int(item.get("ts_ns", 0)))
        return {
            "generated_at": now_text(),
            "session_id": session_id,
            "timeline": timeline,
            "summary": {
                "decision_count": len(timeline),
                "final_resume_mode": str(resume_decision.get("resume_mode", resume_decision.get("mode", "manual_review"))),
            },
        }

    def _build_event_log_index(self, session_id: str, command_journal: list[dict[str, Any]], alarms: dict[str, Any], annotations: list[dict[str, Any]], recovery_report: dict[str, Any], resume_decision: dict[str, Any]) -> dict[str, Any]:
        events: list[dict[str, Any]] = []
        for entry in command_journal:
            data = dict(entry.get("data", {}))
            events.append({
                "topic": "command_trace",
                "ts_ns": int(data.get("ts_ns", 0) or 0),
                "request_id": str(dict(data.get("reply", {})).get("request_id", "")),
                "causation_id": str(data.get("command", "")),
                "payload": {"command": str(data.get("command", "")), "ok": bool(dict(data.get("reply", {})).get("ok", False))},
            })
        for alarm in alarms.get("events", []):
            events.append({
                "topic": "alarm_event",
                "ts_ns": int(alarm.get("ts_ns", alarm.get("event_ts_ns", 0)) or 0),
                "payload": {"severity": str(alarm.get("severity", "WARN")), "message": str(alarm.get("message", ""))},
            })
        for entry in annotations:
            data = dict(entry.get("data", {}))
            events.append({
                "topic": "annotation",
                "ts_ns": int(data.get("ts_ns", 0) or 0),
                "payload": {"kind": str(data.get("kind", "annotation")), "message": str(data.get("message", ""))},
            })
        for event in recovery_report.get("events", []):
            events.append({
                "topic": "recovery_event",
                "ts_ns": int(event.get("ts_ns", 0) or 0),
                "payload": {"kind": str(event.get("kind", "")), "message": str(event.get("message", event.get("command", "")))},
            })
        if resume_decision:
            events.append({
                "topic": "resume_decision",
                "ts_ns": int(max((item.get("ts_ns", 0) for item in recovery_report.get("events", [])), default=0) or 0),
                "payload": {"mode": str(resume_decision.get("resume_mode", resume_decision.get("mode", "manual_review"))), "allowed": bool(resume_decision.get("resume_allowed", False))},
            })
        return self.event_indexer.build(session_id=session_id, events=events)

    def _build_operator_incident_report(self, session_id: str, annotations: list[dict[str, Any]], alarms: dict[str, Any]) -> dict[str, Any]:
        incidents: list[dict[str, Any]] = []
        for entry in annotations:
            data = dict(entry.get("data", {}))
            if str(data.get("severity", "INFO")).upper() not in {"WARN", "ERROR", "FATAL_FAULT"}:
                continue
            incidents.append({
                "kind": str(data.get("kind", "annotation")),
                "message": str(data.get("message", "")),
                "severity": str(data.get("severity", "WARN")),
                "segment_id": int(data.get("segment_id", 0) or 0),
                "ts_ns": int(data.get("ts_ns", 0) or 0),
            })
        for event in alarms.get("events", []):
            incidents.append({
                "kind": "alarm_event",
                "message": str(event.get("message", "")),
                "severity": str(event.get("severity", "WARN")),
                "segment_id": int(event.get("segment_id", 0) or 0),
                "ts_ns": int(event.get("ts_ns", event.get("event_ts_ns", 0)) or 0),
                "source": str(event.get("source", "robot_core")),
            })
        incidents.sort(key=lambda item: int(item.get("ts_ns", 0)))
        return {
            "generated_at": now_text(),
            "session_id": session_id,
            "count": len(incidents),
            "incidents": incidents[-200:],
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        rows: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip():
                rows.append(json.loads(line))
        return rows
