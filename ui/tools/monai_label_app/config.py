from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class MonaiLabelAppConfig:
    """Structured configuration for the offline MONAI Label skeleton.

    The repository ships this config object so offline annotation tooling can be
    exercised without importing MONAI Label itself. Only dataset paths and task
    exposure are tracked here; runtime/UI modules must remain independent.
    """

    dataset_root: Path
    task_names: list[str] = field(default_factory=lambda: ["lamina_center", "uca_auxiliary"])
    studies_subdir: str = "raw_cases"
    annotations_subdir: str = "annotations"
    splits_subdir: str = "splits"
    app_name: str = "spine_ultrasound_monai_label"
    app_version: str = "0.1.0"

    def __post_init__(self) -> None:
        self.dataset_root = Path(self.dataset_root)
        self.task_names = [str(name).strip() for name in self.task_names if str(name).strip()]
        if not self.task_names:
            raise ValueError("task_names must not be empty")

    @property
    def studies_path(self) -> Path:
        return self.dataset_root / self.studies_subdir

    @property
    def annotations_path(self) -> Path:
        return self.dataset_root / self.annotations_subdir

    @property
    def splits_path(self) -> Path:
        return self.dataset_root / self.splits_subdir

    def to_dict(self) -> dict[str, object]:
        return {
            "app_name": self.app_name,
            "app_version": self.app_version,
            "dataset_root": str(self.dataset_root),
            "studies_path": str(self.studies_path),
            "annotations_path": str(self.annotations_path),
            "splits_path": str(self.splits_path),
            "task_names": list(self.task_names),
        }
