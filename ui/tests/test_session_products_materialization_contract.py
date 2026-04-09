from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.services.headless_session_products_reader import HeadlessSessionProductsReader
from spine_ultrasound_ui.services.headless_telemetry_cache import HeadlessTelemetryCache
from spine_ultrasound_ui.services.session_evidence_seal_service import SessionEvidenceSealService
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_intelligence_service import SessionIntelligenceService


class _NoBuildSessionIntelligence(SessionIntelligenceService):
    def __init__(self) -> None:
        super().__init__()
        self.build_all_calls = 0

    def build_all(self, session_dir: Path):  # type: ignore[override]
        self.build_all_calls += 1
        raise AssertionError('read surfaces must not build session intelligence products')


def _reader(session_dir: Path, intelligence: SessionIntelligenceService | None = None) -> HeadlessSessionProductsReader:
    return HeadlessSessionProductsReader(
        telemetry_cache=HeadlessTelemetryCache(),
        resolve_session_dir=lambda: session_dir,
        current_session_id=lambda: json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8')).get('session_id', session_dir.name),
        manifest_reader=lambda p=None: json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8')),
        json_reader=lambda path: json.loads(path.read_text(encoding='utf-8')),
        json_if_exists_reader=lambda path: json.loads(path.read_text(encoding='utf-8')) if path.exists() else {},
        jsonl_reader=lambda path: [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()] if path.exists() else [],
        status_reader=lambda: {'execution_state': 'AUTO_READY'},
        derive_recovery_state=lambda core: 'IDLE',
        command_policy_catalog=lambda: {'policies': []},
        integrity_service=SessionIntegrityService(),
        session_intelligence=intelligence or SessionIntelligenceService(),
        evidence_seal_service=SessionEvidenceSealService(),
    )


def test_missing_lineage_is_reported_without_read_side_materialization(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps({'session_id': 'S1', 'artifact_registry': {}}), encoding='utf-8')
    intelligence = _NoBuildSessionIntelligence()
    reader = _reader(session_dir, intelligence)
    lineage = reader.current_lineage()
    assert lineage['session_id'] == 'S1'
    assert lineage['product'] == 'lineage'
    assert lineage['materialization_state'] == 'not_materialized'
    assert intelligence.build_all_calls == 0


def test_current_session_exposes_registry_driven_materialization_states(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'export').mkdir(parents=True)
    (session_dir / 'derived' / 'sync').mkdir(parents=True)
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps({'session_id': 'S1', 'artifact_registry': {}}), encoding='utf-8')
    (session_dir / 'export' / 'session_report.json').write_text(json.dumps({'quality_summary': {}}), encoding='utf-8')
    (session_dir / 'derived' / 'sync' / 'frame_sync_index.json').write_text(json.dumps({'summary': {'usable_ratio': 1.0}}), encoding='utf-8')
    reader = _reader(session_dir)
    current = reader.current_session()
    assert current['assessment_available'] is False
    assert current['assessment_status'] == 'legacy_fallback_only'
    assert current['materialization_contract']['read_side_effects'] is False
    lineage = next(item for item in current['session_intelligence_products'] if item['product'] == 'lineage')
    assert lineage['materialization_state'] == 'not_materialized'
    assert lineage['read_policy'] == 'materialized_only'


def test_current_assessment_distinguishes_legacy_fallback_only(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'export').mkdir(parents=True)
    (session_dir / 'derived' / 'sync').mkdir(parents=True)
    (session_dir / 'raw' / 'ui').mkdir(parents=True)
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps({'session_id': 'S1', 'robot_profile': {'robot_model': 'xmate3'}}), encoding='utf-8')
    (session_dir / 'export' / 'session_report.json').write_text(json.dumps({'quality_summary': {'avg_quality_score': 0.9}, 'open_issues': []}), encoding='utf-8')
    (session_dir / 'derived' / 'sync' / 'frame_sync_index.json').write_text(json.dumps({'rows': [{'usable': True, 'frame_id': 1, 'quality_score': 0.8, 'contact_confidence': 0.7, 'segment_id': 0, 'ts_ns': 1}], 'summary': {'usable_ratio': 1.0}}), encoding='utf-8')
    reader = _reader(session_dir)
    assessment = reader.current_assessment()
    assert assessment['assessment_state'] == 'legacy_fallback_only'
    assert assessment['materialization_state'] == 'legacy_fallback_only'
    assert assessment['curve_candidate']['status'] == 'legacy_fallback_only'
    assert assessment['authoritative_available'] is False



def test_current_session_reports_prior_assisted_authoritative_status(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True)
    (session_dir / 'derived' / 'assessment').mkdir(parents=True)
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps({'session_id': 'S1', 'artifact_registry': {}, 'robot_profile': {'robot_model': 'xmate3'}}), encoding='utf-8')
    (session_dir / 'derived' / 'assessment' / 'assessment_summary.json').write_text(json.dumps({'closure_verdict': 'prior_assisted'}), encoding='utf-8')
    (session_dir / 'derived' / 'assessment' / 'prior_assisted_cobb.json').write_text(json.dumps({'angle_deg': 12.5}), encoding='utf-8')
    reader = _reader(session_dir)
    current = reader.current_session()
    assert current['assessment_available'] is True
    assert current['assessment_status'] == 'prior_assisted_ready'
    assert current['assessment_authoritative_available'] is True
