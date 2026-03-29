from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.contracts import schema_catalog
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.utils import now_text


class DiagnosticsPackService:
    def __init__(self) -> None:
        self.integrity_service = SessionIntegrityService()

    def build(self, session_dir: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / "meta" / "manifest.json")
        journal = self._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl")
        alarms = self._read_json(session_dir / "derived" / "alarms" / "alarm_timeline.json")
        quality = self._read_json(session_dir / "derived" / "quality" / "quality_timeline.json")
        replay = self._read_json(session_dir / "replay" / "replay_index.json")
        sync_index = self._read_json(session_dir / "derived" / "sync" / "frame_sync_index.json")
        annotations = self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
        incidents = self._read_json(session_dir / "derived" / "incidents" / "session_incidents.json")
        resume_decision = self._read_json(session_dir / "meta" / "resume_decision.json")
        contract_consistency = self._read_json(session_dir / "derived" / "session" / "contract_consistency.json")
        release_evidence = self._read_json(session_dir / "export" / "release_evidence_pack.json")
        artifact_registry = dict(manifest.get("artifact_registry", {}))
        recovery_state = self._derive_recovery_state(alarms)
        integrity = self.integrity_service.build(session_dir)
        return {
            "generated_at": now_text(),
            "session_id": manifest.get("session_id", session_dir.name),
            "health_snapshot": {
                "force_sensor_provider": manifest.get("force_sensor_provider", ""),
                "software_version": manifest.get("software_version", ""),
                "build_id": manifest.get("build_id", ""),
                "session_locked": True,
            },
            "recovery_snapshot": {
                "state": recovery_state,
                "hold_count": alarms.get("summary", {}).get("hold_count", 0),
                "retreat_count": alarms.get("summary", {}).get("retreat_count", 0),
                "fatal_count": alarms.get("summary", {}).get("fatal_count", 0),
                "root_cause_candidates": self._root_cause_candidates(alarms, quality, integrity),
                "evidence_refs": self._evidence_refs(alarms, quality, integrity, incidents),
                "last_recovery_action": self._last_recovery_action(journal, alarms),
            },
            "manifest_excerpt": {
                "experiment_id": manifest.get("experiment_id", ""),
                "session_id": manifest.get("session_id", session_dir.name),
                "protocol_version": manifest.get("protocol_version", 1),
                "core_protocol_version": manifest.get("core_protocol_version", manifest.get("protocol_version", 1)),
                "planner_version": manifest.get("planner_version", ""),
                "registration_version": manifest.get("registration_version", ""),
                "safety_thresholds": manifest.get("safety_thresholds", {}),
                "device_health_snapshot": manifest.get("device_health_snapshot", {}),
                "device_readiness": manifest.get("device_readiness", {}),
                "robot_profile": manifest.get("robot_profile", {}),
                "patient_registration": manifest.get("patient_registration", {}),
                "scan_protocol": manifest.get("scan_protocol", {}),
            },
            "last_commands": [entry.get("data", {}) for entry in journal[-20:]],
            "last_alarms": alarms.get("events", [])[-20:],
            "annotation_tail": [entry.get("data", {}) for entry in annotations[-20:]],
            "incident_digest": incidents.get("summary", {}),
            "resume_digest": resume_decision,
            "contract_consistency": contract_consistency,
            "release_evidence": release_evidence,
            "telemetry_summary": {
                "quality_samples": quality.get("sample_count", len(quality.get("points", []))),
                "stale_samples": quality.get("summary", {}).get("stale_samples", 0),
                "timeline_points": len(replay.get("timeline", [])),
                "usable_sync_ratio": sync_index.get("summary", {}).get("usable_ratio", 0.0),
            },
            "command_digest": {
                "count": len(journal),
                "failed": sum(1 for entry in journal if not bool(entry.get("data", {}).get("reply", {}).get("ok", True))),
                "latest_command": journal[-1].get("data", {}).get("command", "") if journal else "",
            },
            "alarm_digest": alarms.get("summary", {}),
            "quality_digest": quality.get("summary", {}),
            "artifact_digest": {
                "count": len(artifact_registry),
                "ready_count": sum(1 for descriptor in artifact_registry.values() if bool(descriptor.get("ready", False))),
                "artifact_types": sorted(artifact_registry.keys()),
            },
            "artifact_integrity_summary": integrity["summary"],
            "integrity_report": integrity,
            "environment": {
                "session_dir": str(session_dir),
                "backend_mode": manifest.get("config_snapshot", {}).get("backend", ""),
                "robot_model": manifest.get("robot_profile", {}).get("robot_model", ""),
                "preferred_link": manifest.get("robot_profile", {}).get("preferred_link", ""),
                "rt_network_tolerance_percent": manifest.get("robot_profile", {}).get("rt_network_tolerance_percent", 0),
                "fc_frame_type": manifest.get("robot_profile", {}).get("fc_frame_type", ""),
            },
            "versioning": {
                "software_version": manifest.get("software_version", ""),
                "build_id": manifest.get("build_id", ""),
                "protocol_version": manifest.get("protocol_version", 1),
                "schema_count": len(schema_catalog()),
            },
            "recommendations": self._recommendations(quality, alarms, annotations, integrity, resume_decision, incidents),
            "schemas": {key: value.get("$id", key) for key, value in schema_catalog().items()},
            "summary": {
                "command_count": len(journal),
                "alarm_count": alarms.get("summary", {}).get("count", 0),
                "annotation_count": len(annotations),
                "frame_sync_count": sync_index.get("summary", {}).get("frame_count", 0),
                "incident_count": incidents.get("summary", {}).get("count", 0),
                "integrity_ok": integrity["summary"]["integrity_ok"],
                "contract_consistent": contract_consistency.get("summary", {}).get("consistent", True),
                "release_candidate": release_evidence.get("release_candidate", False),
            },
        }

    @staticmethod
    def _derive_recovery_state(alarms: dict[str, Any]) -> str:
        summary = alarms.get("summary", {})
        if int(summary.get("fatal_count", 0)) > 0:
            return "ESTOP_LATCHED"
        if int(summary.get("retreat_count", 0)) > 0:
            return "CONTROLLED_RETRACT"
        if int(summary.get("hold_count", 0)) > 0:
            return "HOLDING"
        return "IDLE"

    @staticmethod
    def _last_recovery_action(journal: list[dict[str, Any]], alarms: dict[str, Any]) -> str:
        for entry in reversed(journal):
            data = entry.get("data", {})
            if data.get("command") in {"safe_retreat", "pause_scan", "resume_scan"}:
                return str(data.get("command"))
        events = list(alarms.get("events", []))
        if not events:
            return ""
        return str(events[-1].get("auto_action", ""))

    @staticmethod
    def _root_cause_candidates(alarms: dict[str, Any], quality: dict[str, Any], integrity: dict[str, Any]) -> list[str]:
        causes: list[str] = []
        alarm_events = list(alarms.get("events", []))
        if any(str(event.get("source", "")) == "sensor" for event in alarm_events):
            causes.append("sensor_freshness")
        if any("pressure" in str(event.get("message", "")).lower() for event in alarm_events):
            causes.append("pressure_control")
        if int(quality.get("summary", {}).get("stale_samples", 0)) > 0:
            causes.append("telemetry_staleness")
        if not integrity.get("summary", {}).get("integrity_ok", True):
            causes.append("artifact_integrity")
        return sorted(set(causes))

    @staticmethod
    def _evidence_refs(alarms: dict[str, Any], quality: dict[str, Any], integrity: dict[str, Any], incidents: dict[str, Any]) -> list[dict[str, Any]]:
        evidence: list[dict[str, Any]] = []
        for event in alarms.get("events", [])[:5]:
            evidence.append({"kind": "alarm", "source": event.get("source", "robot_core"), "ts_ns": event.get("ts_ns", event.get("event_ts_ns", 0)), "message": event.get("message", "")})
        for point in quality.get("points", [])[:5]:
            if float(point.get("quality_score", 1.0)) < 0.75:
                evidence.append({"kind": "quality_valley", "segment_id": point.get("segment_id", 0), "ts_ns": point.get("ts_ns", 0), "quality_score": point.get("quality_score", 0.0)})
        for incident in incidents.get("incidents", [])[:5]:
            evidence.append({"kind": "incident", "incident_type": incident.get("incident_type", ""), "segment_id": incident.get("segment_id", 0), "ts_ns": incident.get("ts_ns", 0)})
        if not integrity.get("summary", {}).get("integrity_ok", True):
            evidence.append({"kind": "integrity", "warnings": integrity.get("warnings", [])})
        return evidence[:12]

    @staticmethod
    def _recommendations(quality: dict[str, Any], alarms: dict[str, Any], annotations: list[dict[str, Any]], integrity: dict[str, Any], resume_decision: dict[str, Any], incidents: dict[str, Any]) -> list[str]:
        recommendations: list[str] = []
        if int(quality.get("summary", {}).get("stale_samples", 0)) > 0:
            recommendations.append("Review telemetry freshness and sensor timestamps before the next run.")
        if int(alarms.get("summary", {}).get("retreat_count", 0)) > 0:
            recommendations.append("Inspect recovery thresholds because controlled retract occurred during the session.")
        if len(annotations) > 0:
            recommendations.append("Use operator annotations as replay anchors during clinical review.")
        if not integrity.get("summary", {}).get("integrity_ok", True):
            recommendations.append("Repair missing or checksum-mismatched session products before downstream review.")
        if not bool(resume_decision.get("resume_allowed", False)):
            recommendations.append("Do not resume directly; inspect resume blockers and consider restart or patch rescan.")
        if int(incidents.get("summary", {}).get("count", 0)) > 0:
            recommendations.append("Review structured incidents to align operator actions, alarms, and quality valleys.")
        return recommendations

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
