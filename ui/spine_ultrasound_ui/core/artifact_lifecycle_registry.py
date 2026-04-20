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

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['consumers'] = list(self.consumers)
        return payload


_ARTIFACT_LIFECYCLE_REGISTRY: tuple[ArtifactLifecycleSpec, ...] = (
    ArtifactLifecycleSpec('scan_plan', 'experiment_manager', ('runtime_executor', 'replay', 'report_builder'), 'workflow_lock', True, 'materialized'),
    ArtifactLifecycleSpec('device_readiness', 'session_lock_service', ('session_governance', 'release_gate'), 'workflow_lock', True, 'materialized'),
    ArtifactLifecycleSpec('patient_registration', 'session_lock_service', ('planning', 'report_builder', 'dataset_export'), 'workflow_lock', True, 'materialized'),
    ArtifactLifecycleSpec('localization_readiness', 'session_lock_service', ('session_governance', 'release_gate'), 'workflow_lock', True, 'materialized'),
    ArtifactLifecycleSpec('source_frame_set', 'session_lock_service', ('replay', 'dataset_export'), 'workflow_lock', True, 'materialized'),
    ArtifactLifecycleSpec('scan_protocol', 'session_lock_service', ('runtime_executor', 'review_surface'), 'workflow_lock', True, 'materialized'),
    ArtifactLifecycleSpec('reconstruction_summary', 'reconstruction_stage', ('assessment_stage', 'dataset_export', 'qa_pack'), 'reconstruction', False, 'materialized'),
    ArtifactLifecycleSpec('spine_curve', 'reconstruction_stage', ('assessment_stage', 'dataset_export', 'benchmark'), 'reconstruction', False, 'materialized_or_sidecar'),
    ArtifactLifecycleSpec('uca_measurement', 'assessment_stage', ('dataset_export', 'benchmark', 'qa_pack'), 'assessment', False, 'materialized_or_sidecar'),
    ArtifactLifecycleSpec('prior_assisted_cobb', 'assessment_stage', ('benchmark', 'dataset_export'), 'assessment', False, 'sidecar_only'),
    ArtifactLifecycleSpec('release_gate_decision', 'session_intelligence', ('release_evidence', 'session_governance'), 'session_finalize', True, 'materialized'),
    ArtifactLifecycleSpec('artifact_registry_snapshot', 'session_intelligence', ('release_evidence', 'session_governance'), 'session_finalize', True, 'materialized'),
)


def iter_artifact_lifecycle_specs() -> tuple[ArtifactLifecycleSpec, ...]:
    return _ARTIFACT_LIFECYCLE_REGISTRY


def lifecycle_spec_for_artifact(name: str) -> ArtifactLifecycleSpec | None:
    normalized = str(name or '').strip()
    for item in _ARTIFACT_LIFECYCLE_REGISTRY:
        if item.artifact_name == normalized:
            return item
    return None
