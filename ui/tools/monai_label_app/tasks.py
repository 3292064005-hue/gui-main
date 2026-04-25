from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import MonaiLabelAppConfig


@dataclass(frozen=True)
class TaskResult:
    """Normalized result envelope returned by repository-local MONAI tasks."""

    payload: dict[str, Any]


class _BaseOfflineTask:
    def __init__(self, config: MonaiLabelAppConfig, *, task_name: str) -> None:
        self.config = config
        self.task_name = task_name

    def _resolve_case_dir(self, case_id: str) -> Path:
        normalized = str(case_id).replace("\\", "/").replace("__", "/")
        parts = [part for part in normalized.split("/") if part]
        if len(parts) < 2:
            raise ValueError(f"invalid case_id: {case_id}")
        return self.config.studies_path / parts[-2] / parts[-1]

    def _annotation_stem(self, case_id: str) -> str:
        normalized = str(case_id).replace("\\", "/").replace("__", "/")
        parts = [part for part in normalized.split("/") if part]
        if len(parts) < 2:
            raise ValueError(f"invalid case_id: {case_id}")
        return f"{parts[-2]}__{parts[-1]}"

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _write_json(path: Path, payload: dict[str, Any]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")

    def task_descriptor(self) -> dict[str, Any]:
        raise NotImplementedError

    def infer(self, case_id: str) -> TaskResult:
        raise NotImplementedError

    def save_annotation(self, case_id: str, payload: dict[str, Any]) -> TaskResult:
        raise NotImplementedError

    def train_request(self, output_root: Path, *, backend: str) -> TaskResult:
        payload = {
            "task_name": self.task_name,
            "trainer_backend": str(backend),
            "dataset_root": str(self.config.dataset_root),
        }
        path = Path(output_root) / f"{self.task_name}_{backend}_training_request.json"
        self._write_json(path, payload)
        payload["training_request_path"] = str(path)
        return TaskResult(payload)


class LaminaCenterTask(_BaseOfflineTask):
    def __init__(self, config: MonaiLabelAppConfig) -> None:
        super().__init__(config, task_name="lamina_center")

    def task_descriptor(self) -> dict[str, Any]:
        return {
            "name": self.task_name,
            "kind": "keypoint",
            "reads": ["lamina_candidates.json", "annotations/lamina_centers/*.json"],
            "writes": ["annotations/lamina_centers/*.json"],
        }

    def infer(self, case_id: str) -> TaskResult:
        annotation_path = self.config.annotations_path / "lamina_centers" / f"{self._annotation_stem(case_id)}.json"
        if annotation_path.exists():
            payload = self._read_json(annotation_path)
            payload["source"] = "existing_annotation"
            payload.setdefault("lamina_centers_path", str(annotation_path))
            return TaskResult(payload)
        case_dir = self._resolve_case_dir(case_id)
        candidates = self._read_json(case_dir / "lamina_candidates.json")
        points = [
            {
                "candidate_id": str(item.get("candidate_id", "")),
                "vertebra_id": str(item.get("vertebra_id", "")),
                "side": str(item.get("side", "")),
                "x_mm": float(item.get("x_mm", 0.0) or 0.0),
                "y_mm": float(item.get("y_mm", 0.0) or 0.0),
                "z_mm": float(item.get("z_mm", 0.0) or 0.0),
                "confidence": float(item.get("confidence", 0.0) or 0.0),
            }
            for item in list(candidates.get("candidates", []))
        ]
        return TaskResult(
            {
                "case_id": case_id,
                "source": "reconstruction_candidates",
                "lamina_centers": {"points": points},
                "lamina_centers_path": str(annotation_path),
            }
        )

    def save_annotation(self, case_id: str, payload: dict[str, Any]) -> TaskResult:
        annotation_path = self.config.annotations_path / "lamina_centers" / f"{self._annotation_stem(case_id)}.json"
        persisted = {
            "case_id": case_id,
            "source": str(payload.get("source", "manual_annotation") or "manual_annotation"),
            "lamina_centers": dict(payload.get("lamina_centers", {})),
        }
        self._write_json(annotation_path, persisted)
        return TaskResult(
            {
                "saved": True,
                "lamina_centers_path": str(annotation_path),
                "case_id": case_id,
            }
        )


class UcaAuxiliaryTask(_BaseOfflineTask):
    def __init__(self, config: MonaiLabelAppConfig) -> None:
        super().__init__(config, task_name="uca_auxiliary")

    def task_descriptor(self) -> dict[str, Any]:
        return {
            "name": self.task_name,
            "kind": "ranking",
            "reads": ["ranked_slice_candidates.json", "uca_measurement.json", "annotations/uca_labels/*.json"],
            "writes": ["annotations/uca_labels/*.json"],
        }

    def infer(self, case_id: str) -> TaskResult:
        annotation_path = self.config.annotations_path / "uca_labels" / f"{self._annotation_stem(case_id)}.json"
        if annotation_path.exists():
            payload = self._read_json(annotation_path)
            payload["source"] = "existing_annotation"
            payload.setdefault("uca_label_path", str(annotation_path))
            return TaskResult(payload)
        case_dir = self._resolve_case_dir(case_id)
        ranked = self._read_json(case_dir / "ranked_slice_candidates.json")
        measurement = self._read_json(case_dir / "uca_measurement.json")
        best_slice = dict(ranked.get("best_slice", {}))
        payload = {
            "case_id": case_id,
            "source": "reconstruction_candidates",
            "uca_labels": {
                "best_slice_index": int(best_slice.get("slice_index", 0) or 0),
                "best_slice_score": float(best_slice.get("score", 0.0) or 0.0),
                "ranked_slices": list(ranked.get("ranked_slices", [])),
                "angle_deg": float(measurement.get("angle_deg", 0.0) or 0.0),
                "requires_manual_review": bool(measurement.get("requires_manual_review", False)),
            },
            "uca_label_path": str(annotation_path),
        }
        return TaskResult(payload)

    def save_annotation(self, case_id: str, payload: dict[str, Any]) -> TaskResult:
        annotation_path = self.config.annotations_path / "uca_labels" / f"{self._annotation_stem(case_id)}.json"
        persisted = {
            "case_id": case_id,
            "source": str(payload.get("source", "manual_annotation") or "manual_annotation"),
            "uca_labels": dict(payload.get("uca_labels", {})),
        }
        self._write_json(annotation_path, persisted)
        return TaskResult(
            {
                "saved": True,
                "uca_label_path": str(annotation_path),
                "case_id": case_id,
            }
        )


class OfflineTaskRegistry:
    def __init__(self, config: MonaiLabelAppConfig) -> None:
        builders = {
            "lamina_center": LaminaCenterTask,
            "uca_auxiliary": UcaAuxiliaryTask,
        }
        self.infer_tasks: dict[str, _BaseOfflineTask] = {}
        for name in config.task_names:
            builder = builders.get(name)
            if builder is None:
                raise ValueError(f"unsupported MONAI Label task: {name}")
            self.infer_tasks[name] = builder(config)

    def descriptors(self) -> list[dict[str, Any]]:
        return [task.task_descriptor() for task in self.infer_tasks.values()]
