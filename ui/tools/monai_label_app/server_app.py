from __future__ import annotations

from typing import Any

from .app import SpineUltrasoundMonaiLabelSkeleton
from .config import MonaiLabelAppConfig


class SpineUltrasoundMonaiLabelServerApp(SpineUltrasoundMonaiLabelSkeleton):
    """Offline server-task facade used by tests and dataset tooling.

    This object intentionally does not depend on a live MONAI Label server. It
    exposes repository-owned infer/save/train task objects so annotation flows
    can be validated in a plain Python environment.
    """

    def __init__(self, config: MonaiLabelAppConfig) -> None:
        super().__init__(config)

    def build_server_descriptor(self) -> dict[str, Any]:
        infer = {name: task.task_descriptor() for name, task in self.registry.infer_tasks.items()}
        return {
            **self.build_manifest(),
            "server_tasks": {
                "infer": infer,
                "save_annotation": list(infer),
                "train": list(infer),
            },
        }
