from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.core.artifact_path_policy import infer_dependencies, infer_source_stage
from spine_ultrasound_ui.core.artifact_schema_registry import schema_for_artifact
from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.core.postprocess_service import PostprocessService
from spine_ultrasound_ui.core.session_finalize_service import SessionFinalizeService
from spine_ultrasound_ui.core.session_service import SessionService
from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan
from spine_ultrasound_ui.models.session_model import ScanWaypoint
from spine_ultrasound_ui.services.release_evidence_pack_service import ReleaseEvidencePackService
from spine_ultrasound_ui.services.release_gate_decision_service import ReleaseGateDecisionService
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService


def test_artifact_registry_helpers_expose_stable_contracts() -> None:
    assert schema_for_artifact("release_gate_decision") == "runtime/release_gate_decision_v1.schema.json"
    assert infer_source_stage("frame_sync_index") == "reconstruction"
    assert infer_source_stage("cobb_measurement") == "assessment"
    assert infer_dependencies("reconstruction_summary") == ["spine_curve", "landmark_track", "reconstruction_input_index", "reconstruction_evidence"]
    assert infer_dependencies("release_evidence_pack") == [
        "contract_consistency",
        "session_integrity",
        "diagnostics_pack",
        "event_log_index",
        "recovery_decision_timeline",
        "session_report",
        "qa_pack",
    ]


def test_session_service_uses_wave45_helpers(tmp_path: Path) -> None:
    manager = ExperimentManager(tmp_path)
    service = SessionService(manager)
    assert service.lock_service.__class__.__name__ == "SessionLockService"
    assert service.recorder_service.__class__.__name__ == "SessionRecorderService"
    assert service.finalize_service.__class__.__name__ == "SessionFinalizeService"


def test_postprocess_service_exposes_stage_helpers(tmp_path: Path) -> None:
    service = PostprocessService(ExperimentManager(tmp_path))
    assert service.preprocess_stage.__class__.__name__ == "PreprocessStage"
    assert service.reconstruct_stage.__class__.__name__ == "ReconstructStage"
    assert service.report_stage.__class__.__name__ == "ReportStage"
    assert service.export_stage.__class__.__name__ == "ExportStage"


def test_release_services_use_split_helpers() -> None:
    evidence = ReleaseEvidencePackService()
    gate = ReleaseGateDecisionService()
    assert evidence.artifact_resolver.__class__.__name__ == "ReleaseArtifactResolver"
    assert evidence.evidence_index_builder.__class__.__name__ == "EvidenceIndexBuilder"
    assert gate.input_loader.__class__.__name__ == "ReleaseGateInputLoader"
    assert gate.policy_evaluator.__class__.__name__ == "ReleaseGatePolicyEvaluator"


def test_session_finalize_service_materializes_known_targets(tmp_path: Path) -> None:
    manager = ExperimentManager(tmp_path)
    intelligence = SessionIntelligenceService()
    finalize = SessionFinalizeService(manager, intelligence)
    locked = manager.lock_session(
        exp_id="EXP_2026_0001",
        config_snapshot=RuntimeConfig().to_dict(),
        device_roster={},
        software_version="test",
        build_id="test-build",
        scan_plan=ScanPlan(session_id="preview", plan_id="PLAN_PREVIEW", approach_pose=ScanWaypoint(0,0,0,0,0,0), retreat_pose=ScanWaypoint(0,0,0,0,0,0)),
    )
    session_dir = Path(locked["session_dir"])
    for rel in [
        "derived/alarms/alarm_timeline.json",
        "derived/quality/quality_timeline.json",
        "export/session_report.json",
        "export/summary.json",
        "raw/ui/command_journal.jsonl",
        "raw/ui/annotations.jsonl",
    ]:
        target = session_dir / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("{}" if target.suffix == ".json" else "", encoding="utf-8")
    targets = finalize.refresh(session_dir)
    assert "release_gate_decision" in targets
    assert targets["release_gate_decision"].exists()


def test_session_intelligence_uses_split_stage_helpers() -> None:
    intelligence = SessionIntelligenceService()
    assert intelligence.input_loader.__class__.__name__ == "SessionIntelligenceInputLoader"
    assert intelligence.product_builder.__class__.__name__ == "SessionIntelligenceProductBuilder"
    assert intelligence.artifact_writer.__class__.__name__ == "SessionIntelligenceArtifactWriter"
