from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.session_intelligence.product_contracts import SessionIntelligenceProductBundle


class SessionIntelligenceArtifactWriter:
    """Persist materialized session-intelligence products to canonical paths."""

    def persist(self, service, session_dir: Path, products: SessionIntelligenceProductBundle) -> None:
        session_id = str(products.lineage.get("session_id", session_dir.name))
        service._write_json(session_dir / "derived" / "events" / "event_log_index.json", products.event_log_index)
        service._write_json(session_dir / "derived" / "recovery" / "recovery_decision_timeline.json", products.recovery_decision_timeline)
        service._write_json(session_dir / "meta" / "resume_decision.json", products.resume_decision)
        service._write_json(session_dir / "derived" / "session" / "contract_consistency.json", products.contract_consistency)
        service._write_json(session_dir / "derived" / "planning" / "selected_execution_rationale.json", products.selected_execution_rationale)
        service._write_json(session_dir / "derived" / "session" / "command_policy_snapshot.json", products.command_policy_snapshot)
        service._write_json(session_dir / "derived" / "session" / "contract_kernel_diff.json", products.contract_kernel_diff)
        service._write_json(session_dir / "derived" / "events" / "event_delivery_summary.json", products.event_delivery_summary)
        service._write_json(session_dir / "export" / "release_gate_decision.json", products.release_gate_decision)
        service._write_json(session_dir / "derived" / "session" / "control_plane_snapshot.json", products.control_plane_snapshot)
        service._write_json(session_dir / "derived" / "session" / "control_authority_snapshot.json", products.control_authority_snapshot)
        service._write_json(session_dir / "derived" / "events" / "bridge_observability_report.json", products.bridge_observability_report)
        service._write_json(session_dir / "derived" / "session" / "artifact_registry_snapshot.json", products.artifact_registry_snapshot)
        _ = session_id
