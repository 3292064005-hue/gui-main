from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService
from spine_ultrasound_ui.utils.truth_ledger_service import refresh_live_truth_ledger_from_artifacts


class SessionFinalizeService:
    """Materialize session-intelligence products into stable artifact paths."""

    def __init__(self, exp_manager: ExperimentManager, intelligence: SessionIntelligenceService) -> None:
        self.exp_manager = exp_manager
        self.intelligence = intelligence

    def refresh(self, session_dir: Path) -> dict[str, Path]:
        """Rebuild all session-intelligence products for a locked session.

        Args:
            session_dir: Locked session directory.

        Returns:
            Mapping from artifact name to materialized path.

        Raises:
            RuntimeError: Propagated when any downstream intelligence product
                fails to render.
        """
        products = self.intelligence.build_all(session_dir)
        targets = {
            "lineage": self.exp_manager.save_json_artifact(session_dir, "meta/lineage.json", products["lineage"]),
            "resume_state": self.exp_manager.save_json_artifact(session_dir, "meta/resume_state.json", products["resume_state"]),
            "resume_decision": self.exp_manager.save_json_artifact(session_dir, "meta/resume_decision.json", products["resume_decision"]),
            "resume_attempts": self.exp_manager.save_json_artifact(session_dir, "derived/session/resume_attempts.json", products["resume_attempts"]),
            "resume_attempt_outcomes": self.exp_manager.save_json_artifact(session_dir, "derived/session/resume_attempt_outcomes.json", products["resume_attempt_outcomes"]),
            "command_state_policy": self.exp_manager.save_json_artifact(session_dir, "derived/session/command_state_policy.json", products["command_state_policy"]),
            "command_policy_snapshot": self.exp_manager.save_json_artifact(session_dir, "derived/session/command_policy_snapshot.json", products["command_policy_snapshot"]),
            "contract_kernel_diff": self.exp_manager.save_json_artifact(session_dir, "derived/session/contract_kernel_diff.json", products["contract_kernel_diff"]),
            "recovery_report": self.exp_manager.save_json_artifact(session_dir, "export/recovery_report.json", products["recovery_report"]),
            "recovery_decision_timeline": self.exp_manager.save_json_artifact(session_dir, "derived/recovery/recovery_decision_timeline.json", products["recovery_decision_timeline"]),
            "operator_incident_report": self.exp_manager.save_json_artifact(session_dir, "export/operator_incident_report.json", products["operator_incident_report"]),
            "session_incidents": self.exp_manager.save_json_artifact(session_dir, "derived/incidents/session_incidents.json", products["session_incidents"]),
            "event_log_index": self.exp_manager.save_json_artifact(session_dir, "derived/events/event_log_index.json", products["event_log_index"]),
            "event_delivery_summary": self.exp_manager.save_json_artifact(session_dir, "derived/events/event_delivery_summary.json", products["event_delivery_summary"]),
            "selected_execution_rationale": self.exp_manager.save_json_artifact(session_dir, "derived/planning/selected_execution_rationale.json", products["selected_execution_rationale"]),
            "release_evidence_pack": self.exp_manager.save_json_artifact(session_dir, "export/release_evidence_pack.json", products["release_evidence_pack"]),
            "release_gate_decision": self.exp_manager.save_json_artifact(session_dir, "export/release_gate_decision.json", products["release_gate_decision"]),
            "contract_consistency": self.exp_manager.save_json_artifact(session_dir, "derived/session/contract_consistency.json", products["contract_consistency"]),
            "control_plane_snapshot": self.exp_manager.save_json_artifact(session_dir, "derived/session/control_plane_snapshot.json", products["control_plane_snapshot"]),
            "control_authority_snapshot": self.exp_manager.save_json_artifact(session_dir, "derived/session/control_authority_snapshot.json", products["control_authority_snapshot"]),
            "bridge_observability_report": self.exp_manager.save_json_artifact(session_dir, "derived/events/bridge_observability_report.json", products["bridge_observability_report"]),
            "artifact_registry_snapshot": self.exp_manager.save_json_artifact(session_dir, "derived/session/artifact_registry_snapshot.json", products["artifact_registry_snapshot"]),
            "session_evidence_seal": self.exp_manager.save_json_artifact(session_dir, "meta/session_evidence_seal.json", products["session_evidence_seal"]),
        }
        manifest_target = self._write_intelligence_manifest(session_dir, products, targets)
        targets["session_intelligence_manifest"] = manifest_target
        live_truth_ledger = refresh_live_truth_ledger_from_artifacts(
            session_dir,
            existing=self.exp_manager.load_manifest(session_dir).get("live_truth_ledger", {}),
        )
        live_truth_target = self.exp_manager.save_json_artifact(session_dir, "meta/live_truth_ledger.json", live_truth_ledger)
        targets["live_truth_ledger"] = live_truth_target
        for name, target in targets.items():
            self.exp_manager.append_artifact(session_dir, name, target)
        self.exp_manager.sync_canonical_manifest_fields(session_dir, live_truth_ledger=live_truth_ledger)
        return targets

    def _write_intelligence_manifest(self, session_dir: Path, products: dict[str, Any], targets: dict[str, Path]) -> Path:
        payload = {
            "generated_at": now_text(),
            "session_id": self.exp_manager.load_manifest(session_dir)["session_id"],
            "schema": "session/session_intelligence_manifest_v1.schema.json",
            "products": [
                {
                    **spec.to_dict(),
                    "materialized": spec.product in products and spec.product in targets,
                }
                for spec in self.intelligence.product_specs
            ],
        }
        return self.exp_manager.save_json_artifact(session_dir, "derived/session/session_intelligence_manifest.json", payload)
