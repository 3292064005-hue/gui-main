import json
from pathlib import Path

import numpy as np
from PIL import Image

from spine_ultrasound_ui.training.runtime_adapters.keypoint_runtime_adapter import KeypointRuntimeAdapter
from spine_ultrasound_ui.training.specs.frame_anatomy_keypoint_training_spec import FrameAnatomyKeypointTrainingSpec
from spine_ultrasound_ui.training.trainers.frame_anatomy_keypoint_trainer import FrameAnatomyKeypointTrainer


def _make_ultrasound_image(width: int, height: int, left_x: int, right_x: int, y: int) -> np.ndarray:
    image = np.zeros((height, width), dtype=np.uint8)
    for row in range(height):
        image[row, :] = np.clip(18 + row * 2, 0, 255)
    for center_x in (left_x, right_x):
        for dy in range(-2, 3):
            for dx in range(-2, 3):
                yy = min(max(y + dy, 0), height - 1)
                xx = min(max(center_x + dx, 0), width - 1)
                image[yy, xx] = 255
        shadow_start = min(height - 1, y + 1)
        image[shadow_start:, max(center_x - 1, 0):min(center_x + 2, width)] = 0
    return image


def test_exported_frame_anatomy_runtime_package_passes_benchmark_gate() -> None:
    adapter = KeypointRuntimeAdapter()
    adapter.load('configs/models/frame_anatomy_keypoint_runtime.yaml')
    runtime_model = adapter.runtime_model
    assert runtime_model['package_name'] == 'frame_anatomy_keypoint_exported'
    assert runtime_model['runtime_kind'] == 'exported_weight_template'
    assert runtime_model['benchmark_gate']['passed'] is True
    assert Path(runtime_model['runtime_model_path']).exists()


def test_exported_frame_anatomy_runtime_can_track_stable_points() -> None:
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
    assert first['left']['x_px'] == 18
    assert first['right']['x_px'] == 46
    assert second['stable'] is True
    assert second['stability_score'] >= 0.55


def test_benchmark_gate_blocks_runtime_when_thresholds_fail(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[1]
    package_dir = (repo_root / 'models' / 'frame_anatomy_keypoint').resolve()
    failing_config = tmp_path / 'frame_runtime_fail.yaml'
    failing_config.write_text(
        '\n'.join([
            f'package_dir: {package_dir}',
            'backend: numpy_template_export',
            f'runtime_model_path: {package_dir / "frame_anatomy_keypoint_weights.npz"}',
            f'benchmark_manifest: {package_dir / "benchmark_manifest.json"}',
            'required_release_state: research_validated',
            'require_benchmark_gate: true',
            'benchmark_thresholds:',
            '  max_mean_error_px: -0.01',
            '  max_max_error_px: -0.01',
            '  min_detection_rate: 1.01',
            '  min_stable_detection_rate: 1.01',
        ]),
        encoding='utf-8',
    )
    adapter = KeypointRuntimeAdapter()
    try:
        adapter.load(failing_config)
    except RuntimeError as exc:
        assert 'benchmark release gate failed' in str(exc)
    else:  # pragma: no cover
        raise AssertionError('expected failing release gate to raise RuntimeError')


def test_frame_anatomy_trainer_exports_weight_package(tmp_path: Path) -> None:
    frame_dir = tmp_path / 'frames'
    frame_dir.mkdir(parents=True)
    cases = []
    for idx, (left_x, right_x, y_px) in enumerate([(18, 46, 18), (20, 44, 19), (22, 42, 20)], start=1):
        image = _make_ultrasound_image(64, 48, left_x, right_x, y_px)
        image_path = frame_dir / f'case_{idx:03d}.png'
        Image.fromarray(image, mode='L').save(image_path)
        cases.append({
            'case_id': f'case_{idx:03d}',
            'image_path': str(image_path),
            'left': {'x_px': left_x, 'y_px': y_px},
            'right': {'x_px': right_x, 'y_px': y_px},
        })
    manifest_path = tmp_path / 'manifest.json'
    manifest_path.write_text(json.dumps({'cases': cases}, indent=2), encoding='utf-8')
    trainer = FrameAnatomyKeypointTrainer()
    spec = FrameAnatomyKeypointTrainingSpec(dataset_manifest=manifest_path, output_dir=tmp_path / 'output')
    training_result = trainer.train(spec)
    export = trainer.export_runtime_package(training_result, spec, package_dir=tmp_path / 'package')
    assert Path(export['runtime_model_path']).exists()
    assert Path(export['benchmark_manifest_path']).exists()
    adapter = KeypointRuntimeAdapter()
    adapter.load(tmp_path / 'package')
    assert adapter.runtime_model['runtime_kind'] == 'exported_weight_template'
