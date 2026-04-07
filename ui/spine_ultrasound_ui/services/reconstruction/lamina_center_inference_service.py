from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.services.reconstruction.closure_profile import load_reconstruction_profile, profile_name
from spine_ultrasound_ui.training.runtime_adapters.keypoint_runtime_adapter import KeypointRuntimeAdapter
from spine_ultrasound_ui.utils import now_text


class LaminaCenterInferenceService:
    """Infer lamina-center candidates from raw-frame anatomy points or projected bone masks."""

    def __init__(
        self,
        *,
        min_confidence: float = 0.15,
        method_version: str = 'lamina_center_inference_v3',
        runtime_adapter: KeypointRuntimeAdapter | None = None,
        runtime_model_config: str | Path | None = None,
    ) -> None:
        self.min_confidence = float(min_confidence)
        self.method_version = method_version
        self.runtime_adapter = runtime_adapter
        self.profile = load_reconstruction_profile()
        self.runtime_model_config = runtime_model_config or os.environ.get(
            'SPINE_LAMINA_KEYPOINT_RUNTIME_CONFIG',
            Path(__file__).resolve().parents[3] / 'configs' / 'models' / 'lamina_keypoint_runtime.yaml',
        )
        self.runtime_load_error = ''
        self._try_load_runtime_adapter()

    def infer(
        self,
        projection_bundle: dict[str, Any],
        bone_mask_bundle: dict[str, Any],
        input_index: dict[str, Any],
        frame_anatomy_points: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Infer left/right lamina candidates from a VPI projection.

        Args:
            projection_bundle: Projection bundle with VPI image and slice data.
            bone_mask_bundle: Segmentation mask bundle.
            input_index: Reconstruction input payload.
            frame_anatomy_points: Optional frame-level anatomical point payload.

        Returns:
            Candidate payload containing per-vertebra left/right lamina centers.

        Raises:
            ValueError: Raised when the bundle images are malformed.

        Boundary behaviour:
            The service prefers stable frame-level anatomy points extracted from
            raw ultrasound frames. If none are available, it falls back to the
            projection/bone-mask pathway while keeping the fallback explicit in
            the returned summary.
        """
        image = np.asarray(projection_bundle.get('image'))
        binary_mask = np.asarray(bone_mask_bundle.get('binary_mask'))
        if image.ndim != 2 or binary_mask.ndim != 2:
            raise ValueError('projection and bone mask must both be 2D arrays')
        row_geometry = [dict(item) for item in projection_bundle.get('row_geometry', []) if isinstance(item, dict)]
        rows = [dict(item) for item in input_index.get('selected_rows', input_index.get('rows', [])) if isinstance(item, dict)]
        if not rows or image.shape[0] == 0:
            return {
                'generated_at': now_text(),
                'session_id': str(projection_bundle.get('session_id', '') or ''),
                'method_version': self.method_version,
                'candidates': [],
                'summary': {'candidate_count': 0, 'pair_count': 0, 'avg_confidence': 0.0, 'primary_source': 'projection_fallback', 'runtime_profile': profile_name(self.profile)},
                'runtime_model': self._with_profile_metadata(self._fallback_runtime_model()),
            }
        if frame_anatomy_points:
            frame_candidates = self._candidates_from_frame_points(frame_anatomy_points, projection_bundle)
            if frame_candidates['candidates']:
                return frame_candidates

        adapter_rows = None
        runtime_model = self._fallback_runtime_model()
        if self.runtime_adapter is not None and self.runtime_adapter.is_loaded:
            payload = self.runtime_adapter.infer({'image': image}, {'binary_mask': binary_mask})
            adapter_rows = payload.get('rows', [])
            runtime_model = dict(payload.get('runtime_model', {}))
        candidates: list[dict[str, Any]] = []
        width = image.shape[1]
        lateral_range = dict(projection_bundle.get('stats', {})).get('lateral_range_mm', [-120.0, 120.0])
        min_x_mm = float(lateral_range[0]) if isinstance(lateral_range, list) and len(lateral_range) == 2 else -120.0
        max_x_mm = float(lateral_range[1]) if isinstance(lateral_range, list) and len(lateral_range) == 2 else 120.0
        geometry_by_index = {int(item.get('row_index', idx)): item for idx, item in enumerate(row_geometry)}
        for idx, row in enumerate(rows[: image.shape[0]]):
            geometry = dict(geometry_by_index.get(idx, {}))
            if adapter_rows and idx < len(adapter_rows):
                adapter_row = dict(adapter_rows[idx])
                left_px = int(adapter_row.get('left_px', 0) or 0)
                right_px = int(adapter_row.get('right_px', min(width - 1, 0)) or min(width - 1, 0))
                confidence = max(self.min_confidence, float(bone_mask_bundle.get('summary', {}).get('peak_score', 0.0) or 0.0))
            else:
                line_mask = binary_mask[idx]
                active = np.flatnonzero(line_mask > 0)
                if active.size >= 2:
                    left_px = int(active[0])
                    right_px = int(active[-1])
                    confidence = float(min(1.0, bone_mask_bundle.get('summary', {}).get('peak_score', 0.0) + line_mask.mean()))
                else:
                    peak = int(np.argmax(image[idx])) if width else 0
                    left_px = max(0, peak - 10)
                    right_px = min(width - 1, peak + 10)
                    confidence = self.min_confidence
            frame_id = str(geometry.get('frame_id', row.get('frame_id', f'frame_{idx:04d}')) or f'frame_{idx:04d}')
            segment_id = int(geometry.get('segment_id', row.get('segment_id', 0)) or 0)
            vertebra_id = f'vertebra_{segment_id:03d}_{idx:04d}'
            for side, x_px in (('left', left_px), ('right', right_px)):
                x_mm = round(min_x_mm + (x_px / max(1, width - 1)) * (max_x_mm - min_x_mm), 3)
                y_mm = round(float(geometry.get('longitudinal_mm', row.get('patient_pose_mm_rad', {}).get('x', row.get('progress_pct', 0.0))) or 0.0), 3)
                z_mm = round(float(geometry.get('normal_mm', row.get('patient_pose_mm_rad', {}).get('z', 0.0)) or 0.0), 3)
                candidates.append({
                    'candidate_id': f'{vertebra_id}_{side}',
                    'vertebra_id': vertebra_id,
                    'frame_id': frame_id,
                    'segment_id': segment_id,
                    'side': side,
                    'x_px': int(x_px),
                    'row_px': int(idx),
                    'x_mm': x_mm,
                    'y_mm': y_mm,
                    'z_mm': z_mm,
                    'confidence': round(max(self.min_confidence, confidence), 4),
                    'source': 'projection_fallback',
                })
        confidences = [float(item.get('confidence', 0.0) or 0.0) for item in candidates]
        pair_count = len({str(item.get('vertebra_id', '')) for item in candidates})
        return {
            'generated_at': now_text(),
            'session_id': str(projection_bundle.get('session_id', '') or ''),
            'method_version': self.method_version,
            'candidates': candidates,
            'summary': {
                'candidate_count': len(candidates),
                'pair_count': pair_count,
                'avg_confidence': round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
                'primary_source': 'projection_fallback',
                'runtime_profile': profile_name(self.profile),
            },
            'runtime_model': self._with_profile_metadata(runtime_model),
        }

    def _candidates_from_frame_points(
        self,
        frame_anatomy_points: dict[str, Any],
        projection_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        """Promote stable raw-frame anatomy points into lamina candidates.

        Args:
            frame_anatomy_points: Frame-level left/right anatomical points.
            projection_bundle: Projection metadata used to preserve session and
                coordinate-frame lineage.

        Returns:
            Lamina-candidate payload whose vertebra identities are stabilized at
            the per-instance level.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Undetected or incomplete pairs are skipped instead of producing
            partial candidates, keeping the downstream Cobb path explicitly
            measured-only.
        """
        stable_pairs = [dict(item) for item in frame_anatomy_points.get('stable_pairs', []) if isinstance(item, dict)]
        candidates: list[dict[str, Any]] = []
        for order, pair in enumerate(stable_pairs, start=1):
            if not bool(pair.get('stable', False)):
                continue
            for side in ('left', 'right'):
                point = dict(pair.get(side, {}))
                if not point:
                    continue
                candidates.append({
                    'candidate_id': str(point.get('point_id', f"{pair.get('frame_id', '')}_{side}")),
                    'vertebra_id': str(point.get('vertebra_id', f"{pair.get('frame_id', '')}_{side}")),
                    'instance_id': str(point.get('instance_id', f'vertebra_instance_{order:04d}')),
                    'longitudinal_order': int(point.get('longitudinal_order', order) or order),
                    'supporting_frames': list(point.get('supporting_frames', [str(point.get('frame_id', pair.get('frame_id', '')))])),
                    'supporting_frame_count': int(point.get('supporting_frame_count', 1) or 1),
                    'pair_completeness': float(point.get('pair_completeness', 1.0) or 1.0),
                    'persistence_score': float(point.get('persistence_score', point.get('stability_score', 0.0)) or 0.0),
                    'frame_id': str(point.get('frame_id', pair.get('frame_id', ''))),
                    'segment_id': int(point.get('segment_id', pair.get('segment_id', 0)) or 0),
                    'side': side,
                    'x_px': int(point.get('x_px', 0) or 0),
                    'y_px': int(point.get('y_px', 0) or 0),
                    'row_px': int(point.get('y_px', 0) or 0),
                    'x_mm': float(point.get('x_mm', 0.0) or 0.0),
                    'y_mm': float(point.get('y_mm', 0.0) or 0.0),
                    'z_mm': float(point.get('z_mm', 0.0) or 0.0),
                    'depth_mm': float(point.get('depth_mm', 0.0) or 0.0),
                    'confidence': round(float(point.get('confidence', 0.0) or 0.0), 6),
                    'stability_score': round(float(point.get('stability_score', 0.0) or 0.0), 6),
                    'source': 'frame_anatomy_points',
                })
        confidences = [float(item.get('confidence', 0.0) or 0.0) for item in candidates]
        pair_count = len({str(item.get('vertebra_id', '')) for item in candidates})
        return {
            'generated_at': now_text(),
            'session_id': str(projection_bundle.get('session_id', '') or ''),
            'method_version': self.method_version,
            'candidates': candidates,
            'summary': {
                'candidate_count': len(candidates),
                'pair_count': pair_count,
                'avg_confidence': round(sum(confidences) / len(confidences), 4) if confidences else 0.0,
                'primary_source': 'frame_anatomy_points',
                'stable_frame_count': int(frame_anatomy_points.get('summary', {}).get('stable_frame_count', 0) or 0),
                'runtime_profile': profile_name(self.profile),
            },
            'runtime_model': self._with_profile_metadata(dict(frame_anatomy_points.get('runtime_model', self._fallback_runtime_model()))),
        }

    def _try_load_runtime_adapter(self) -> None:
        if self.profile.get('closure_mode') == 'measured_only':
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

    def _fallback_runtime_model(self) -> dict[str, Any]:
        """Return runtime metadata for the active lamina-center backend."""
        if self.profile.get('closure_mode') == 'measured_only':
            return {
                'package_name': 'lamina_keypoint_preweight',
                'backend': 'deterministic_baseline',
                'runtime_kind': 'deterministic_baseline',
                'release_state': str(self.profile.get('profile_release_state', 'research_preweight') or 'research_preweight'),
                'load_error': self.runtime_load_error,
            }
        return {
            'package_name': 'lamina_keypoint_inline_fallback',
            'backend': 'inline_fallback',
            'runtime_kind': 'deterministic_fallback',
            'release_state': 'degraded',
            'load_error': self.runtime_load_error,
        }

    def _with_profile_metadata(self, payload: dict[str, Any]) -> dict[str, Any]:
        model = dict(payload)
        model['runtime_profile'] = profile_name(self.profile)
        model['profile_release_state'] = str(self.profile.get('profile_release_state', 'research_validated') or 'research_validated')
        model['closure_mode'] = str(self.profile.get('closure_mode', 'runtime_optional') or 'runtime_optional')
        return model
