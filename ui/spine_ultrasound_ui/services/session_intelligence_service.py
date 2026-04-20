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
from spine_ultrasound_ui.services.session_evidence_seal_service import SessionEvidenceSealService
from spine_ultrasound_ui.services.session_intelligence.lineage_builder import LineageBuilder
from spine_ultrasound_ui.services.session_intelligence.recovery_report_builder import RecoveryReportBuilder
from spine_ultrasound_ui.services.session_intelligence.resume_state_builder import ResumeStateBuilder
from spine_ultrasound_ui.services.session_intelligence.incident_report_builder import IncidentReportBuilder
from spine_ultrasound_ui.services.session_intelligence.release_artifact_builder import ReleaseArtifactBuilder
from spine_ultrasound_ui.services.session_intelligence.input_loader import SessionIntelligenceInputLoader
from spine_ultrasound_ui.services.session_intelligence.product_builder import SessionIntelligenceProductBuilder
from spine_ultrasound_ui.services.session_intelligence.artifact_writer import SessionIntelligenceArtifactWriter
from spine_ultrasound_ui.services.session_intelligence.registry import iter_product_specs
from spine_ultrasound_ui.services.session_intelligence.service_mixin import SessionIntelligenceServiceMixin


class SessionIntelligenceService(SessionIntelligenceServiceMixin):
    """Facade for session-intelligence product orchestration.

    The service now stages session-product generation through explicit read,
    derive, and write steps so callers can reason about inputs and side
    effects without changing the historical ``build_all`` public API.
    """

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
        self.evidence_seal = SessionEvidenceSealService()
        self.lineage_builder = LineageBuilder()
        self.recovery_builder = RecoveryReportBuilder()
        self.resume_state_builder = ResumeStateBuilder()
        self.incident_report_builder = IncidentReportBuilder()
        self.release_artifact_builder = ReleaseArtifactBuilder()
        self.input_loader = SessionIntelligenceInputLoader()
        self.product_builder = SessionIntelligenceProductBuilder()
        self.artifact_writer = SessionIntelligenceArtifactWriter()
        self.product_specs = iter_product_specs()

    def describe_products(self) -> list[dict[str, Any]]:
        """Return the declarative session-intelligence product registry.

        Returns:
            Ordered list of product descriptors.

        Raises:
            No exceptions are raised.
        """
        return [spec.to_dict() for spec in self.product_specs]

    def build_all(self, session_dir: Path) -> dict[str, Any]:
        """Build and persist all session-intelligence products.

        Args:
            session_dir: Session directory containing raw, derived, and export
                artifacts.

        Returns:
            Dictionary containing all generated session-intelligence products.

        Raises:
            FileNotFoundError: Required session artifacts are missing.
            json.JSONDecodeError: Persisted JSON/JSONL inputs are malformed.

        Boundary behavior:
            Existing product file names remain unchanged for backward
            compatibility; only the orchestration internals were staged.
        """
        inputs = self._load_inputs(session_dir)
        derived_products = self._build_products(session_dir, inputs)
        self._persist_products(session_dir, derived_products)
        return derived_products.to_dict()

    def _load_inputs(self, session_dir: Path):
        return self.input_loader.load(self, session_dir)

    def _build_products(self, session_dir: Path, inputs):
        return self.product_builder.build(self, session_dir, inputs)

    def _persist_products(self, session_dir: Path, products) -> None:
        self.artifact_writer.persist(self, session_dir, products)

