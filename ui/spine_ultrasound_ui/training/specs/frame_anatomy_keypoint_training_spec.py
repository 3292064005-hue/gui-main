from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .common import load_structured_config, normalize_trainer_backend


@dataclass(slots=True)
class FrameAnatomyKeypointTrainingSpec:
    """Structured training configuration for raw-frame anatomy point export.

    Args:
        dataset_manifest: JSON manifest describing annotated raw ultrasound frames.
        output_dir: Directory where training and export artifacts are emitted.
        task_name: Human-readable training task identifier.
        trainer_backend: Backend identifier. Only ``numpy_baseline`` is executed
            inside the runtime repository; heavyweight backends remain external.
        patch_radius_px: Radius of the exported point template.
        min_pair_separation_px: Minimum horizontal separation between left/right points.
        max_temporal_drift_px: Runtime stability threshold.
        min_stability_score: Runtime stability score gate.
        min_confidence: Runtime confidence gate.
        export_model_filename: Name of the exported weights file.
        benchmark_thresholds: Release-gate thresholds applied to the exported package.
        backend_options: Optional backend-specific payload.
    """

    dataset_manifest: Path
    output_dir: Path
    task_name: str = 'frame_anatomy_keypoint'
    trainer_backend: str = 'numpy_baseline'
    patch_radius_px: int = 4
    min_pair_separation_px: int = 18
    max_temporal_drift_px: float = 18.0
    min_stability_score: float = 0.55
    min_confidence: float = 0.35
    export_model_filename: str = 'frame_anatomy_keypoint_weights.npz'
    benchmark_thresholds: dict[str, Any] = field(default_factory=lambda: {
        'max_mean_error_px': 2.5,
        'max_max_error_px': 6.0,
        'min_detection_rate': 0.95,
        'min_stable_detection_rate': 0.9,
    })
    backend_options: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        self.trainer_backend = normalize_trainer_backend(self.trainer_backend)
        if self.patch_radius_px <= 0:
            raise ValueError('patch_radius_px must be positive')
        if self.min_pair_separation_px <= 0:
            raise ValueError('min_pair_separation_px must be positive')
        if self.max_temporal_drift_px <= 0.0:
            raise ValueError('max_temporal_drift_px must be positive')
        if self.min_stability_score < 0.0:
            raise ValueError('min_stability_score must be non-negative')
        if self.min_confidence < 0.0:
            raise ValueError('min_confidence must be non-negative')
        if not self.task_name.strip():
            raise ValueError('task_name must not be empty')
        if not self.export_model_filename.strip():
            raise ValueError('export_model_filename must not be empty')
        if not isinstance(self.benchmark_thresholds, dict):
            raise ValueError('benchmark_thresholds must be a mapping')
        if not isinstance(self.backend_options, dict):
            raise ValueError('backend_options must be a mapping')

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['dataset_manifest'] = str(self.dataset_manifest)
        payload['output_dir'] = str(self.output_dir)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'FrameAnatomyKeypointTrainingSpec':
        payload = dict(data)
        return cls(
            dataset_manifest=Path(payload['dataset_manifest']),
            output_dir=Path(payload['output_dir']),
            task_name=str(payload.get('task_name', 'frame_anatomy_keypoint') or 'frame_anatomy_keypoint'),
            trainer_backend=str(payload.get('trainer_backend', 'numpy_baseline') or 'numpy_baseline'),
            patch_radius_px=int(payload.get('patch_radius_px', 4) or 4),
            min_pair_separation_px=int(payload.get('min_pair_separation_px', 18) or 18),
            max_temporal_drift_px=float(payload.get('max_temporal_drift_px', 18.0) or 18.0),
            min_stability_score=float(payload.get('min_stability_score', 0.55) or 0.55),
            min_confidence=float(payload.get('min_confidence', 0.35) or 0.35),
            export_model_filename=str(payload.get('export_model_filename', 'frame_anatomy_keypoint_weights.npz') or 'frame_anatomy_keypoint_weights.npz'),
            benchmark_thresholds=dict(payload.get('benchmark_thresholds', {}) or {}),
            backend_options=dict(payload.get('backend_options', {}) or {}),
        )

    @classmethod
    def from_file(cls, path: Path) -> 'FrameAnatomyKeypointTrainingSpec':
        return cls.from_dict(load_structured_config(path))
