from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from spine_ultrasound_ui.training.runtime_adapters.keypoint_runtime_adapter import KeypointRuntimeAdapter
from spine_ultrasound_ui.utils import now_text


class FrameAnatomyBenchmarkService:
    """Benchmark exported raw-frame anatomy-point packages against pixel labels."""

    def evaluate_many(self, runtime_target: str | Path, case_specs: list[dict[str, Any]]) -> dict[str, Any]:
        adapter = KeypointRuntimeAdapter()
        adapter.load(runtime_target)
        details: list[dict[str, Any]] = []
        point_errors: list[float] = []
        detected_count = 0
        stable_count = 0
        for case in case_specs:
            detail = self._evaluate_case(adapter, dict(case))
            details.append(detail)
            if detail['detected']:
                detected_count += 1
                point_errors.extend(detail['point_errors_px'])
            if detail['stable']:
                stable_count += 1
        summary = {
            'case_count': len(details),
            'detected_case_count': detected_count,
            'stable_case_count': stable_count,
            'detection_rate': round(detected_count / len(details), 6) if details else 0.0,
            'stable_detection_rate': round(stable_count / len(details), 6) if details else 0.0,
            'mean_error_px': round(float(np.mean(point_errors)), 6) if point_errors else 0.0,
            'max_error_px': round(float(np.max(point_errors)), 6) if point_errors else 0.0,
        }
        return {
            'generated_at': now_text(),
            'runtime_model': dict(adapter.runtime_model),
            'details': details,
            'summary': summary,
        }

    def _evaluate_case(self, adapter: KeypointRuntimeAdapter, case: dict[str, Any]) -> dict[str, Any]:
        image_path = Path(str(case.get('image_path', '') or ''))
        if not image_path.exists():
            raise FileNotFoundError(image_path)
        with Image.open(image_path) as image:
            array = np.asarray(image.convert('L'), dtype=np.float32)
        low = float(array.min()) if array.size else 0.0
        high = float(array.max()) if array.size else 0.0
        normalized = (array - low) / (high - low) if array.size and high > low else np.zeros_like(array, dtype=np.float32)
        result = adapter.infer({'image': normalized}, {'task_variant': 'frame_anatomy_points'})
        left_gt = dict(case.get('left', {}) or {})
        right_gt = dict(case.get('right', {}) or {})
        errors = []
        if result.get('left') and left_gt:
            errors.append(float(np.hypot(float(result['left']['x_px']) - float(left_gt.get('x_px', 0.0)), float(result['left']['y_px']) - float(left_gt.get('y_px', 0.0)))))
        if result.get('right') and right_gt:
            errors.append(float(np.hypot(float(result['right']['x_px']) - float(right_gt.get('x_px', 0.0)), float(result['right']['y_px']) - float(right_gt.get('y_px', 0.0)))))
        return {
            'case_id': str(case.get('case_id', image_path.stem) or image_path.stem),
            'detected': bool(result.get('left') and result.get('right')),
            'stable': bool(result.get('stable', False)),
            'point_errors_px': [round(value, 6) for value in errors],
            'result': result,
        }
