from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .common import load_structured_config, normalize_trainer_backend


@dataclass(slots=True)
class UCATrainingSpec:
    """Structured training configuration for the auxiliary-UCA pipeline.

    The specification mirrors :class:`LaminaCenterTrainingSpec` but is tailored
    to slice-ranking and lateral bone-feature segmentation tasks.
    """

    dataset_root: Path
    split_file: Path
    output_dir: Path
    task_name: str = 'uca_auxiliary'
    ranking_model: str = 'numpy_baseline_rank'
    segmentation_backbone: str = 'numpy_baseline_seg'
    batch_size: int = 8
    max_epochs: int = 10
    learning_rate: float = 1e-3
    num_workers: int = 0
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
        if not self.ranking_model.strip():
            raise ValueError('ranking_model must not be empty')
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
    def from_dict(cls, data: dict[str, Any]) -> 'UCATrainingSpec':
        payload = dict(data)
        return cls(
            dataset_root=Path(payload['dataset_root']),
            split_file=Path(payload['split_file']),
            output_dir=Path(payload['output_dir']),
            task_name=str(payload.get('task_name', 'uca_auxiliary') or 'uca_auxiliary'),
            ranking_model=str(payload.get('ranking_model', 'numpy_baseline_rank') or 'numpy_baseline_rank'),
            segmentation_backbone=str(payload.get('segmentation_backbone', 'numpy_baseline_seg') or 'numpy_baseline_seg'),
            batch_size=int(payload.get('batch_size', 8) or 8),
            max_epochs=int(payload.get('max_epochs', 10) or 10),
            learning_rate=float(payload.get('learning_rate', 1e-3) or 1e-3),
            num_workers=int(payload.get('num_workers', 0) or 0),
            export_onnx=bool(payload.get('export_onnx', False)),
            split_name=str(payload.get('split_name', 'train') or 'train'),
            trainer_backend=str(payload.get('trainer_backend', 'numpy_baseline') or 'numpy_baseline'),
            backend_options=dict(payload.get('backend_options', {}) or {}),
        )

    @classmethod
    def from_file(cls, path: Path) -> 'UCATrainingSpec':
        return cls.from_dict(load_structured_config(path))
