from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

from spine_ultrasound_ui.utils import now_text


class VPIProjectionBuilder:
    """Build a pose-resampled coronal-VPI projection bundle.

    The previous implementation synthesized a ridge from scan progress and
    registration priors. This implementation consumes stored ultrasound pixels
    and measured patient-frame probe poses whenever the reconstruction-input
    contract marks a row as reconstructable.
    """

    def __init__(
        self,
        *,
        width_px: int = 192,
        slice_count: int = 16,
        default_lateral_span_mm: float = 240.0,
        lateral_margin_mm: float = 20.0,
        method_version: str = 'vpi_projection_v2',
    ) -> None:
        self.width_px = int(width_px)
        self.slice_count = int(slice_count)
        self.default_lateral_span_mm = float(default_lateral_span_mm)
        self.lateral_margin_mm = float(lateral_margin_mm)
        self.method_version = method_version

    def build(self, input_index: dict[str, Any]) -> dict[str, Any]:
        """Construct a coronal-VPI representation from ultrasound pixels.

        Args:
            input_index: Reconstruction input payload built from authoritative
                session artifacts.

        Returns:
            Dictionary containing a VPI array, preview image, row geometry,
            slice metadata, and projection statistics.

        Raises:
            ValueError: Raised when mandatory session metadata is missing.

        Boundary behaviour:
            If no reconstructable rows are available the method returns a zero
            image together with explicit manual-review reasons instead of
            fabricating a projection from progress-only priors.
        """
        session_id = str(input_index.get('session_id', '') or '')
        if not session_id:
            raise ValueError('input_index.session_id is required')
        rows = [dict(item) for item in input_index.get('selected_rows', []) if isinstance(item, dict)]
        valid_entries = self._collect_entries(rows, dict(input_index.get('scan_geometry', {})))
        if not valid_entries:
            image = np.zeros((1, self.width_px), dtype=np.float32)
            contribution_map = np.zeros_like(image, dtype=np.float32)
            return {
                'generated_at': now_text(),
                'session_id': session_id,
                'experiment_id': str(input_index.get('experiment_id', '') or ''),
                'method_version': self.method_version,
                'image': image,
                'preview_rgb': np.zeros((1, self.width_px, 3), dtype=np.uint8),
                'row_geometry': [],
                'contribution_map': contribution_map,
                'contributing_frames': [],
                'slices': [],
                'stats': {
                    'height_px': 1,
                    'width_px': self.width_px,
                    'slice_count': 0,
                    'peak_intensity': 0.0,
                    'projection_source': 'missing_reconstructable_frames',
                    'manual_review_reasons': list(input_index.get('manual_review_reasons', ['no_reconstructable_rows'])),
                    'reconstructable_frame_count': 0,
                },
            }

        valid_entries.sort(key=lambda item: (item['longitudinal_mm'], item['frame_id']))
        lateral_min, lateral_max = self._lateral_bounds(valid_entries, dict(input_index.get('scan_geometry', {})))
        image = np.zeros((len(valid_entries), self.width_px), dtype=np.float32)
        contribution_map = np.zeros_like(image, dtype=np.float32)
        row_geometry: list[dict[str, Any]] = []
        contributing_frames: list[dict[str, Any]] = []

        for row_index, entry in enumerate(valid_entries):
            profile = np.asarray(entry['profile'], dtype=np.float32)
            if profile.size == 0:
                continue
            center_index = (profile.size - 1) / 2.0
            for column_index, value in enumerate(profile):
                lateral_mm = entry['lateral_center_mm'] + (column_index - center_index) * entry['sample_spacing_mm']
                target_x = int(np.clip(round((lateral_mm - lateral_min) / max(1e-6, lateral_max - lateral_min) * (self.width_px - 1)), 0, self.width_px - 1))
                image[row_index, target_x] = max(float(image[row_index, target_x]), float(value))
                contribution_map[row_index, target_x] += 1.0
            row_geometry.append({
                'row_index': row_index,
                'frame_id': entry['frame_id'],
                'segment_id': entry['segment_id'],
                'longitudinal_mm': round(entry['longitudinal_mm'], 6),
                'lateral_center_mm': round(entry['lateral_center_mm'], 6),
                'normal_mm': round(entry['normal_mm'], 6),
                'sample_spacing_mm': round(entry['sample_spacing_mm'], 6),
                'pose_source': entry['pose_source'],
            })
            contributing_frames.append({
                'frame_id': entry['frame_id'],
                'segment_id': entry['segment_id'],
                'frame_path': entry['frame_path'],
                'row_index': row_index,
                'pose_source': entry['pose_source'],
            })

        peak = float(image.max()) if image.size else 0.0
        if peak > 0.0:
            image = image / peak
        slice_meta = self._slice_metadata(image, contribution_map, row_geometry)
        preview = self._colorize(image)
        return {
            'generated_at': now_text(),
            'session_id': session_id,
            'experiment_id': str(input_index.get('experiment_id', '') or ''),
            'method_version': self.method_version,
            'image': image,
            'preview_rgb': preview,
            'row_geometry': row_geometry,
            'contribution_map': contribution_map,
            'contributing_frames': contributing_frames,
            'slices': slice_meta,
            'stats': {
                'height_px': int(image.shape[0]),
                'width_px': int(image.shape[1]),
                'slice_count': len(slice_meta),
                'peak_intensity': round(float(image.max()) if image.size else 0.0, 6),
                'projection_source': 'pose_resampled_ultrasound',
                'manual_review_reasons': list(input_index.get('manual_review_reasons', [])),
                'reconstructable_frame_count': len(valid_entries),
                'lateral_range_mm': [round(lateral_min, 6), round(lateral_max, 6)],
                'contribution_density': round(float((contribution_map > 0).mean()) if contribution_map.size else 0.0, 6),
            },
        }

    def _collect_entries(self, rows: list[dict[str, Any]], scan_geometry: dict[str, Any]) -> list[dict[str, Any]]:
        entries: list[dict[str, Any]] = []
        default_span = float(scan_geometry.get('corridor_width_mm', self.default_lateral_span_mm) or self.default_lateral_span_mm)
        for row in rows:
            if not bool(row.get('reconstructable', False)):
                continue
            frame_path = Path(str(row.get('ultrasound_frame_path', '') or ''))
            if not frame_path.exists():
                continue
            image = self._load_ultrasound_frame(frame_path)
            if image.size == 0:
                continue
            profile = self._extract_profile(image)
            if profile.size == 0:
                continue
            pose = dict(row.get('patient_pose_mm_rad', {}))
            lateral_span_mm = float(row.get('ultrasound_frame_meta', {}).get('lateral_span_mm', default_span) or default_span)
            if lateral_span_mm <= 0.0:
                lateral_span_mm = default_span
            entries.append({
                'frame_id': str(row.get('frame_id', '')),
                'segment_id': int(row.get('segment_id', 0) or 0),
                'frame_path': str(frame_path),
                'profile': profile,
                'sample_spacing_mm': lateral_span_mm / max(1, profile.size - 1),
                'longitudinal_mm': float(pose.get('x', float(row.get('progress_pct', 0.0) or 0.0)) or 0.0),
                'lateral_center_mm': float(pose.get('y', 0.0) or 0.0),
                'normal_mm': float(pose.get('z', 0.0) or 0.0),
                'pose_source': str(row.get('robot_pose_source', 'missing') or 'missing'),
            })
        return entries

    def _lateral_bounds(self, entries: list[dict[str, Any]], scan_geometry: dict[str, Any]) -> tuple[float, float]:
        span = max(float(scan_geometry.get('corridor_width_mm', self.default_lateral_span_mm) or self.default_lateral_span_mm), self.default_lateral_span_mm)
        lateral_values = [float(item['lateral_center_mm']) for item in entries]
        lateral_min = min(lateral_values, default=-span / 2.0) - self.lateral_margin_mm
        lateral_max = max(lateral_values, default=span / 2.0) + self.lateral_margin_mm
        if lateral_max - lateral_min < span:
            center = (lateral_max + lateral_min) / 2.0
            lateral_min = center - span / 2.0
            lateral_max = center + span / 2.0
        return lateral_min, lateral_max

    def _slice_metadata(
        self,
        image: np.ndarray,
        contribution_map: np.ndarray,
        row_geometry: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        slice_edges = np.linspace(0, image.shape[1], num=self.slice_count + 1, dtype=int)
        slice_meta: list[dict[str, Any]] = []
        contributing_frame_ids = [str(item.get('frame_id', '')) for item in row_geometry]
        for slice_index in range(self.slice_count):
            start = int(slice_edges[slice_index])
            end = int(max(start + 1, slice_edges[slice_index + 1]))
            slice_arr = image[:, start:end]
            slice_meta.append({
                'slice_id': f'slice_{slice_index:03d}',
                'x_range_px': [start, end - 1],
                'score': round(float(slice_arr.mean()) if slice_arr.size else 0.0, 6),
                'peak_intensity': round(float(slice_arr.max()) if slice_arr.size else 0.0, 6),
                'contribution_ratio': round(float((contribution_map[:, start:end] > 0).mean()) if slice_arr.size else 0.0, 6),
                'frame_ids': contributing_frame_ids[:24],
            })
        return slice_meta

    @staticmethod
    def _load_ultrasound_frame(path: Path) -> np.ndarray:
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
    def _extract_profile(image: np.ndarray) -> np.ndarray:
        if image.ndim != 2:
            raise ValueError('ultrasound frame must be a 2D grayscale image')
        if image.size == 0:
            return np.zeros((0,), dtype=np.float32)
        clipped = np.clip(image - float(np.quantile(image, 0.35)), 0.0, 1.0)
        profile = np.max(clipped, axis=0)
        if float(profile.max()) > 0.0:
            profile = profile / float(profile.max())
        return profile.astype(np.float32)

    @staticmethod
    def save_preview(preview_rgb: np.ndarray, target: Path) -> Path:
        """Persist the VPI preview image to disk.

        Args:
            preview_rgb: Preview RGB array in uint8 format.
            target: Destination path for the PNG preview.

        Returns:
            Written PNG path.

        Raises:
            ValueError: Raised when the preview array has an invalid shape.

        Boundary behaviour:
            Single-row arrays are expanded to ensure a visible preview image.
        """
        if preview_rgb.ndim != 3 or preview_rgb.shape[2] != 3:
            raise ValueError('preview_rgb must be an HxWx3 array')
        array = preview_rgb
        if array.shape[0] == 1:
            array = np.repeat(array, 16, axis=0)
        Image.fromarray(array, mode='RGB').save(target)
        return target

    @staticmethod
    def _colorize(image: np.ndarray) -> np.ndarray:
        base = np.clip(image * 255.0, 0, 255).astype(np.uint8)
        return np.stack([
            base,
            np.clip(base * 0.85, 0, 255).astype(np.uint8),
            np.clip(base * 0.45, 0, 255).astype(np.uint8),
        ], axis=-1)
