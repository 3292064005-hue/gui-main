import json
from pathlib import Path

from spine_ultrasound_ui.services.datasets.session_export_service import SessionExportService


def test_export_manifest_marks_placeholder_artifacts(tmp_path: Path):
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'derived' / 'reconstruction').mkdir(parents=True)
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps({'session_id': 'S1', 'experiment_id': 'E1'}), encoding='utf-8')
    (session_dir / 'meta' / 'patient_registration.json').write_text(json.dumps({'patient_id': 'P1'}), encoding='utf-8')
    output_root = tmp_path / 'dataset'
    payload = SessionExportService().export_uca_case(session_dir, output_root)
    assert payload['placeholder_artifact_count'] > 0
    manifest = json.loads((Path(payload['case_dir']) / 'export_manifest.json').read_text(encoding='utf-8'))
    assert manifest['integrity_state'] == 'placeholder_present'
    assert 'artifact_states' in manifest
    assert manifest['artifact_states']['uca_measurement']['placeholder_generated'] is True
