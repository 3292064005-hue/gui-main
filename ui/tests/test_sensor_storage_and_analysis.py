from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtGui import QPixmap

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.force_control_config import load_force_control_config
def _device_roster() -> dict:
    return {
        "robot": {"online": True, "fresh": True, "fact_source": "test"},
        "camera": {"online": True, "fresh": True, "fact_source": "test"},
        "ultrasound": {"online": True, "fresh": True, "fact_source": "test"},
        "pressure": {"online": True, "fresh": True, "fact_source": "test"},
    }


from spine_ultrasound_ui.services.localization_strategies import FallbackRegistrationStrategy


def _build_locked_session(tmp_path: Path):
    controller = AppController(tmp_path, MockBackend(tmp_path / 'runtime'))
    record = controller.session_facade.create_experiment(controller.config, note='sensor-analysis test')
    controller.session_service.current_experiment = record
    controller.workflow_artifacts.has_experiment = True
    controller.workflow_artifacts.experiment_id = record.exp_id
    controller.localization_result = FallbackRegistrationStrategy().run(controller.session_service.current_experiment, controller.config, device_roster=_device_roster())
    controller.workflow_artifacts.localization = controller.localization_result.status
    controller.workflow_artifacts.localization_review_required = True
    controller.workflow_artifacts.localization_source_type = 'fallback_simulated'
    controller.approve_localization_review()
    controller.generate_path()
    controller.session_service.ensure_locked(
        controller.config,
        controller.telemetry.device_roster(),
        controller.execution_scan_plan,
        protocol_version=1,
        safety_thresholds=load_force_control_config(),
        device_health_snapshot=controller.backend_link_snapshot.get('devices', {}),
        patient_registration=controller.localization_result.patient_registration,
        localization_result=controller.localization_result,
        control_authority=controller.backend_link_snapshot.get('control_plane', {}).get('control_authority', {}),
    )
    assert controller.session_service.current_session_dir is not None
    return controller, controller.session_service.current_session_dir


def test_pressure_samples_and_ultrasound_frames_are_recorded(tmp_path: Path) -> None:
    controller, session_dir = _build_locked_session(tmp_path)
    controller.session_service.record_pressure_sample(
        {
            'pressure_current': 1.8,
            'desired_force_n': 1.5,
            'pressure_error': 0.3,
            'contact_confidence': 0.91,
            'contact_mode': 'STABLE_CONTACT',
            'recommended_action': 'SCAN',
            'contact_stable': True,
            'force_status': 'ok',
            'force_source': 'mock_force_sensor',
            'wrench_n': [0.0, 0.0, 1.8, 0.0, 0.0, 0.0],
        },
        123,
    )
    pixmap = QPixmap(64, 48)
    pixmap.fill()
    controller.session_service.record_ultrasound_pixmap(pixmap, source_ts_ns=456, metadata={'frame_id': 7, 'segment_id': 2, 'quality_score': 0.88, 'pressure_current': 1.7, 'contact_mode': 'SCAN'})
    pressure_lines = (session_dir / 'raw' / 'pressure' / 'samples.jsonl').read_text(encoding='utf-8').splitlines()
    ultrasound_lines = (session_dir / 'raw' / 'ultrasound' / 'index.jsonl').read_text(encoding='utf-8').splitlines()
    assert pressure_lines
    assert ultrasound_lines
    pressure_entry = json.loads(pressure_lines[-1])
    ultrasound_entry = json.loads(ultrasound_lines[-1])
    assert pressure_entry['data']['force_source'] == 'mock_force_sensor'
    assert ultrasound_entry['data']['frame_id'] == 7
    assert ultrasound_entry['data']['segment_id'] == 2


def test_postprocess_builds_pressure_and_ultrasound_analysis(tmp_path: Path) -> None:
    controller, session_dir = _build_locked_session(tmp_path)
    for idx in range(3):
        controller.session_service.record_pressure_sample(
            {
                'pressure_current': 1.4 + idx * 0.2,
                'desired_force_n': 1.5,
                'pressure_error': -0.1 + idx * 0.2,
                'contact_confidence': 0.8,
                'contact_mode': 'STABLE_CONTACT',
                'recommended_action': 'SCAN',
                'contact_stable': True,
                'force_status': 'ok',
                'force_source': 'mock_force_sensor',
                'wrench_n': [0.0, 0.0, 1.4 + idx * 0.2, 0.0, 0.0, 0.0],
            },
            1000 + idx,
        )
    pixmap = QPixmap(64, 48)
    pixmap.fill()
    for idx in range(2):
        controller.session_service.record_ultrasound_pixmap(pixmap, source_ts_ns=2000 + idx, metadata={'frame_id': idx + 1, 'segment_id': 1, 'quality_score': 0.9, 'pressure_current': 1.6, 'contact_mode': 'SCAN'})
    controller.session_service.record_quality_feedback({'quality_score': 0.9, 'image_quality': 0.9, 'feature_confidence': 0.9}, 2000)
    controller.postprocess_service.preprocess(session_dir)
    controller.postprocess_service.reconstruct(session_dir)
    controller.postprocess_service.assess(session_dir)
    pressure_timeline = json.loads((session_dir / 'derived' / 'pressure' / 'pressure_sensor_timeline.json').read_text(encoding='utf-8'))
    ultrasound_metrics = json.loads((session_dir / 'derived' / 'ultrasound' / 'ultrasound_frame_metrics.json').read_text(encoding='utf-8'))
    pressure_analysis = json.loads((session_dir / 'export' / 'pressure_analysis.json').read_text(encoding='utf-8'))
    ultrasound_analysis = json.loads((session_dir / 'export' / 'ultrasound_analysis.json').read_text(encoding='utf-8'))
    report = json.loads((session_dir / 'export' / 'session_report.json').read_text(encoding='utf-8'))
    assert pressure_timeline['summary']['sample_count'] >= 3
    assert ultrasound_metrics['summary']['frame_count'] >= 2
    assert 'recommendations' in pressure_analysis
    assert 'recommendations' in ultrasound_analysis
    assert 'pressure_summary' in report
    assert 'ultrasound_summary' in report
