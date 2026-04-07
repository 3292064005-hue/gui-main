from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from spine_ultrasound_ui.services.reconstruction.closure_profile import is_preweight_profile, load_reconstruction_profile, profile_name
from spine_ultrasound_ui.training.runtime_adapters.keypoint_runtime_adapter import KeypointRuntimeAdapter
from spine_ultrasound_ui.utils import now_text


class FrameAnatomyPointInferenceService:
    """Infer stable anatomical lamina points directly from raw ultrasound frames.

    The service upgrades reconstruction from projection-only point extraction to
    a primary per-frame inference chain. It consumes synchronized raw ultrasound
    frames, runs the configured runtime adapter on each frame, then stabilizes
    left/right landmarks across time before mapping them into patient-frame
    coordinates.
    """

    def __init__(
        self,
        *,
        min_confidence: float = 0.2,
        min_stability: float = 0.55,
        method_version: str = 'frame_anatomy_point_inference_v1',
        runtime_adapter: KeypointRuntimeAdapter | None = None,
        runtime_model_config: str | Path | None = None,
    ) -> None:
        self.min_confidence = float(min_confidence)
        self.min_stability = float(min_stability)
        self.method_version = method_version
        self.runtime_adapter = runtime_adapter
        self.profile = load_reconstruction_profile()
        self.runtime_model_config = runtime_model_config or os.environ.get(
            'SPINE_FRAME_ANATOMY_KEYPOINT_RUNTIME_CONFIG',
            Path(__file__).resolve().parents[3] / 'configs' / 'models' / 'frame_anatomy_keypoint_runtime.yaml',
        )
        self.runtime_load_error = ''
        self._try_load_runtime_adapter()

    def infer(self, input_index: dict[str, Any]) -> dict[str, Any]:
        """Infer anatomical landmark pairs from raw ultrasound frames.

        Args:
            input_index: Reconstruction input payload containing synchronized
                rows, patient-frame probe poses, and per-frame ultrasound paths.

        Returns:
            Serializable payload containing frame-level points, stable pairs,
            and runtime model identity.

        Raises:
            ValueError: Raised when configured thresholds are invalid.

        Boundary behaviour:
            Missing runtime packages or unreadable frames do not abort the
            reconstruction chain. The service instead returns explicit degraded
            status together with per-frame manual-review reasons so downstream
            aggregation can select a projection-based fallback.
        """
        if self.min_confidence < 0.0 or self.min_stability < 0.0:
            raise ValueError('confidence and stability thresholds must be non-negative')
        rows = [dict(item) for item in input_index.get('selected_rows', input_index.get('rows', [])) if isinstance(item, dict)]
        session_id = str(input_index.get('session_id', '') or '')
        if not rows:
            return {
                'generated_at': now_text(),
                'session_id': session_id,
                'method_version': self.method_version,
                'points': [],
                'stable_pairs': [],
                'summary': {
                    'frame_count': 0,
                    'detected_frame_count': 0,
                    'stable_frame_count': 0,
                    'point_count': 0,
                    'primary_source': 'raw_ultrasound_frame_model',
                    'manual_review_reasons': ['no_reconstruction_rows'],
                },
                'runtime_model': self._with_profile_metadata(self._fallback_runtime_model()),
            }

        runtime_model = self._fallback_runtime_model()
        previous_pair: dict[str, dict[str, float]] = {}
        points: list[dict[str, Any]] = []
        stable_pairs: list[dict[str, Any]] = []
        point_confidences: list[float] = []
        stability_scores: list[float] = []
        detected_frames = 0

        for row_index, row in enumerate(rows, start=1):
            frame_id = str(row.get('frame_id', f'frame_{row_index:06d}') or f'frame_{row_index:06d}')
            frame_path = Path(str(row.get('ultrasound_frame_path', '') or ''))
            manual_review_reasons = [str(item) for item in list(row.get('manual_review_reasons', [])) if str(item)]
            if not frame_path.exists():
                manual_review_reasons.append('missing_ultrasound_frame')
                stable_pairs.append(self._empty_pair(row, frame_id, manual_review_reasons))
                continue
            image = self._load_frame(frame_path)
            if image.size == 0:
                manual_review_reasons.append('empty_ultrasound_frame')
                stable_pairs.append(self._empty_pair(row, frame_id, manual_review_reasons))
                continue
            result = None
            if self.runtime_adapter is not None and self.runtime_adapter.is_loaded:
                try:
                    result = self.runtime_adapter.infer(
                        {'image': image},
                        {
                            'task_variant': 'frame_anatomy_points',
                            'previous_pair': previous_pair,
                            'frame_meta': dict(row.get('ultrasound_frame_meta', {})),
                            'quality_score': float(row.get('quality_score', 0.0) or 0.0),
                            'contact_confidence': float(row.get('contact_confidence', 0.0) or 0.0),
                        },
                    )
                    runtime_model = dict(result.get('runtime_model', runtime_model))
                except Exception as exc:  # pragma: no cover - runtime failure path
                    manual_review_reasons.append(f'frame_model_inference_failed:{type(exc).__name__}')
            if result is None:
                result = self._fallback_infer(image, previous_pair)
            pair = self._normalize_pair(row, frame_id, image.shape, result, manual_review_reasons)
            if pair['detected']:
                detected_frames += 1
                previous_pair = {
                    'left': {'x_px': float(pair['left']['x_px']), 'y_px': float(pair['left']['y_px'])},
                    'right': {'x_px': float(pair['right']['x_px']), 'y_px': float(pair['right']['y_px'])},
                }
                point_confidences.extend([
                    float(pair['left']['confidence'] or 0.0),
                    float(pair['right']['confidence'] or 0.0),
                ])
                stability_scores.append(float(pair['stability_score'] or 0.0))
                points.extend([dict(pair['left']), dict(pair['right'])])
            stable_pairs.append(pair)

        summary_reasons = self._unique_reasons(
            [reason for pair in stable_pairs for reason in pair.get('manual_review_reasons', [])]
        )
        if not points:
            summary_reasons.append('no_frame_level_anatomy_points')
        runtime_model = self._with_profile_metadata(runtime_model)
        return {
            'generated_at': now_text(),
            'session_id': session_id,
            'method_version': self.method_version,
            'points': points,
            'stable_pairs': stable_pairs,
            'summary': {
                'frame_count': len(rows),
                'detected_frame_count': detected_frames,
                'stable_frame_count': sum(1 for pair in stable_pairs if bool(pair.get('stable', False))),
                'point_count': len(points),
                'avg_confidence': round(sum(point_confidences) / len(point_confidences), 6) if point_confidences else 0.0,
                'avg_stability_score': round(sum(stability_scores) / len(stability_scores), 6) if stability_scores else 0.0,
                'primary_source': 'raw_ultrasound_frame_model',
                'runtime_profile': profile_name(self.profile),
                'manual_review_reasons': self._unique_reasons(summary_reasons),
            },
            'runtime_model': runtime_model,
        }

    def _normalize_pair(
        self,
        row: dict[str, Any],
        frame_id: str,
        image_shape: tuple[int, int],
        result: dict[str, Any],
        manual_review_reasons: list[str],
    ) -> dict[str, Any]:
        left = dict(result.get('left', {}))
        right = dict(result.get('right', {}))
        detected = bool(left and right)
        pair_reasons = list(manual_review_reasons)
        if not detected:
            pair_reasons.append('frame_anatomy_points_missing')
            return self._empty_pair(row, frame_id, pair_reasons)

        frame_meta = dict(row.get('ultrasound_frame_meta', {}))
        spacing = self._pixel_spacing_mm(frame_meta)
        patient_pose = dict(row.get('patient_pose_mm_rad', {}))
        stable = bool(result.get('stable', False))
        stability_score = float(result.get('stability_score', 0.0) or 0.0)
        if stability_score < self.min_stability:
            pair_reasons.append('frame_point_stability_below_threshold')
        point_payloads = []
        for side, payload in (('left', left), ('right', right)):
            confidence = float(payload.get('confidence', 0.0) or 0.0)
            if confidence < self.min_confidence:
                pair_reasons.append(f'{side}_point_confidence_below_threshold')
            point_payloads.append(
                self._build_point_payload(
                    row=row,
                    frame_id=frame_id,
                    side=side,
                    image_shape=image_shape,
                    detection=payload,
                    pixel_spacing_mm=spacing,
                    patient_pose=patient_pose,
                    stable=stable,
                    stability_score=stability_score,
                    pair_manual_review_reasons=pair_reasons,
                )
            )
        pair_stable = stable and stability_score >= self.min_stability and all(
            float(point.get('confidence', 0.0) or 0.0) >= self.min_confidence for point in point_payloads
        )
        if not pair_stable:
            pair_reasons.append('frame_pair_not_stable')
        left_payload, right_payload = point_payloads
        return {
            'pair_id': f'{frame_id}_pair',
            'frame_id': frame_id,
            'segment_id': int(row.get('segment_id', 0) or 0),
            'detected': True,
            'stable': pair_stable,
            'stability_score': round(stability_score, 6),
            'manual_review_reasons': self._unique_reasons(pair_reasons),
            'left': left_payload,
            'right': right_payload,
        }

    def _build_point_payload(
        self,
        *,
        row: dict[str, Any],
        frame_id: str,
        side: str,
        image_shape: tuple[int, int],
        detection: dict[str, Any],
        pixel_spacing_mm: tuple[float, float],
        patient_pose: dict[str, Any],
        stable: bool,
        stability_score: float,
        pair_manual_review_reasons: list[str],
    ) -> dict[str, Any]:
        height, width = image_shape
        x_px = int(np.clip(round(float(detection.get('x_px', 0.0) or 0.0)), 0, max(width - 1, 0)))
        y_px = int(np.clip(round(float(detection.get('y_px', 0.0) or 0.0)), 0, max(height - 1, 0)))
        spacing_x_mm, spacing_y_mm = pixel_spacing_mm
        lateral_offset_mm = (x_px - ((width - 1) / 2.0)) * spacing_x_mm
        depth_mm = y_px * spacing_y_mm
        x_mm = float(patient_pose.get('y', 0.0) or 0.0) + lateral_offset_mm
        y_mm = float(patient_pose.get('x', 0.0) or 0.0)
        z_mm = float(patient_pose.get('z', 0.0) or 0.0) + depth_mm
        instance_id = f'instance_{int(row.get("segment_id", 0) or 0):03d}_{int(row.get("row_index", 0) or 0):04d}'
        longitudinal_order = int(row.get('row_index', 0) or 0)
        return {
            'point_id': f'{frame_id}_{side}',
            'vertebra_id': f'segment_{int(row.get("segment_id", 0) or 0):03d}_{int(row.get("row_index", 0) or 0):04d}',
            'instance_id': instance_id,
            'longitudinal_order': longitudinal_order,
            'supporting_frames': [frame_id],
            'supporting_frame_count': 1,
            'pair_completeness': 1.0,
            'persistence_score': round(float(stability_score or 0.0), 6),
            'frame_id': frame_id,
            'segment_id': int(row.get('segment_id', 0) or 0),
            'side': side,
            'x_px': x_px,
            'y_px': y_px,
            'x_mm': round(x_mm, 6),
            'y_mm': round(y_mm, 6),
            'z_mm': round(z_mm, 6),
            'depth_mm': round(depth_mm, 6),
            'lateral_offset_mm': round(lateral_offset_mm, 6),
            'confidence': round(float(detection.get('confidence', 0.0) or 0.0), 6),
            'stable': bool(stable),
            'stability_score': round(float(stability_score or 0.0), 6),
            'pose_source': str(row.get('robot_pose_source', 'missing') or 'missing'),
            'manual_review_reasons': self._unique_reasons(pair_manual_review_reasons),
        }

    def _fallback_infer(self, image: np.ndarray, previous_pair: dict[str, dict[str, float]]) -> dict[str, Any]:
        payload = self.runtime_adapter.fallback_frame_points(image, previous_pair=previous_pair) if self.runtime_adapter is not None else {}
        return payload or {'left': {}, 'right': {}, 'stable': False, 'stability_score': 0.0}

    def _try_load_runtime_adapter(self) -> None:
        if is_preweight_profile(self.profile):
            self.runtime_adapter = None
            self.runtime_load_error = 'preweight_profile_uses_deterministic_baseline'
            return
        if self.runtime_adapter is None and self.runtime_model_config:
            self.runtime_adapter = KeypointRuntimeAdapter()
        if self.runtime_adapter is None or not self.runtime_model_config:
            return
        config_path = Path(str(self.runtime_model_config))
        if not config_path.exists():
            self.runtime_load_error = f'missing_runtime_model_config:{config_path}'
            return
        try:
            self.runtime_adapter.load(config_path)
        except Exception as exc:  # pragma: no cover - exercised by runtime failures
            self.runtime_load_error = f'{type(exc).__name__}:{exc}'

    @staticmethod
    def _load_frame(path: Path) -> np.ndarray:
        with Image.open(path) as image:
            array = np.asarray(image.convert('L'), dtype=np.float32)
        if array.size == 0:
            return np.zeros((0, 0), dtype=np.float32)
        low = float(array.min())
        high = float(array.max())
        if high <= low:
            return np.zeros_like(array, dtype=np.float32)
        return (array - low) / (high - low)

    @staticmethod
    def _pixel_spacing_mm(frame_meta: dict[str, Any]) -> tuple[float, float]:
        spacing = list(frame_meta.get('pixel_spacing_mm', []))
        if len(spacing) >= 2:
            return float(spacing[0] or 0.4), float(spacing[1] or 0.4)
        return 0.4, 0.4

    @staticmethod
    def _empty_pair(row: dict[str, Any], frame_id: str, manual_review_reasons: list[str]) -> dict[str, Any]:
        return {
            'pair_id': f'{frame_id}_pair',
            'frame_id': frame_id,
            'segment_id': int(row.get('segment_id', 0) or 0),
            'detected': False,
            'stable': False,
            'stability_score': 0.0,
            'manual_review_reasons': FrameAnatomyPointInferenceService._unique_reasons(manual_review_reasons),
            'left': {},
            'right': {},
        }

    def _fallback_runtime_model(self) -> dict[str, Any]:
        runtime_kind = 'deterministic_baseline' if is_preweight_profile(self.profile) else 'runtime_failure_fallback'
        backend = 'deterministic_baseline' if is_preweight_profile(self.profile) else 'inline_fallback'
        release_state = str(self.profile.get('profile_release_state', 'degraded') or 'degraded') if is_preweight_profile(self.profile) else 'degraded'
        return self._with_profile_metadata({
            'package_name': 'frame_anatomy_keypoint_preweight' if is_preweight_profile(self.profile) else 'frame_anatomy_inline_fallback',
            'backend': backend,
            'runtime_kind': runtime_kind,
            'release_state': release_state,
            'load_error': self.runtime_load_error,
        })

    def _with_profile_metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = dict(payload)
        model['runtime_profile'] = profile_name(self.profile)
        model['profile_release_state'] = str(self.profile.get('profile_release_state', 'research_validated') or 'research_validated')
        model['closure_mode'] = str(self.profile.get('closure_mode', 'runtime_optional') or 'runtime_optional')
        return model

    @staticmethod
    def _unique_reasons(values: list[str]) -> list[str]:
        ordered: list[str] = []
        for value in values:
            item = str(value or '').strip()
            if item and item not in ordered:
                ordered.append(item)
        return ordered
