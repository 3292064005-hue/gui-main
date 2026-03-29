from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.utils import now_text


class IncidentClassifier:
    def classify(
        self,
        *,
        session_id: str,
        annotations: list[dict[str, Any]],
        alarms: dict[str, Any],
        recovery_report: dict[str, Any],
        quality: dict[str, Any],
    ) -> dict[str, Any]:
        incidents: list[dict[str, Any]] = []
        for alarm in alarms.get("events", []):
            message = str(alarm.get("message", "")).lower()
            if "pressure" in message or alarm.get("auto_action") == "hold":
                incidents.append({
                    "incident_type": "force_excursion_incident",
                    "severity": str(alarm.get("severity", "WARN")),
                    "message": str(alarm.get("message", "")),
                    "segment_id": int(alarm.get("segment_id", 0) or 0),
                    "ts_ns": int(alarm.get("ts_ns", alarm.get("event_ts_ns", 0)) or 0),
                    "evidence_refs": [{"kind": "alarm", "source": alarm.get("source", "robot_core")}],
                })
            if "stale" in message or str(alarm.get("source", "")) == "sensor":
                incidents.append({
                    "incident_type": "recording_degradation_incident",
                    "severity": str(alarm.get("severity", "WARN")),
                    "message": str(alarm.get("message", "")),
                    "segment_id": int(alarm.get("segment_id", 0) or 0),
                    "ts_ns": int(alarm.get("ts_ns", alarm.get("event_ts_ns", 0)) or 0),
                    "evidence_refs": [{"kind": "sensor_alarm"}],
                })
        for point in quality.get("points", []):
            if float(point.get("quality_score", 1.0)) < 0.72:
                incidents.append({
                    "incident_type": "contact_instability_incident",
                    "severity": "WARN",
                    "message": "low quality valley suggests unstable contact",
                    "segment_id": int(point.get("segment_id", 0) or 0),
                    "ts_ns": int(point.get("ts_ns", 0) or 0),
                    "evidence_refs": [{"kind": "quality", "quality_score": float(point.get("quality_score", 0.0))}],
                })
        for entry in annotations:
            data = dict(entry.get("data", entry))
            if str(data.get("kind", "")).lower() in {"workflow_failure", "alarm", "quality_issue"}:
                incidents.append({
                    "incident_type": "plan_validity_incident" if "plan" in str(data.get("message", "")).lower() else "operator_flagged_incident",
                    "severity": str(data.get("severity", "WARN")),
                    "message": str(data.get("message", "")),
                    "segment_id": int(data.get("segment_id", 0) or 0),
                    "ts_ns": int(data.get("ts_ns", 0) or 0),
                    "evidence_refs": [{"kind": "annotation"}],
                })
        incidents.sort(key=lambda item: int(item.get("ts_ns", 0)))
        summary = {
            "count": len(incidents),
            "types": sorted({incident["incident_type"] for incident in incidents}),
            "hold_count": int(recovery_report.get("summary", {}).get("hold_count", 0)),
            "retreat_count": int(recovery_report.get("summary", {}).get("retreat_count", 0)),
        }
        return {
            "generated_at": now_text(),
            "session_id": session_id,
            "summary": summary,
            "incidents": incidents[-200:],
        }
