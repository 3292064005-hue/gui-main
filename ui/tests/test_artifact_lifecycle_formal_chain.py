from __future__ import annotations

from spine_ultrasound_ui.core.artifact_lifecycle_registry import iter_artifact_lifecycle_specs
from spine_ultrasound_ui.core.artifact_schema_registry import schema_for_artifact


FORMAL_SCOPES = {'dataset_export', 'training', 'export'}


def test_formal_dataset_export_training_artifacts_are_release_required_and_materialized() -> None:
    formal_specs = [spec for spec in iter_artifact_lifecycle_specs() if spec.evidence_chain_scope in FORMAL_SCOPES]
    assert formal_specs
    for spec in formal_specs:
        assert spec.required_for_release is True
        assert 'placeholder' not in spec.materialization_policy.lower()
        assert spec.producer_symbols
        assert spec.consumer_symbols
        assert schema_for_artifact(spec.artifact_name)


def test_required_dataset_export_training_chain_is_registered() -> None:
    names = {spec.artifact_name for spec in iter_artifact_lifecycle_specs()}
    assert {
        'dataset_export_manifest',
        'lamina_center_dataset_case',
        'uca_dataset_case',
        'training_bridge_model_ready_input_index',
        'nnunet_conversion_manifest',
        'training_backend_request',
        'training_model_package',
        'session_report',
        'qa_pack',
        'release_evidence_pack',
    }.issubset(names)
