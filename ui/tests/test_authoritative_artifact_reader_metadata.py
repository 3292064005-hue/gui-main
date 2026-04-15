from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.services.authoritative_artifact_reader import AuthoritativeArtifactReader


def test_authoritative_artifact_reader_emits_authority_metadata_for_prior_assisted_payload(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session-1'
    (session_dir / 'derived' / 'assessment').mkdir(parents=True)
    (session_dir / 'derived' / 'assessment' / 'assessment_summary.json').write_text(
        json.dumps({'closure_verdict': 'prior_assisted', 'source_contamination_flags': ['registration_prior_curve_used']}),
        encoding='utf-8',
    )
    (session_dir / 'derived' / 'assessment' / 'prior_assisted_cobb.json').write_text(
        json.dumps({'angle_deg': 12.5}),
        encoding='utf-8',
    )
    reader = AuthoritativeArtifactReader()
    payload = reader.read_cobb_measurement(session_dir)
    metadata = payload['authority_metadata']
    assert metadata['source_class'] == 'prior_assisted'
    assert metadata['authority_level'] == 'derived_prior_assisted'
    assert metadata['sidecar_selected'] is True
    assert metadata['review_suitability'] is True
    assert metadata['effective_source_path'] == 'derived/assessment/prior_assisted_cobb.json'
