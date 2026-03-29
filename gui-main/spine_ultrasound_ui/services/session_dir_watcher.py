from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.event_envelope import EventEnvelope
from spine_ultrasound_ui.utils import now_ns


class SessionDirWatcher:
    def __init__(self) -> None:
        self._topic_signatures: dict[str, str] = {}
        self._last_signature = ""

    def poll(self, session_dir: Path | None, *, session_id: str = "") -> list[dict[str, Any]]:
        if session_dir is None:
            signature = "no-session"
            changed = self._last_signature != signature
            self._last_signature = signature
            if not changed:
                return []
            return [
                EventEnvelope(
                    topic="session_product_update",
                    payload={"session_id": session_id, "signature": signature, "changed": True, "changed_topics": []},
                    session_id=session_id,
                    category="session",
                    delivery="event",
                ).to_message()
            ]

        watched = {
            "manifest_updated": session_dir / "meta" / "manifest.json",
            "readiness_updated": session_dir / "meta" / "device_readiness.json",
            "profile_updated": session_dir / "meta" / "xmate_profile.json",
            "registration_updated": session_dir / "meta" / "patient_registration.json",
            "report_updated": session_dir / "export" / "session_report.json",
            "compare_updated": session_dir / "export" / "session_compare.json",
            "trends_updated": session_dir / "export" / "session_trends.json",
            "qa_pack_updated": session_dir / "export" / "qa_pack.json",
            "diagnostics_updated": session_dir / "export" / "diagnostics_pack.json",
            "recovery_timeline_updated": session_dir / "derived" / "recovery" / "recovery_decision_timeline.json",
            "resume_attempts_updated": session_dir / "derived" / "session" / "resume_attempts.json",
            "resume_outcomes_updated": session_dir / "derived" / "session" / "resume_attempt_outcomes.json",
            "command_policy_updated": session_dir / "derived" / "session" / "command_state_policy.json",
            "command_policy_snapshot_updated": session_dir / "derived" / "session" / "command_policy_snapshot.json",
            "contract_kernel_diff_updated": session_dir / "derived" / "session" / "contract_kernel_diff.json",
            "contract_consistency_updated": session_dir / "derived" / "session" / "contract_consistency.json",
            "release_evidence_updated": session_dir / "export" / "release_evidence_pack.json",
            "event_log_index_updated": session_dir / "derived" / "events" / "event_log_index.json",
            "event_delivery_summary_updated": session_dir / "derived" / "events" / "event_delivery_summary.json",
            "selected_execution_rationale_updated": session_dir / "derived" / "planning" / "selected_execution_rationale.json",
            "release_gate_updated": session_dir / "export" / "release_gate_decision.json",
            "replay_updated": session_dir / "replay" / "replay_index.json",
            "quality_updated": session_dir / "derived" / "quality" / "quality_timeline.json",
            "alarms_updated": session_dir / "derived" / "alarms" / "alarm_timeline.json",
            "frame_sync_updated": session_dir / "derived" / "sync" / "frame_sync_index.json",
            "scan_protocol_updated": session_dir / "derived" / "preview" / "scan_protocol.json",
            "annotations_updated": session_dir / "raw" / "ui" / "annotations.jsonl",
            "command_trace_updated": session_dir / "raw" / "ui" / "command_journal.jsonl",
            "lineage_updated": session_dir / "meta" / "lineage.json",
            "resume_state_updated": session_dir / "meta" / "resume_state.json",
            "resume_decision_updated": session_dir / "meta" / "resume_decision.json",
            "recovery_report_updated": session_dir / "export" / "recovery_report.json",
            "operator_incident_report_updated": session_dir / "export" / "operator_incident_report.json",
            "incidents_updated": session_dir / "derived" / "incidents" / "session_incidents.json",
        }
        changed_topics: list[str] = []
        events: list[dict[str, Any]] = []
        signature_parts = [str(session_dir)]
        for topic, path in watched.items():
            signature = "missing"
            if path.exists():
                stat = path.stat()
                signature = f"{path.name}:{stat.st_mtime_ns}:{stat.st_size}"
                signature_parts.append(signature)
            previous = self._topic_signatures.get(topic)
            if previous != signature:
                self._topic_signatures[topic] = signature
                if previous is not None:
                    changed_topics.append(topic)
                    events.append(
                        EventEnvelope(
                            topic=topic,
                            payload={"session_id": session_id or session_dir.name, "path": str(path)},
                            session_id=session_id or session_dir.name,
                            category="session",
                            delivery="event",
                            ts_ns=now_ns(),
                        ).to_message()
                    )
        signature = "|".join(signature_parts)
        if signature != self._last_signature:
            self._last_signature = signature
            if changed_topics:
                events.append(
                    EventEnvelope(
                        topic="artifact_ready",
                        payload={"session_id": session_id or session_dir.name, "changed_topics": changed_topics},
                        session_id=session_id or session_dir.name,
                        category="session",
                        delivery="must_deliver",
                    ).to_message()
                )
            events.append(
                EventEnvelope(
                    topic="session_product_update",
                    payload={"session_id": session_id or session_dir.name, "signature": signature, "changed": True, "changed_topics": changed_topics},
                    session_id=session_id or session_dir.name,
                    category="session",
                    delivery="event",
                ).to_message()
            )
        return events
