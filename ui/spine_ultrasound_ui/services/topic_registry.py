from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.services.role_matrix import RoleMatrix
from spine_ultrasound_ui.utils import now_text


@dataclass
class TopicMeta:
    topic: str
    category: str
    delivery: str
    description: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic": self.topic,
            "category": self.category,
            "delivery": self.delivery,
            "description": self.description,
        }


class TopicRegistry:
    def __init__(self, role_matrix: RoleMatrix | None = None) -> None:
        self._topics: dict[str, TopicMeta] = {}
        self.role_matrix = role_matrix or RoleMatrix()
        self._bootstrap()

    def _bootstrap(self) -> None:
        for topic, category, delivery, description in [
            ("core_state", "runtime", "telemetry", "Execution state, recovery state, active segment, and plan hash."),
            ("robot_state", "runtime", "telemetry", "Robot joint, TCP, force, and controller health snapshot."),
            ("contact_state", "runtime", "telemetry", "Contact mode, confidence, and pressure band state."),
            ("scan_progress", "runtime", "telemetry", "Scan progress and active waypoint state."),
            ("device_health", "runtime", "telemetry", "Per-device liveness and freshness signals."),
            ("safety_status", "runtime", "telemetry", "Interlocks, safety gates, and recovery reasons."),
            ("recording_status", "runtime", "telemetry", "Recorder state and dropped sample counters."),
            ("quality_feedback", "runtime", "telemetry", "Online quality metrics and resample hints."),
            ("alarm_event", "runtime", "telemetry", "Alarm and auto-action events from the control core."),
            ("session_product_update", "session", "event", "Session-level product signature and change summary."),
            ("artifact_ready", "session", "event", "Artifact materialization or replacement notification."),
            ("manifest_updated", "session", "event", "Manifest refresh notification."),
            ("readiness_updated", "session", "event", "Device readiness artifact update."),
            ("profile_updated", "session", "event", "Robot profile artifact update."),
            ("registration_updated", "session", "event", "Patient registration artifact update."),
            ("scan_protocol_updated", "session", "event", "Scan protocol artifact update."),
            ("report_updated", "session", "event", "Session report refresh notification."),
            ("compare_updated", "session", "event", "Session compare refresh notification."),
            ("trends_updated", "session", "event", "Session trend refresh notification."),
            ("qa_pack_updated", "session", "event", "QA pack refresh notification."),
            ("diagnostics_updated", "session", "event", "Diagnostics pack refresh notification."),
            ("replay_updated", "session", "event", "Replay index refresh notification."),
            ("quality_updated", "session", "event", "Quality timeline refresh notification."),
            ("alarms_updated", "session", "event", "Alarm timeline refresh notification."),
            ("frame_sync_updated", "session", "event", "Frame sync index refresh notification."),
            ("annotations_updated", "session", "event", "Annotation journal refresh notification."),
            ("command_trace_updated", "session", "event", "Command trace refresh notification."),
            ("lineage_updated", "session", "event", "Session lineage refresh notification."),
            ("resume_state_updated", "session", "event", "Resume state refresh notification."),
            ("resume_decision_updated", "session", "event", "Resume decision refresh notification."),
            ("recovery_report_updated", "session", "event", "Recovery report refresh notification."),
            ("operator_incident_report_updated", "session", "event", "Operator incident report refresh notification."),
            ("incidents_updated", "session", "event", "Structured incident timeline refresh notification."),
            ("event_log_index_updated", "session", "persisted", "Event log index refresh notification."),
            ("event_delivery_summary_updated", "session", "persisted", "Event delivery continuity summary refresh notification."),
            ("selected_execution_rationale_updated", "session", "persisted", "Selected execution rationale refresh notification."),
            ("release_gate_updated", "session", "persisted", "Release gate decision refresh notification."),
            ("recovery_timeline_updated", "session", "persisted", "Recovery decision timeline refresh notification."),
            ("resume_attempts_updated", "session", "persisted", "Resume attempts timeline refresh notification."),
            ("resume_outcomes_updated", "session", "persisted", "Resume execution outcomes refresh notification."),
            ("command_policy_updated", "session", "persisted", "Command state policy snapshot refresh notification."),
            ("command_policy_snapshot_updated", "session", "persisted", "Command policy decision snapshot refresh notification."),
            ("contract_kernel_diff_updated", "session", "persisted", "Contract kernel diff refresh notification."),
            ("contract_consistency_updated", "session", "persisted", "Contract consistency snapshot refresh notification."),
            ("release_evidence_updated", "session", "persisted", "Release evidence pack refresh notification."),
            ("dead_letter_updated", "session", "persisted", "Delivery dead-letter snapshot refresh notification."),
        ]:
            self._topics[topic] = TopicMeta(topic, category, delivery, description)

    def ensure(self, topic: str, *, category: str = "runtime", delivery: str = "telemetry", description: str | None = None) -> None:
        if topic not in self._topics:
            self._topics[topic] = TopicMeta(topic, category, delivery, description or topic.replace('_', ' '))

    def catalog(self) -> dict[str, Any]:
        return {
            "generated_at": now_text(),
            "topics": [meta.to_dict() for meta in sorted(self._topics.values(), key=lambda item: (item.category, item.topic))],
            "roles": self.role_matrix.catalog()["roles"],
            "command_groups": self.role_matrix.catalog()["command_groups"],
        }
