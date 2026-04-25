import json
import os
from pathlib import Path

import numpy as np
from PIL import Image

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.core.session_recorders import JsonlRecorder
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.training.runtime_adapters.keypoint_runtime_adapter import KeypointRuntimeAdapter


def _reset_app() -> None:
    app = QApplication.instance()
    if app is None:
        return
    if hasattr(app, 'quit'):
        try:
            app.quit()
        except Exception:
            pass
    if hasattr(app, 'processEvents'):
        try:
            app.processEvents()
        except Exception:
            pass
    if hasattr(type(app), '_instance'):
        type(app)._instance = None


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def _make_ultrasound_image(width: int, height: int, left_x: int, right_x: int, y: int) -> np.ndarray:
    image = np.zeros((height, width), dtype=np.uint8)
    # low background texture
    for row in range(height):
        image[row, :] = np.clip(20 + row, 0, 255)
    for center_x in (left_x, right_x):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                yy = min(max(y + dy, 0), height - 1)
                xx = min(max(center_x + dx, 0), width - 1)
                image[yy, xx] = 255
        # posterior shadow cue
        shadow_start = min(height - 1, y + 1)
        image[shadow_start:, max(center_x - 1, 0):min(center_x + 2, width)] = 0
    return image


def _paint_recorded_ultrasound_frames(session_dir: Path) -> None:
    index_path = session_dir / 'raw' / 'ultrasound' / 'index.jsonl'
    entries = [json.loads(line) for line in index_path.read_text(encoding='utf-8').splitlines() if line.strip()]
    positions = [(18, 46, 18), (20, 44, 19), (22, 42, 20)]
    for entry, (left_x, right_x, y_px) in zip(entries, positions):
        frame_path = Path(entry['data']['frame_path'])
        frame = _make_ultrasound_image(64, 48, left_x, right_x, y_px)
        Image.fromarray(frame, mode='L').save(frame_path)


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
                'quality_score': 0.95,
                'pressure_current': 1.8,
                'contact_mode': 'SCAN',
                'pixel_spacing_mm': [0.6, 0.6],
            },
        )
        controller.session_service.record_quality_feedback(
            {'quality_score': 0.95, 'image_quality': 0.93, 'feature_confidence': 0.94},
            ts_ns,
        )
        controller.session_service.record_pressure_sample(
            {
                'pressure_current': 1.8,
                'desired_force_n': 1.6,
                'pressure_error': 0.1,
                'contact_confidence': 0.9,
                'contact_mode': 'STABLE_CONTACT',
                'recommended_action': 'SCAN',
                'contact_stable': True,
                'force_status': 'ok',
                'force_source': 'mock_force_sensor',
                'wrench_n': [0.0, 0.0, 1.8, 0.0, 0.0, 0.0],
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
                'confidence': 0.9,
                'pressure_current': 1.8,
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
    _paint_recorded_ultrasound_frames(session_dir)


def _build_session(tmp_path: Path) -> Path:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    try:
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
        return controller.session_service.current_session_dir
    finally:
        controller.shutdown()
        _reset_app()


def test_frame_point_runtime_adapter_tracks_stable_raw_ultrasound_points() -> None:
    adapter = KeypointRuntimeAdapter()
    adapter.load('configs/models/frame_anatomy_keypoint_runtime.yaml')
    image_a = _make_ultrasound_image(64, 48, 18, 46, 18).astype(np.float32) / 255.0
    image_b = _make_ultrasound_image(64, 48, 20, 44, 19).astype(np.float32) / 255.0

    first = adapter.infer({'image': image_a}, {'task_variant': 'frame_anatomy_points', 'quality_score': 0.95, 'contact_confidence': 0.9})
    second = adapter.infer(
        {'image': image_b},
        {
            'task_variant': 'frame_anatomy_points',
            'quality_score': 0.95,
            'contact_confidence': 0.9,
            'previous_pair': {
                'left': {'x_px': first['left']['x_px'], 'y_px': first['left']['y_px']},
                'right': {'x_px': first['right']['x_px'], 'y_px': first['right']['y_px']},
            },
        },
    )

    assert first['left']['x_px'] < first['right']['x_px']
    assert second['left']['x_px'] < second['right']['x_px']
    assert second['stable'] is True
    assert second['stability_score'] >= 0.55


def test_reconstruction_emits_frame_level_anatomy_points_and_uses_them_as_primary_source(tmp_path: Path) -> None:
    session_dir = _build_session(tmp_path)
    frame_points_path = session_dir / 'derived' / 'reconstruction' / 'frame_anatomy_points.json'
    lamina_path = session_dir / 'derived' / 'reconstruction' / 'lamina_candidates.json'
    summary_path = session_dir / 'derived' / 'reconstruction' / 'reconstruction_summary.json'
    assert frame_points_path.exists()

    frame_points = json.loads(frame_points_path.read_text(encoding='utf-8'))
    lamina_candidates = json.loads(lamina_path.read_text(encoding='utf-8'))
    summary = json.loads(summary_path.read_text(encoding='utf-8'))

    assert frame_points['summary']['stable_frame_count'] >= 2
    assert frame_points['summary']['point_count'] >= 4
    assert lamina_candidates['summary']['primary_source'] == 'frame_anatomy_points'
    assert summary['lamina_candidate_source'] == 'frame_anatomy_points'
    assert summary['runtime_models']['frame_anatomy_keypoint']['package_name'] == 'frame_anatomy_keypoint_exported'
    assert summary['runtime_models']['frame_anatomy_keypoint']['benchmark_gate']['passed'] is True
