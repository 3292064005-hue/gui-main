from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.services.headless_session_products_reader import HeadlessSessionProductsReader
from spine_ultrasound_ui.services.headless_telemetry_cache import HeadlessTelemetryCache
from spine_ultrasound_ui.services.session_evidence_seal_service import SessionEvidenceSealService
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService


def _reader(tmp_path: Path) -> HeadlessSessionProductsReader:
    session_dir = tmp_path / 'session'
    (session_dir / 'export').mkdir(parents=True)
    (session_dir / 'replay').mkdir(parents=True)
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'derived' / 'sync').mkdir(parents=True)
    (session_dir / 'raw' / 'ui').mkdir(parents=True)
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps({'session_id': 'S1', 'artifacts': {}}), encoding='utf-8')
    (session_dir / 'export' / 'session_report.json').write_text(json.dumps({'session_id': 'S1', 'quality_summary': {'avg_quality_score': 0.9}}), encoding='utf-8')
    (session_dir / 'replay' / 'replay_index.json').write_text(json.dumps({'session_id': 'S1'}), encoding='utf-8')
    (session_dir / 'derived' / 'sync' / 'frame_sync_index.json').write_text(json.dumps({'rows': [{'usable': True, 'frame_id': 1, 'quality_score': 0.8, 'contact_confidence': 0.7, 'segment_id': 0, 'ts_ns': 1}], 'summary': {'usable_ratio': 1.0}}), encoding='utf-8')
    (session_dir / 'raw' / 'ui' / 'annotations.jsonl').write_text(json.dumps({'data': {'kind': 'manual_review_note', 'message': 'check'}}) + '\n', encoding='utf-8')
    telemetry_cache = HeadlessTelemetryCache()
    return HeadlessSessionProductsReader(
        telemetry_cache=telemetry_cache,
        resolve_session_dir=lambda: session_dir,
        current_session_id=lambda: 'S1',
        manifest_reader=lambda p=None: json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8')),
        json_reader=lambda path: json.loads(path.read_text(encoding='utf-8')),
        json_if_exists_reader=lambda path: json.loads(path.read_text(encoding='utf-8')) if path.exists() else {},
        jsonl_reader=lambda path: [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()] if path.exists() else [],
        status_reader=lambda: {'execution_state': 'AUTO_READY'},
        derive_recovery_state=lambda core: 'IDLE',
        command_policy_catalog=lambda: {'policies': []},
        integrity_service=SessionIntegrityService(),
        session_intelligence=SessionIntelligenceService(),
        evidence_seal_service=SessionEvidenceSealService(),
    )


def test_headless_session_products_reader_current_session(tmp_path: Path) -> None:
    reader = _reader(tmp_path)
    current = reader.current_session()
    assert current['session_id'] == 'S1'
    assert current['report_available'] is True
    assert current['replay_available'] is True


def test_headless_session_products_reader_assessment(tmp_path: Path) -> None:
    reader = _reader(tmp_path)
    assessment = reader.current_assessment()
    assert assessment['session_id'] == 'S1'
    assert assessment['requires_manual_review'] is True
    assert assessment['evidence_frames'][0]['frame_id'] == 1
