import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.core.session_recorders import JsonlRecorder
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.training.runtime_adapters.common import resolve_model_package


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _seed_recorded_evidence(controller: AppController, session_dir: Path) -> None:
    session_id = session_dir.name
    ts0 = 1_700_000_000_000_000_000
    pixmap = QPixmap(64, 48)
    pixmap.fill()

    robot_recorder = JsonlRecorder(session_dir / 'raw' / 'core' / 'robot_state.jsonl', session_id)
    contact_recorder = JsonlRecorder(session_dir / 'raw' / 'core' / 'contact_state.jsonl', session_id)
    progress_recorder = JsonlRecorder(session_dir / 'raw' / 'core' / 'scan_progress.jsonl', session_id)

    for idx in range(3):
        ts_ns = ts0 + idx * 10_000_000
        controller.session_service.record_camera_pixmap(
            pixmap,
            source_ts_ns=ts_ns,
            metadata={'frame_id': f'camera-{idx + 1}', 'provider_mode': 'synthetic'},
        )
        controller.session_service.record_ultrasound_pixmap(
            pixmap,
            source_ts_ns=ts_ns,
            metadata={
                'frame_id': f'us-{idx + 1}',
                'segment_id': idx + 1,
                'quality_score': 0.92,
                'pressure_current': 1.6,
                'contact_mode': 'SCAN',
                'pixel_spacing_mm': [0.5, 0.5],
            },
        )
        controller.session_service.record_quality_feedback(
            {'quality_score': 0.92, 'image_quality': 0.9, 'feature_confidence': 0.91},
            ts_ns,
        )
        controller.session_service.record_pressure_sample(
            {
                'pressure_current': 1.6,
                'desired_force_n': 1.5,
                'pressure_error': 0.1,
                'contact_confidence': 0.87,
                'contact_mode': 'STABLE_CONTACT',
                'recommended_action': 'SCAN',
                'contact_stable': True,
                'force_status': 'ok',
                'force_source': 'mock_force_sensor',
                'wrench_n': [0.0, 0.0, 1.6, 0.0, 0.0, 0.0],
            },
            ts_ns,
        )
        robot_recorder.append(
            {
                'powered': True,
                'operate_mode': 'automatic',
                'joint_pos': [0.05 * idx, 0.1, -0.1, 0.2, 0.0, 0.3],
                'joint_torque': [0.0, 0.0, 0.1, 0.0, 0.0, 0.0],
                'tcp_pose': {
                    'x': 110.0 + idx * 18.0,
                    'y': -10.42 + (idx - 1) * 0.8,
                    'z': 205.0,
                    'rx': 180.0,
                    'ry': 0.0,
                    'rz': 90.0,
                },
            },
            source_ts_ns=ts_ns,
        )
        contact_recorder.append(
            {
                'mode': 'STABLE_CONTACT',
                'confidence': 0.87,
                'pressure_current': 1.6,
                'recommended_action': 'SCAN',
                'contact_stable': True,
                'force_status': 'ok',
                'force_source': 'mock_force_sensor',
            },
            source_ts_ns=ts_ns,
        )
        progress_recorder.append(
            {
                'execution_state': 'SCANNING',
                'active_segment': idx + 1,
                'path_index': idx,
                'progress_pct': 25.0 + idx * 25.0,
                'frame_id': f'us-{idx + 1}',
            },
            source_ts_ns=ts_ns,
        )


def _build_session(tmp_path: Path) -> Path:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_procedure()
    controller.safe_retreat()
    controller.save_results()
    controller.export_summary()
    assert controller.session_service.current_session_dir is not None
    _seed_recorded_evidence(controller, controller.session_service.current_session_dir)
    controller.run_preprocess()
    controller.run_reconstruction()
    assert controller.session_service.current_session_dir is not None
    return controller.session_service.current_session_dir


def test_frame_sync_and_reconstruction_input_expose_measured_pose(tmp_path: Path) -> None:
    session_dir = _build_session(tmp_path)
    frame_sync = json.loads((session_dir / 'derived' / 'sync' / 'frame_sync_index.json').read_text(encoding='utf-8'))
    reconstruction_input = json.loads((session_dir / 'derived' / 'reconstruction' / 'reconstruction_input_index.json').read_text(encoding='utf-8'))

    assert frame_sync['summary']['robot_alignment_available'] is True
    assert frame_sync['summary']['pose_valid_count'] > 0
    assert frame_sync['summary']['reconstructable_count'] > 0
    first_row = frame_sync['rows'][0]
    assert first_row['pose_valid'] is True
    assert first_row['sync_valid'] is True
    assert first_row['robot_pose_source'] in {'tcp_pose_dict', 'tcp_pose_list', 'tcp_pose_matrix'}

    pose_row = reconstruction_input['selected_rows'][0]
    assert pose_row['robot_pose_mm_rad']
    assert pose_row['patient_pose_mm_rad']
    assert 'missing_robot_pose' not in pose_row['manual_review_reasons']
    assert reconstruction_input['selection_mode'] == 'authoritative_measured_rows'
    assert reconstruction_input['gates']['authoritative_pose_available'] is True


def test_pose_resampled_vpi_and_runtime_packages_are_materialized(tmp_path: Path) -> None:
    session_dir = _build_session(tmp_path)
    reconstruction_summary = json.loads((session_dir / 'derived' / 'reconstruction' / 'reconstruction_summary.json').read_text(encoding='utf-8'))
    evidence = json.loads((session_dir / 'derived' / 'reconstruction' / 'reconstruction_evidence.json').read_text(encoding='utf-8'))

    assert reconstruction_summary['runtime_models']['bone_segmentation']['package_name'] == 'lamina_seg_baseline'
    assert reconstruction_summary['runtime_models']['lamina_keypoint']['package_name'] == 'lamina_keypoint_baseline'
    assert evidence['vpi_stats']['projection_source'] == 'pose_resampled_ultrasound'
    assert len(evidence['row_geometry']) > 0

    seg_package = resolve_model_package('configs/models/lamina_seg_runtime.yaml')
    keypoint_package = resolve_model_package('configs/models/lamina_keypoint_runtime.yaml')
    rank_package = resolve_model_package('configs/models/uca_rank_runtime.yaml')
    assert seg_package['meta']['package_hash']
    assert keypoint_package['meta']['package_hash']
    assert rank_package['meta']['package_hash']
