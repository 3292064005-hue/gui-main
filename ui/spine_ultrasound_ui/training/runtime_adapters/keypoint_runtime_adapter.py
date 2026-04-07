from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.services.benchmark.runtime_model_release_gate_service import RuntimeModelReleaseGateService

from .common import resolve_model_package


class KeypointRuntimeAdapter:
    """Runtime adapter for segmentation-row and raw-frame keypoint packages.

    The adapter now supports two raw-frame modes:

    * ``deterministic_baseline`` for inline heuristics; and
    * ``exported_weight_template`` for genuine exported weight artifacts loaded
      from a standalone ``.npz`` package file.
    """

    def __init__(self) -> None:
        self._loaded = False
        self._meta: dict[str, Any] = {}
        self._parameters: dict[str, Any] = {}
        self._config: dict[str, Any] = {}
        self._runtime_weights: dict[str, np.ndarray] = {}

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    @property
    def runtime_model(self) -> dict[str, Any]:
        return dict(self._meta)

    def load(self, model_dir_or_config: str | Path) -> None:
        """Load a runtime package and enforce release-gate checks.

        Args:
            model_dir_or_config: Package directory or runtime config file.

        Raises:
            FileNotFoundError: Raised when package artifacts are missing.
            RuntimeError: Raised when the configured benchmark gate fails.
            ValueError: Raised when the package is malformed.

        Boundary behaviour:
            Packages without exported runtime artifacts keep working for legacy
            projection/VPI tasks. Raw-frame packages may require a benchmark gate
            depending on their runtime config.
        """
        payload = resolve_model_package(model_dir_or_config)
        self._meta = dict(payload['meta'])
        self._parameters = dict(payload['parameters'])
        self._config = dict(payload.get('config', {}) or {})
        self._runtime_weights = {}
        runtime_kind = str(self._meta.get('runtime_kind', '') or '')
        runtime_model_path = str(self._meta.get('runtime_model_path', '') or '')
        if runtime_kind == 'exported_weight_template':
            if not runtime_model_path:
                raise ValueError('exported_weight_template packages must declare runtime_model_path')
            weight_payload = np.load(runtime_model_path, allow_pickle=False)
            self._runtime_weights = {name: np.asarray(weight_payload[name], dtype=np.float32) for name in weight_payload.files}
            if 'left_template' not in self._runtime_weights or 'right_template' not in self._runtime_weights:
                raise ValueError('exported frame anatomy weight package must contain left_template and right_template')
        self._apply_release_gate()
        self._loaded = True

    def infer(self, image_bundle: dict[str, Any], bone_mask: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self._loaded:
            raise RuntimeError('keypoint runtime adapter is not loaded')
        image = np.asarray(image_bundle.get('image'), dtype=np.float32)
        if image.ndim != 2:
            raise ValueError('image_bundle.image must be 2D')
        context = dict(bone_mask or {})
        task_variant = str(context.get('task_variant', '') or '')
        if task_variant == 'frame_anatomy_points' or str(self._meta.get('input_contract', '')).lower() == 'raw_ultrasound_frame_sequence':
            return self._infer_frame_points(image, context)
        binary_mask = np.asarray(context.get('binary_mask'), dtype=np.uint8) if context.get('binary_mask') is not None else np.zeros_like(image, dtype=np.uint8)
        if binary_mask.shape != image.shape:
            binary_mask = np.zeros_like(image, dtype=np.uint8)
        candidate_window_px = int(self._parameters.get('candidate_window_px', 12) or 12)
        rows = []
        for row_index in range(image.shape[0]):
            active = np.flatnonzero(binary_mask[row_index] > 0)
            if active.size >= 2:
                left_px = int(active[0])
                right_px = int(active[-1])
            else:
                peak = int(np.argmax(image[row_index])) if image.shape[1] else 0
                left_px = max(0, peak - candidate_window_px)
                right_px = min(max(0, image.shape[1] - 1), peak + candidate_window_px)
            rows.append({'row_px': row_index, 'left_px': left_px, 'right_px': right_px})
        return {
            'rows': rows,
            'summary': {
                'row_count': len(rows),
                'avg_separation_px': round(float(np.mean([row['right_px'] - row['left_px'] for row in rows])) if rows else 0.0, 6),
            },
            'runtime_model': dict(self._meta),
        }

    def fallback_frame_points(self, image: np.ndarray, *, previous_pair: dict[str, dict[str, float]] | None = None) -> dict[str, Any]:
        """Run deterministic raw-frame point extraction without a loaded package."""
        meta = {
            'package_name': 'frame_anatomy_inline_fallback',
            'backend': 'inline_fallback',
            'runtime_kind': 'deterministic_fallback',
            'release_state': 'degraded',
        }
        return self._infer_frame_points_baseline(np.asarray(image, dtype=np.float32), {'previous_pair': previous_pair or {}}, meta_override=meta)

    def _apply_release_gate(self) -> None:
        require_gate = bool(self._config.get('require_benchmark_gate', False))
        benchmark_manifest_path = str(self._meta.get('benchmark_manifest_path', '') or self._config.get('benchmark_manifest', '') or '')
        thresholds = dict(self._config.get('benchmark_thresholds', {}) or {})
        required_release_state = str(self._config.get('required_release_state', '') or '')
        if not require_gate and not benchmark_manifest_path:
            return
        gate = RuntimeModelReleaseGateService().evaluate(
            runtime_meta=self._meta,
            benchmark_manifest_path=benchmark_manifest_path,
            thresholds=thresholds,
            required_release_state=required_release_state,
        )
        self._meta['benchmark_gate'] = gate
        if require_gate and not bool(gate.get('passed', False)):
            failures = ', '.join(gate.get('failures', [])) or 'unknown_gate_failure'
            raise RuntimeError(f'benchmark release gate failed: {failures}')

    def _infer_frame_points(self, image: np.ndarray, context: dict[str, Any]) -> dict[str, Any]:
        if str(self._meta.get('runtime_kind', '') or '') == 'exported_weight_template' and self._runtime_weights:
            return self._infer_frame_points_exported(image, context)
        return self._infer_frame_points_baseline(image, context)

    def _infer_frame_points_exported(self, image: np.ndarray, context: dict[str, Any]) -> dict[str, Any]:
        normalized = self._normalize(image)
        if normalized.size == 0:
            return {'left': {}, 'right': {}, 'stable': False, 'stability_score': 0.0, 'runtime_model': dict(self._meta)}
        patch_radius = int(self._parameters.get('patch_radius_px', max(1, (self._runtime_weights['left_template'].shape[0] - 1) // 2)) or 4)
        min_separation_px = int(self._parameters.get('min_pair_separation_px', 18) or 18)
        previous_pair = context.get('previous_pair', {}) if isinstance(context.get('previous_pair', {}), dict) else {}
        quality_scale = min(1.0, max(0.0, 0.5 * float(context.get('quality_score', 1.0) or 1.0) + 0.5 * float(context.get('contact_confidence', 1.0) or 1.0)))
        score_map = self._compute_template_score_map(normalized, self._runtime_weights['left_template'], patch_radius)
        height, width = score_map.shape
        if height == 0 or width == 0:
            return {'left': {}, 'right': {}, 'stable': False, 'stability_score': 0.0, 'runtime_model': dict(self._meta)}
        left_region = score_map[:, : max(1, width // 2)]
        right_region = score_map[:, min(width // 2, width - 1):]
        left_idx = int(np.argmax(left_region))
        left_y, left_x = divmod(left_idx, left_region.shape[1])
        right_idx = int(np.argmax(right_region))
        right_y, right_x_local = divmod(right_idx, right_region.shape[1])
        right_x = int(right_x_local + min(width // 2, width - 1))
        if abs(right_x - left_x) < min_separation_px:
            candidate_order = np.argsort(score_map.reshape(-1))[::-1]
            selected = []
            for flat_idx in candidate_order:
                y_px, x_px = divmod(int(flat_idx), width)
                if not selected or all(abs(x_px - existing[1]) >= min_separation_px for existing in selected):
                    selected.append((y_px, x_px))
                if len(selected) == 2:
                    break
            if len(selected) < 2:
                return {'left': {}, 'right': {}, 'stable': False, 'stability_score': 0.0, 'runtime_model': dict(self._meta)}
            selected.sort(key=lambda item: item[1])
            (left_y, left_x), (right_y, right_x) = selected
        left_confidence = self._score_to_confidence(float(score_map[left_y, left_x]), quality_scale)
        right_confidence = self._score_to_confidence(float(score_map[right_y, right_x]), quality_scale)
        stability_score = self._stability_score(previous_pair, left_x, left_y, right_x, right_y)
        stable = bool(stability_score >= float(self._parameters.get('min_stability_score', 0.55) or 0.55))
        return {
            'left': {'x_px': int(left_x), 'y_px': int(left_y), 'confidence': round(left_confidence, 6)},
            'right': {'x_px': int(right_x), 'y_px': int(right_y), 'confidence': round(right_confidence, 6)},
            'stable': stable,
            'stability_score': round(float(stability_score), 6),
            'summary': {'pair_separation_px': int(right_x - left_x), 'score_floor': float(self._parameters.get('ncc_score_floor', 0.15) or 0.15)},
            'runtime_model': dict(self._meta),
        }

    def _infer_frame_points_baseline(self, image: np.ndarray, context: dict[str, Any], *, meta_override: dict[str, Any] | None = None) -> dict[str, Any]:
        normalized = self._normalize(image)
        if normalized.size == 0:
            return {'left': {}, 'right': {}, 'stable': False, 'stability_score': 0.0, 'runtime_model': dict(meta_override or self._meta)}
        roi_top = int(round(float(self._parameters.get('roi_top_fraction', 0.18) or 0.18) * max(0, normalized.shape[0] - 1)))
        roi_bottom = int(round(float(self._parameters.get('roi_bottom_fraction', 0.82) or 0.82) * max(0, normalized.shape[0] - 1)))
        roi_bottom = max(roi_top + 1, min(normalized.shape[0], roi_bottom))
        roi = normalized[roi_top:roi_bottom, :]
        candidate_window_px = int(self._parameters.get('candidate_window_px', 12) or 12)
        min_separation_px = int(self._parameters.get('min_pair_separation_px', 20) or 20)
        max_drift_px = float(self._parameters.get('max_temporal_drift_px', 18.0) or 18.0)
        shadow_weight = float(self._parameters.get('posterior_shadow_weight', 0.25) or 0.25)
        contrast_weight = float(self._parameters.get('contrast_weight', 0.35) or 0.35)
        previous_pair = context.get('previous_pair', {}) if isinstance(context.get('previous_pair', {}), dict) else {}
        quality_scale = min(1.0, max(0.0, 0.5 * float(context.get('quality_score', 1.0) or 1.0) + 0.5 * float(context.get('contact_confidence', 1.0) or 1.0)))

        height, width = normalized.shape
        if roi.size == 0 or width == 0:
            return {'left': {}, 'right': {}, 'stable': False, 'stability_score': 0.0, 'runtime_model': dict(meta_override or self._meta)}

        peak_rows = np.argmax(roi, axis=0)
        peak_scores = roi[peak_rows, np.arange(width)]
        shadow_scores = np.zeros((width,), dtype=np.float32)
        for column in range(width):
            start = int(peak_rows[column])
            tail = roi[start:, column]
            if tail.size > 2:
                shadow_scores[column] = float(max(0.0, 1.0 - float(np.mean(tail[min(1, tail.size - 1):]))))
        column_signal = peak_scores * (1.0 + shadow_weight * shadow_scores)
        local_mean = self._moving_average(column_signal, int(self._parameters.get('contrast_window_px', 11) or 11))
        column_signal = column_signal + contrast_weight * np.clip(column_signal - local_mean, 0.0, 1.0)

        peak_order = list(np.argsort(column_signal)[::-1])
        selected: list[int] = []
        for idx in peak_order:
            idx = int(idx)
            if not selected or all(abs(idx - item) >= min_separation_px for item in selected):
                selected.append(idx)
            if len(selected) == 2:
                break
        if len(selected) < 2:
            return {'left': {}, 'right': {}, 'stable': False, 'stability_score': 0.0, 'runtime_model': dict(meta_override or self._meta)}
        selected.sort()

        left_px, right_px = int(selected[0]), int(selected[1])
        left_y = int(peak_rows[left_px] + roi_top)
        right_y = int(peak_rows[right_px] + roi_top)
        left_confidence = float(column_signal[left_px] * quality_scale)
        right_confidence = float(column_signal[right_px] * quality_scale)

        stability_score = self._stability_score(previous_pair, left_px, left_y, right_px, right_y, max_drift_px=max_drift_px)
        stable = bool(stability_score >= float(self._parameters.get('min_stability_score', 0.55) or 0.55))
        confidence_scale = 0.5 + 0.5 * stability_score
        return {
            'left': {
                'x_px': left_px,
                'y_px': left_y,
                'confidence': round(min(1.0, max(0.0, left_confidence * confidence_scale)), 6),
            },
            'right': {
                'x_px': right_px,
                'y_px': right_y,
                'confidence': round(min(1.0, max(0.0, right_confidence * confidence_scale)), 6),
            },
            'stable': stable,
            'stability_score': round(float(stability_score), 6),
            'summary': {
                'candidate_window_px': candidate_window_px,
                'pair_separation_px': int(right_px - left_px),
            },
            'runtime_model': dict(meta_override or self._meta),
        }

    @staticmethod
    def _normalize(image: np.ndarray) -> np.ndarray:
        if image.size == 0:
            return np.zeros((0, 0), dtype=np.float32)
        low = float(image.min())
        high = float(image.max())
        if high <= low:
            return np.zeros_like(image, dtype=np.float32)
        normalized = (image - low) / (high - low)
        threshold = float(np.quantile(normalized, 0.20))
        return np.clip((normalized - threshold) / max(1e-6, 1.0 - threshold), 0.0, 1.0).astype(np.float32)

    @staticmethod
    def _moving_average(values: np.ndarray, window: int) -> np.ndarray:
        window = max(1, int(window))
        if window == 1 or values.size == 0:
            return values.astype(np.float32, copy=True)
        kernel = np.ones((window,), dtype=np.float32) / float(window)
        padded = np.pad(values.astype(np.float32), (window // 2, window - 1 - (window // 2)), mode='edge')
        return np.convolve(padded, kernel, mode='valid').astype(np.float32)

    def _compute_template_score_map(self, image: np.ndarray, template: np.ndarray, patch_radius: int) -> np.ndarray:
        image = np.asarray(image, dtype=np.float32)
        template = np.asarray(template, dtype=np.float32)
        if image.size == 0 or template.size == 0:
            return np.zeros((0, 0), dtype=np.float32)
        height, width = image.shape
        score_map = np.full((height, width), -1.0, dtype=np.float32)
        template_norm = float(np.linalg.norm(template))
        if template_norm <= 1e-6:
            return score_map
        for y_px in range(patch_radius, height - patch_radius):
            for x_px in range(patch_radius, width - patch_radius):
                patch = image[y_px - patch_radius:y_px + patch_radius + 1, x_px - patch_radius:x_px + patch_radius + 1]
                patch = patch - float(np.mean(patch))
                patch_norm = float(np.linalg.norm(patch))
                if patch_norm <= 1e-6:
                    continue
                score_map[y_px, x_px] = float(np.sum(patch * template) / (patch_norm * template_norm))
        return score_map

    def _score_to_confidence(self, score: float, quality_scale: float) -> float:
        floor = float(self._parameters.get('ncc_score_floor', 0.15) or 0.15)
        normalized = max(0.0, (score - floor) / max(1e-6, 1.0 - floor))
        return min(1.0, max(0.0, normalized * quality_scale))

    def _stability_score(self, previous_pair: dict[str, dict[str, float]], left_x: int, left_y: int, right_x: int, right_y: int, max_drift_px: float | None = None) -> float:
        max_drift_px = float(max_drift_px if max_drift_px is not None else self._parameters.get('max_temporal_drift_px', 18.0) or 18.0)
        stability_score = 1.0
        if previous_pair:
            drift_values = []
            if 'left' in previous_pair:
                drift_values.append(abs(float(previous_pair['left'].get('x_px', left_x)) - left_x))
                drift_values.append(abs(float(previous_pair['left'].get('y_px', left_y)) - left_y))
            if 'right' in previous_pair:
                drift_values.append(abs(float(previous_pair['right'].get('x_px', right_x)) - right_x))
                drift_values.append(abs(float(previous_pair['right'].get('y_px', right_y)) - right_y))
            if drift_values:
                stability_score = max(0.0, 1.0 - (float(np.mean(drift_values)) / max(1.0, max_drift_px)))
        return stability_score
