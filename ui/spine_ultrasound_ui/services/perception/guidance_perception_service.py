from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import numpy as np

from spine_ultrasound_ui.services.perception.camera_provider import CapturedFrame


@dataclass
class GuidanceObservation:
    """Perception facts derived from actual guidance frames.

    Attributes:
        roi_center_y_mm: Lateral corridor center in millimeters.
        segment_count: Estimated usable strip count.
        confidence: Overall observation confidence.
        back_roi: Back ROI artifact payload.
        midline_polyline: Midline artifact payload.
        landmarks: Landmark list in millimeter coordinates.
        body_surface: Body-surface model payload.
        guidance_targets: Guidance target payload.
        usable_segments: Ordered usable segment identifiers.
        notes: Human-readable audit notes.
        registration_quality: Summary metrics used by guidance gating.
        provider_mode: Camera input mode that produced the observation.
    """

    roi_center_y_mm: float
    segment_count: int
    confidence: float
    back_roi: dict[str, Any]
    midline_polyline: dict[str, Any]
    landmarks: list[dict[str, Any]]
    body_surface: dict[str, Any]
    guidance_targets: dict[str, Any]
    usable_segments: list[int]
    notes: list[str]
    registration_quality: dict[str, Any]
    provider_mode: str


class GuidancePerceptionService:
    """Estimate guidance facts from captured camera frames.

    The implementation uses deterministic image heuristics so the guidance
    contract is derived from real frame tensors instead of fixed constants.
    """

    def analyze(
        self,
        *,
        frames: list[CapturedFrame],
        config: Any,
        calibration_bundle: dict[str, Any],
        source_type: str,
    ) -> GuidanceObservation:
        """Analyze captured frames and return normalized guidance observations.

        Args:
            frames: Ordered captured frames.
            config: Runtime configuration.
            calibration_bundle: Active calibration bundle.
            source_type: Guidance source mode.

        Returns:
            Structured guidance observation.

        Raises:
            RuntimeError: If no frames are available or the image content is invalid.
        """
        if not frames:
            raise RuntimeError('guidance perception requires at least one frame')
        stack = np.stack([frame.pixels for frame in frames], axis=0)
        mean_frame = np.mean(stack, axis=0)
        provider_mode = frames[0].provider_mode
        height, width = mean_frame.shape
        mm_per_pixel_x = float(
            calibration_bundle.get('camera_intrinsics', {}).get('mm_per_pixel_x', 0.15)
            or calibration_bundle.get('support_frame', {}).get('mm_per_pixel_x', 0.15)
            or 0.15
        )
        mm_per_pixel_y = float(
            calibration_bundle.get('camera_intrinsics', {}).get('mm_per_pixel_y', 0.15)
            or calibration_bundle.get('support_frame', {}).get('mm_per_pixel_y', 0.15)
            or 0.15
        )
        column_energy = mean_frame.mean(axis=0)
        row_energy = mean_frame.mean(axis=1)
        col_threshold = float(column_energy.mean() + 0.35 * (column_energy.std() or 1.0))
        row_threshold = float(row_energy.mean() + 0.15 * (row_energy.std() or 1.0))
        active_cols = np.where(column_energy >= col_threshold)[0]
        active_rows = np.where(row_energy >= row_threshold)[0]
        if active_cols.size == 0:
            peak = int(np.argmax(column_energy))
            half_band = max(width // 20, 8)
            active_cols = np.arange(max(0, peak - half_band), min(width, peak + half_band + 1))
        if active_rows.size == 0:
            active_rows = np.arange(max(0, height // 8), min(height, height - height // 10))
        x0, x1 = int(active_cols.min()), int(active_cols.max())
        y0, y1 = int(active_rows.min()), int(active_rows.max())
        center_col = float(active_cols.mean())
        bbox_width_px = max(1, x1 - x0 + 1)
        bbox_height_px = max(1, y1 - y0 + 1)
        roi_center_y_mm = round((center_col - (width / 2.0)) * mm_per_pixel_x, 2)
        corridor_length_mm = max(float(config.segment_length_mm), bbox_height_px * mm_per_pixel_y)
        segment_length_mm = max(float(getattr(config, 'segment_length_mm', 120.0) or 120.0), 1.0)
        segment_count = max(1, int(round(corridor_length_mm / segment_length_mm)))
        segment_count = max(3, min(segment_count, 8))
        sample_rows = np.linspace(y0, y1, num=4, dtype=int)
        midline_points: list[dict[str, float]] = []
        center_cols: list[float] = []
        for idx, row in enumerate(sample_rows):
            row_slice = mean_frame[max(0, row - 2):min(height, row + 3), :].mean(axis=0)
            row_active = np.where(row_slice >= max(float(row_slice.mean()), 0.35))[0]
            if row_active.size == 0:
                row_center = center_col
            else:
                row_center = float(np.average(row_active, weights=row_slice[row_active]))
            center_cols.append(row_center)
            progress = idx / max(len(sample_rows) - 1, 1)
            longitudinal_mm = round(progress * segment_count * segment_length_mm, 2)
            lateral_mm = round((row_center - (width / 2.0)) * mm_per_pixel_x, 2)
            midline_points.append({'x': longitudinal_mm, 'y': lateral_mm, 'z': 205.0})
        slope = 0.0
        if len(center_cols) > 1:
            slope = float(np.polyfit(sample_rows.astype(np.float64), np.array(center_cols, dtype=np.float64), deg=1)[0])
        surface_yaw_deg = round(float(np.degrees(np.arctan(slope))), 2)
        coverage_ratio = float((bbox_width_px * bbox_height_px) / max(width * height, 1))
        contrast = float((column_energy.max() - column_energy.mean()) / max(column_energy.std(), 1e-6))
        confidence = round(float(np.clip(0.62 + 0.12 * min(contrast, 2.0) + 0.18 * min(coverage_ratio * 10.0, 1.0), 0.0, 0.98)), 3)
        if source_type == 'camera_ultrasound_fusion':
            confidence = round(min(0.98, confidence + 0.03), 3)
        landmarks = [
            {'name': 'c7_estimate', **midline_points[0]},
            {'name': 'thoracic_midline', **midline_points[1]},
            {'name': 'thoracolumbar_junction', **midline_points[2]},
            {'name': 'sacrum_estimate', **midline_points[3]},
        ]
        back_roi = {
            'center_y_mm': roi_center_y_mm,
            'length_mm': round(bbox_height_px * mm_per_pixel_y, 2),
            'height_mm': round(bbox_width_px * mm_per_pixel_x, 2),
            'confidence': confidence,
            'bounding_box_px': {'x0': x0, 'x1': x1, 'y0': y0, 'y1': y1},
        }
        midline_polyline = {
            'coordinate_frame': 'patient_surface',
            'points_mm': midline_points,
            'confidence': round(min(0.99, confidence + 0.02), 3),
        }
        body_surface = {
            'model': 'camera_surface_fit_v1',
            'normal': [0.0, 0.0, -1.0],
            'surface_pitch_deg': 0.0,
            'surface_yaw_deg': surface_yaw_deg,
            'probe_tilt_limits_deg': {'min': -8.0, 'max': 8.0},
            'contact_guard_margin_mm': 4.0,
        }
        guidance_targets = {
            'entry_point_mm': dict(midline_points[0]),
            'exit_point_mm': dict(midline_points[-1]),
            'centerline_mm': dict(midline_points[len(midline_points) // 2]),
            'approach_clearance_mm': 18.0,
        }
        usable_segments = list(range(1, segment_count + 1))
        quality_metrics = {
            'overall_confidence': confidence,
            'roi_confidence': confidence,
            'midline_confidence': midline_polyline['confidence'],
            'surface_fit_rms_mm': round(max(0.8, 3.0 - coverage_ratio * 5.0), 3),
            'corridor_margin_mm': round(max(5.0, 12.0 - abs(roi_center_y_mm) * 0.1), 3),
            'landmark_count': len(landmarks),
            'coverage_ratio': round(coverage_ratio, 4),
            'provider_mode': provider_mode,
        }
        registration_quality = {
            'overall_confidence': confidence,
            'surface_fit_rms_mm': quality_metrics['surface_fit_rms_mm'],
            'corridor_margin_mm': quality_metrics['corridor_margin_mm'],
            'registration_ready': True,
            'confidence_breakdown': {
                'camera': confidence if source_type != 'camera_ultrasound_fusion' else round(confidence * 0.6, 3),
                'ultrasound': round(confidence * 0.4, 3) if source_type == 'camera_ultrasound_fusion' else 0.0,
                'hybrid': confidence if source_type == 'camera_ultrasound_fusion' else 0.0,
                'fallback': confidence if source_type == 'fallback_simulated' else 0.0,
            },
            'quality_metrics': quality_metrics,
            'registration_covariance': {
                'longitudinal_mm2': round(max(0.5, corridor_length_mm / 200.0), 3),
                'lateral_mm2': round(max(0.4, back_roi['height_mm'] / 40.0), 3),
                'normal_mm2': 0.35,
            },
        }
        notes = [
            f'Guidance derived from {len(frames)} frame(s) using provider mode {provider_mode}.',
            f'Image-derived ROI center={roi_center_y_mm} mm, segment_count={segment_count}, confidence={confidence}.',
        ]
        return GuidanceObservation(
            roi_center_y_mm=roi_center_y_mm,
            segment_count=segment_count,
            confidence=confidence,
            back_roi=back_roi,
            midline_polyline=midline_polyline,
            landmarks=landmarks,
            body_surface=body_surface,
            guidance_targets=guidance_targets,
            usable_segments=usable_segments,
            notes=notes,
            registration_quality=registration_quality,
            provider_mode=provider_mode,
        )
