from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState
from spine_ultrasound_ui.core.postprocess_job_manager import PostprocessJobManager
from spine_ultrasound_ui.services.algorithms import PluginExecutor, PluginPlane, PluginRegistry
from spine_ultrasound_ui.services.session_products_authority_surface import SessionProductsAuthoritySurface
from spine_ultrasound_ui.services.assessment import (
    AssessmentArtifactWriter,
    AssessmentEvidenceRenderer,
    AssessmentInputBuilder,
    CobbMeasurementService,
    LaminaPairingService,
    UCAMeasurementService,
    VertebraTiltService,
    VPISliceSelectorService,
)
from spine_ultrasound_ui.services.diagnostics_pack_service import DiagnosticsPackService
from spine_ultrasound_ui.services.frame_sync_indexer import FrameSyncIndexer
from spine_ultrasound_ui.services.qa_pack_service import QAPackService
from spine_ultrasound_ui.services.reconstruction import (
    BoneFeatureSegmentationService,
    ReconstructionArtifactWriter,
    ReconstructionInputBuilder,
    SpineCurveReconstructionService,
)
from spine_ultrasound_ui.services.datasets import AnnotationManifestBuilder, SessionExportService
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_analytics import SessionAnalyticsService
from spine_ultrasound_ui.services.pressure_analysis_service import PressureAnalysisService
from spine_ultrasound_ui.services.ultrasound_analysis_service import UltrasoundAnalysisService
from spine_ultrasound_ui.utils import now_text
from spine_ultrasound_ui.core.postprocess.preprocess_stage import PreprocessStage
from spine_ultrasound_ui.core.postprocess.reconstruct_stage import ReconstructStage
from spine_ultrasound_ui.core.postprocess.report_stage import ReportStage
from spine_ultrasound_ui.core.postprocess.export_stage import ExportStage
from spine_ultrasound_ui.core.postprocess.stage_registry import iter_stage_specs
from spine_ultrasound_ui.core.postprocess.stage_contracts import PostprocessStageStatusBundle
from spine_ultrasound_ui.core.postprocess.service_mixin import PostprocessServiceMixin

POSTPROCESS_STAGE_MANIFEST_RELATIVE_PATH = "derived/postprocess/postprocess_stage_manifest.json"


class PostprocessService(PostprocessServiceMixin):
    def __init__(self, exp_manager: ExperimentManager):
        self.exp_manager = exp_manager
        self.plugins = PluginPlane()
        self.plugin_registry = PluginRegistry(self.plugins.all_plugins())
        self.plugin_executor = PluginExecutor()
        self.qa_pack_service = QAPackService()
        self.diagnostics_service = DiagnosticsPackService()
        self.analytics = SessionAnalyticsService(exp_manager.root)
        self.sync_indexer = FrameSyncIndexer()
        self.pressure_analysis_service = PressureAnalysisService()
        self.ultrasound_analysis_service = UltrasoundAnalysisService()
        self.integrity_service = SessionIntegrityService()
        self.reconstruction_input_builder = ReconstructionInputBuilder()
        self.reconstruction_service = SpineCurveReconstructionService()
        self.reconstruction_writer = ReconstructionArtifactWriter(exp_manager)
        self.assessment_input_builder = AssessmentInputBuilder()
        self.lamina_pairing_service = LaminaPairingService()
        self.vertebra_tilt_service = VertebraTiltService()
        self.cobb_measurement_service = CobbMeasurementService(
            lamina_pairing_service=self.lamina_pairing_service,
            vertebra_tilt_service=self.vertebra_tilt_service,
        )
        self.vpi_slice_selector_service = VPISliceSelectorService()
        self.bone_feature_segmentation_service = BoneFeatureSegmentationService()
        self.uca_measurement_service = UCAMeasurementService()
        self.assessment_evidence_renderer = AssessmentEvidenceRenderer()
        self.assessment_writer = AssessmentArtifactWriter(exp_manager)
        self.authoritative_artifact_reader = SessionProductsAuthoritySurface()
        self.dataset_export_service = SessionExportService()
        self.annotation_manifest_builder = AnnotationManifestBuilder()
        self.job_manager = PostprocessJobManager()
        self.preprocess_stage = PreprocessStage()
        self.reconstruct_stage = ReconstructStage()
        self.report_stage = ReportStage()
        self.export_stage = ExportStage()
        self.stage_specs = iter_stage_specs()

    def preprocess(self, session_dir: Path | None) -> CapabilityStatus:
        return self.preprocess_stage.run(self, session_dir)

    def reconstruct(self, session_dir: Path | None) -> CapabilityStatus:
        return self.reconstruct_stage.run(self, session_dir)

    def assess(self, session_dir: Path | None) -> CapabilityStatus:
        return self.report_stage.run(self, session_dir)

    def export_lamina_center_case(self, session_dir: Path | None, output_root: Path) -> dict[str, Any]:
        """Export a locked session into the lamina-center dataset tree.

        Args:
            session_dir: Locked session directory.
            output_root: Dataset root receiving the exported case.

        Returns:
            Export manifest payload for the written case.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` is ``None`` or missing.

        Boundary behaviour:
            The method first materializes reconstruction artifacts so exported
            cases always contain authoritative reconstruction evidence.
        """
        if session_dir is None:
            raise FileNotFoundError('no active session')
        self._build_reconstruction_artifacts(session_dir)
        return self.dataset_export_service.export_lamina_center_case(session_dir, output_root)

    def export_uca_case(self, session_dir: Path | None, output_root: Path) -> dict[str, Any]:
        """Export a locked session into the UCA dataset tree.

        Args:
            session_dir: Locked session directory.
            output_root: Dataset root receiving the exported case.

        Returns:
            Export manifest payload for the written case.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` is ``None`` or missing.

        Boundary behaviour:
            Reconstruction and assessment artifacts are materialized before the
            export so UCA annotation tooling receives the latest authoritative
            VPI and auxiliary measurement payloads.
        """
        if session_dir is None:
            raise FileNotFoundError('no active session')
        self._build_reconstruction_artifacts(session_dir)
        self._build_assessment_artifacts(session_dir)
        return self.dataset_export_service.export_uca_case(session_dir, output_root)

    def build_annotation_manifest(self, dataset_root: Path) -> dict[str, Any]:
        """Build a patient-level annotation manifest for exported datasets.

        Args:
            dataset_root: Dataset root to scan.

        Returns:
            Annotation manifest payload.

        Raises:
            FileNotFoundError: Raised when the dataset root does not exist.
        """
        return self.annotation_manifest_builder.build(dataset_root)

    def refresh_all(self, session_dir: Path | None) -> dict[str, CapabilityStatus]:
        statuses = PostprocessStageStatusBundle.from_mapping(self.export_stage.run(self, session_dir))
        if session_dir is not None:
            target = self._build_stage_manifest(session_dir, statuses)
            self.exp_manager.append_artifact(session_dir, "postprocess_stage_manifest", target)
        return statuses.to_dict()

    def describe_pipeline(self) -> list[dict[str, Any]]:
        """Return the declarative postprocess pipeline specification.

        Returns:
            Ordered list of postprocess stage descriptors.

        Raises:
            No exceptions are raised.
        """
        return [spec.to_dict() for spec in self.stage_specs]

