from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import MonaiLabelAppConfig
from .tasks import OfflineTaskRegistry


class SpineUltrasoundMonaiLabelSkeleton:
    """Repository-local MONAI Label skeleton for offline annotation flows."""

    def __init__(self, config: MonaiLabelAppConfig) -> None:
        self.config = config
        self.registry = OfflineTaskRegistry(config)

    def build_manifest(self) -> dict[str, Any]:
        return {
            **self.config.to_dict(),
            "tasks": self.registry.descriptors(),
            "studies_path": str(self.config.studies_path),
        }

    def validate_dataset_layout(self) -> dict[str, Any]:
        return {
            "dataset_root_exists": self.config.dataset_root.exists(),
            "studies_path_exists": self.config.studies_path.exists(),
            "annotations_path_exists": self.config.annotations_path.exists(),
            "splits_path_exists": self.config.splits_path.exists(),
        }

    def write_manifest(self, output_path: Path) -> dict[str, Any]:
        manifest = self.build_manifest()
        output = Path(output_path)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest
