from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ArtifactLifecycleSpec:
    artifact_name: str
    producer: str
    consumers: tuple[str, ...]
    source_stage: str
    required_for_release: bool
    materialization_policy: str
    retention_tier: str
    producer_symbols: tuple[str, ...] = ()
    consumer_symbols: tuple[str, ...] = ()
    evidence_chain_scope: str = "session"

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['consumers'] = list(self.consumers)
        payload['producer_symbols'] = list(self.producer_symbols)
        payload['consumer_symbols'] = list(self.consumer_symbols)
        return payload


_ARTIFACT_LIFECYCLE_REGISTRY: tuple[ArtifactLifecycleSpec, ...] = (
    ArtifactLifecycleSpec('scan_plan', 'experiment_manager', ('runtime_executor', 'replay', 'report_builder'), 'workflow_lock', True, 'materialized', 'session_core', ('meta/scan_plan.json', 'append_artifact(session_dir, "scan_plan"'), ('current_scan_plan', 'meta/scan_plan.json')),
    ArtifactLifecycleSpec('device_readiness', 'session_lock_service', ('session_governance', 'release_gate'), 'workflow_lock', True, 'materialized', 'release_evidence', ('meta/device_readiness.json', 'build_device_readiness'), ('device_readiness.json', 'device_readiness')),
    ArtifactLifecycleSpec('patient_registration', 'session_lock_service', ('planning', 'report_builder', 'dataset_export'), 'workflow_lock', True, 'materialized', 'release_evidence', ('meta/patient_registration.json', 'patient_registration='), ('meta/patient_registration.json', 'patient_registration')),
    ArtifactLifecycleSpec('localization_readiness', 'session_lock_service', ('session_governance', 'release_gate'), 'workflow_lock', True, 'materialized', 'release_evidence', ('localization_readiness_hash', 'localization_readiness='), ('localization_readiness', 'session_governance')),
    ArtifactLifecycleSpec('source_frame_set', 'session_lock_service', ('replay', 'dataset_export'), 'workflow_lock', True, 'materialized', 'session_core', ('source_frame_set', 'source_frame_index'), ('source_frame_set', 'dataset_export')),
    ArtifactLifecycleSpec('scan_protocol', 'session_lock_service', ('runtime_executor', 'review_surface'), 'workflow_lock', True, 'materialized', 'session_core', ('derived/preview/scan_protocol.json', 'build_scan_protocol'), ('current_scan_protocol', 'scan_protocol_available')),
    ArtifactLifecycleSpec('reconstruction_summary', 'reconstruction_stage', ('assessment_stage', 'dataset_export', 'qa_pack'), 'reconstruction', False, 'materialized', 'derived_review', ('derived/reconstruction/reconstruction_summary.json', 'reconstruction_artifact_writer'), ('reconstruction_summary =', 'reconstruction_summary.json')),
    ArtifactLifecycleSpec('spine_curve', 'reconstruction_stage', ('assessment_stage', 'dataset_export', 'benchmark'), 'reconstruction', False, 'materialized_or_sidecar', 'derived_review', ('derived/reconstruction/spine_curve.json', 'spine_curve='), ('spine_curve_source_path', 'spine_curve.json')),
    ArtifactLifecycleSpec('uca_measurement', 'assessment_stage', ('dataset_export', 'benchmark', 'qa_pack'), 'assessment', False, 'materialized_or_sidecar', 'derived_review', ('uca_measurement', 'uca_measurement.json'), ('uca_measurement', 'dataset_export')),
    ArtifactLifecycleSpec('prior_assisted_cobb', 'assessment_stage', ('benchmark', 'dataset_export'), 'assessment', False, 'sidecar_only', 'derived_optional', ('prior_assisted_cobb', 'prior_assisted_curve'), ('prior_assisted_cobb', 'benchmark')),
    ArtifactLifecycleSpec('release_gate_decision', 'session_intelligence', ('release_evidence', 'session_governance'), 'session_finalize', True, 'materialized', 'release_evidence', ('release_gate_decision', 'release_gate_decision.json'), ('release_gate_decision', 'release_evidence')),
    ArtifactLifecycleSpec('artifact_registry_snapshot', 'session_intelligence', ('release_evidence', 'session_governance'), 'session_finalize', True, 'materialized', 'release_evidence', ('artifact_registry_snapshot', 'build_artifact_registry_snapshot'), ('artifact_registry_snapshot', 'release_evidence')),
    ArtifactLifecycleSpec('session_report', 'postprocess_report_stage', ('qa_pack', 'release_evidence_pack', 'dataset_export'), 'assessment', True, 'materialized', 'release_evidence', ('export/session_report.json', 'build_session_report'), ('session_report', 'release_evidence_pack'), 'export'),
    ArtifactLifecycleSpec('qa_pack', 'postprocess_report_stage', ('release_evidence_pack', 'review_surface'), 'assessment', True, 'materialized', 'release_evidence', ('export/qa_pack.json', 'build_qa_pack'), ('qa_pack', 'current_qa_pack'), 'export'),
    ArtifactLifecycleSpec('release_evidence_pack', 'release_evidence_pack_service', ('release_gate', 'truth_ledger'), 'session_finalize', True, 'materialized', 'release_evidence', ('export/release_evidence_pack.json', 'ReleaseEvidencePackService'), ('release_evidence_pack', 'release_evidence_pack_path'), 'export'),
    ArtifactLifecycleSpec('dataset_export_manifest', 'session_export_service', ('training_dataset_loaders', 'annotation_manifest', 'release_evidence'), 'dataset_export', True, 'materialized', 'dataset_evidence', ('export_manifest.json', '_write_export_manifest'), ('export_manifest.json', 'SessionExportService'), 'dataset_export'),
    ArtifactLifecycleSpec('lamina_center_dataset_case', 'session_export_service', ('lamina_center_training', 'nnunet_export', 'annotation_tools'), 'dataset_export', True, 'materialized', 'dataset_evidence', ('export_lamina_center_case', "dataset_role='lamina_center'"), ('LaminaCenterDataset', 'export_lamina_center_dataset'), 'dataset_export'),
    ArtifactLifecycleSpec('uca_dataset_case', 'session_export_service', ('uca_training', 'nnunet_export', 'annotation_tools'), 'dataset_export', True, 'materialized', 'dataset_evidence', ('export_uca_case', "dataset_role='uca'"), ('UCADataset', 'export_uca_bone_feature_dataset'), 'dataset_export'),
    ArtifactLifecycleSpec('training_bridge_model_ready_input_index', 'training_bridge', ('training', 'dataset_export'), 'reconstruction', True, 'materialized', 'dataset_evidence', ('training_bridge_model_ready_input_index', 'model_ready_input_index.json'), ('training_bridge_model_ready_input_index', 'training'), 'training'),
    ArtifactLifecycleSpec('nnunet_conversion_manifest', 'nnunet_dataset_export_service', ('nnunet_runner', 'training_backend_request'), 'training_export', True, 'materialized', 'training_evidence', ('conversion_manifest.json', 'export_lamina_center_dataset'), ('conversion_manifest_path', 'nnunet_runner'), 'training'),
    ArtifactLifecycleSpec('training_backend_request', 'training_backend_adapter', ('training_runner', 'release_evidence'), 'training', True, 'materialized', 'training_evidence', ('build_monai_lamina_keypoint_request', 'build_monai_uca_rank_request'), ('backend_payload', 'backend_training_request'), 'training'),
    ArtifactLifecycleSpec('training_model_package', 'model_export_service', ('runtime_adapters', 'release_evidence'), 'training_export', True, 'materialized', 'training_evidence', ('model_package', 'ModelExportService'), ('resolve_model_package', 'runtime_target'), 'training'),
)


def iter_artifact_lifecycle_specs() -> tuple[ArtifactLifecycleSpec, ...]:
    return _ARTIFACT_LIFECYCLE_REGISTRY


def lifecycle_spec_for_artifact(name: str) -> ArtifactLifecycleSpec | None:
    normalized = str(name or '').strip()
    for item in _ARTIFACT_LIFECYCLE_REGISTRY:
        if item.artifact_name == normalized:
            return item
    return None
