from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .common import load_structured_config, normalize_trainer_backend


@dataclass(slots=True)
class LaminaCenterTrainingSpec:
    """Structured training configuration for the lamina-center pipeline.

    Args:
        dataset_root: Root directory of the exported lamina-center dataset.
        split_file: Patient-level split file.
        output_dir: Training output directory.
        task_name: Human-readable task identifier.
        input_mode: Training input mode such as ``vpi_2d``.
        segmentation_backbone: Named segmentation backbone or backend profile.
        keypoint_head: Keypoint-head strategy name.
        batch_size: Training batch size.
        max_epochs: Maximum training epochs.
        learning_rate: Optimizer learning rate.
        num_workers: Dataset worker count.
        mixed_precision: Whether mixed precision should be enabled.
        export_onnx: Whether exporters should emit an ONNX-compatible package.
        split_name: Split partition consumed for training.
        trainer_backend: Selected trainer backend.
        backend_options: Backend-specific configuration payload.

    Returns:
        Dataclass instance describing a lamina-center training run.

    Raises:
        ValueError: Raised by :meth:`validate` when mandatory fields are invalid.

    Boundary behaviour:
        The spec can be created from either dictionaries or JSON/YAML files,
        allowing offline training pipelines to remain detached from the runtime
        application configuration loader.
    """

    dataset_root: Path
    split_file: Path
    output_dir: Path
    task_name: str = 'lamina_center'
    input_mode: str = 'vpi_2d'
    segmentation_backbone: str = 'numpy_baseline_seg'
    keypoint_head: str = 'numpy_baseline_heatmap'
    batch_size: int = 4
    max_epochs: int = 12
    learning_rate: float = 1e-3
    num_workers: int = 0
    mixed_precision: bool = False
    export_onnx: bool = False
    split_name: str = 'train'
    trainer_backend: str = 'numpy_baseline'
    backend_options: dict[str, Any] = field(default_factory=dict)

    def validate(self) -> None:
        if self.batch_size <= 0:
            raise ValueError('batch_size must be positive')
        if self.max_epochs <= 0:
            raise ValueError('max_epochs must be positive')
        if self.learning_rate <= 0.0:
            raise ValueError('learning_rate must be positive')
        if self.num_workers < 0:
            raise ValueError('num_workers cannot be negative')
        if not self.task_name.strip():
            raise ValueError('task_name must not be empty')
        if not self.input_mode.strip():
            raise ValueError('input_mode must not be empty')
        self.trainer_backend = normalize_trainer_backend(self.trainer_backend)
        if not isinstance(self.backend_options, dict):
            raise ValueError('backend_options must be a mapping')

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload['dataset_root'] = str(self.dataset_root)
        payload['split_file'] = str(self.split_file)
        payload['output_dir'] = str(self.output_dir)
        return payload

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> 'LaminaCenterTrainingSpec':
        payload = dict(data)
        return cls(
            dataset_root=Path(payload['dataset_root']),
            split_file=Path(payload['split_file']),
            output_dir=Path(payload['output_dir']),
            task_name=str(payload.get('task_name', 'lamina_center') or 'lamina_center'),
            input_mode=str(payload.get('input_mode', 'vpi_2d') or 'vpi_2d'),
            segmentation_backbone=str(payload.get('segmentation_backbone', 'numpy_baseline_seg') or 'numpy_baseline_seg'),
            keypoint_head=str(payload.get('keypoint_head', 'numpy_baseline_heatmap') or 'numpy_baseline_heatmap'),
            batch_size=int(payload.get('batch_size', 4) or 4),
            max_epochs=int(payload.get('max_epochs', 12) or 12),
            learning_rate=float(payload.get('learning_rate', 1e-3) or 1e-3),
            num_workers=int(payload.get('num_workers', 0) or 0),
            mixed_precision=bool(payload.get('mixed_precision', False)),
            export_onnx=bool(payload.get('export_onnx', False)),
            split_name=str(payload.get('split_name', 'train') or 'train'),
            trainer_backend=str(payload.get('trainer_backend', 'numpy_baseline') or 'numpy_baseline'),
            backend_options=dict(payload.get('backend_options', {}) or {}),
        )

    @classmethod
    def from_file(cls, path: Path) -> 'LaminaCenterTrainingSpec':
        return cls.from_dict(load_structured_config(path))
