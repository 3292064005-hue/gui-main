from __future__ import annotations

from spine_ultrasound_ui.contracts.schema_validator import validate_payload_against_schema
from spine_ultrasound_ui.services.authoritative_artifact_reader import AuthoritativeArtifactReader


def test_authority_metadata_schema_validates_reader_payload() -> None:
    payload = AuthoritativeArtifactReader._build_authority_metadata(
        effective_status='prior_assisted',
        closure_verdict='prior_assisted',
        effective_source_path='derived/assessment/prior_assisted_cobb.json',
        used_sidecar=True,
        source_contamination_flags=['registration_prior_curve_used'],
    )
    validate_payload_against_schema(schema_name='session/authority_metadata_v1.schema.json', payload=payload)


def test_assessment_and_reconstruction_schemas_expose_authority_metadata() -> None:
    assessment_payload = {
        'session_id': 'S1',
        'method_version': 'v1',
        'cobb_angle_deg': 12.0,
        'confidence': 0.9,
        'requires_manual_review': False,
        'coordinate_frame': 'patient',
        'evidence_refs': [],
        'authority_metadata': {
            'source_class': 'authoritative',
            'authority_level': 'runtime_authoritative',
            'fallback_reason': '',
            'effective_source_path': 'derived/assessment/cobb_measurement.json',
            'sidecar_selected': False,
            'source_contamination_flags': [],
            'review_suitability': True,
        },
    }
    reconstruction_payload = {
        'session_id': 'S1',
        'method_version': 'v1',
        'coordinate_frame': 'patient',
        'points': [],
        'fit': {},
        'evidence_refs': [],
        'authority_metadata': {
            'source_class': 'prior_assisted',
            'authority_level': 'derived_prior_assisted',
            'fallback_reason': 'prior_assisted',
            'effective_source_path': 'derived/reconstruction/prior_assisted_curve.json',
            'sidecar_selected': True,
            'source_contamination_flags': ['registration_prior_curve_used'],
            'review_suitability': True,
        },
    }
    validate_payload_against_schema(schema_name='assessment_summary.schema.json', payload=assessment_payload)
    validate_payload_against_schema(schema_name='spine_curve.schema.json', payload=reconstruction_payload)
