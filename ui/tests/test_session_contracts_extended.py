from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend


def _build_session(tmp_path: Path) -> Path:
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_procedure()
    controller.pause_scan()
    controller.resume_scan()
    controller.safe_retreat()
    controller.save_results()
    controller.export_summary()
    controller.run_preprocess()
    controller.run_reconstruction()
    controller.run_assessment()
    assert controller.session_service.current_session_dir is not None
    return controller.session_service.current_session_dir


def test_manifest_contains_artifact_registry_and_processing_steps(tmp_path):
    session_dir = _build_session(tmp_path)
    manifest = json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8'))
    assert 'artifact_registry' in manifest
    assert 'processing_steps' in manifest
    assert manifest['artifact_registry']['qa_pack']['path'] == 'export/qa_pack.json'
    assert manifest['artifact_registry']['frame_sync_index']['path'] == 'derived/sync/frame_sync_index.json'
    assert any(step['step_id'] == 'assessment' for step in manifest['processing_steps'])


def test_extended_products_are_materialized(tmp_path):
    session_dir = _build_session(tmp_path)
    assert (session_dir / 'derived' / 'alarms' / 'alarm_timeline.json').exists()
    assert (session_dir / 'derived' / 'sync' / 'frame_sync_index.json').exists()
    assert (session_dir / 'export' / 'session_compare.json').exists()
    assert (session_dir / 'export' / 'session_trends.json').exists()
    assert (session_dir / 'export' / 'diagnostics_pack.json').exists()
    assert (session_dir / 'export' / 'qa_pack.json').exists()

    report = json.loads((session_dir / 'export' / 'session_report.json').read_text(encoding='utf-8'))
    replay = json.loads((session_dir / 'replay' / 'replay_index.json').read_text(encoding='utf-8'))
    quality = json.loads((session_dir / 'derived' / 'quality' / 'quality_timeline.json').read_text(encoding='utf-8'))
    alarms = json.loads((session_dir / 'derived' / 'alarms' / 'alarm_timeline.json').read_text(encoding='utf-8'))
    trends = json.loads((session_dir / 'export' / 'session_trends.json').read_text(encoding='utf-8'))
    diagnostics = json.loads((session_dir / 'export' / 'diagnostics_pack.json').read_text(encoding='utf-8'))
    frame_sync = json.loads((session_dir / 'derived' / 'sync' / 'frame_sync_index.json').read_text(encoding='utf-8'))

    assert 'session_overview' in report
    assert 'quality_summary' in report
    assert 'timeline' in replay
    assert 'annotation_segments' in replay
    assert 'coverage_ratio' in quality['summary']
    assert 'stale_threshold_ms' in quality['summary']
    assert 'events' in alarms
    assert 'history' in trends
    assert 'summary' in diagnostics
    assert 'summary' in frame_sync


def test_manifest_freezes_thresholds_and_artifact_checksums(tmp_path):
    session_dir = _build_session(tmp_path)
    manifest = json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8'))
    assert manifest['safety_thresholds']['stale_telemetry_ms'] > 0
    report_descriptor = manifest['artifact_registry']['session_report']
    assert report_descriptor['artifact_id'] == 'session_report'
    assert report_descriptor['checksum']
    quality = json.loads((session_dir / 'derived' / 'quality' / 'quality_timeline.json').read_text(encoding='utf-8'))
    assert quality['summary']['stale_threshold_ms'] == manifest['safety_thresholds']['stale_telemetry_ms']


def test_qa_pack_contains_trends_diagnostics_and_annotations(tmp_path):
    session_dir = _build_session(tmp_path)
    qa_pack = json.loads((session_dir / 'export' / 'qa_pack.json').read_text(encoding='utf-8'))
    assert 'trends' in qa_pack
    assert 'frame_sync' in qa_pack
    assert 'diagnostics' in qa_pack
    assert isinstance(qa_pack['annotations'], list)
