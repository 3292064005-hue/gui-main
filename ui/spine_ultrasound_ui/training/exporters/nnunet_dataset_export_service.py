from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image, ImageDraw

from spine_ultrasound_ui.training.datasets.lamina_center_dataset import LaminaCenterDataset
from spine_ultrasound_ui.training.datasets.uca_dataset import UCADataset
from spine_ultrasound_ui.utils import ensure_dir, now_text


@dataclass(slots=True)
class NnUNetExportConfig:
    """Structured configuration for exporting an nnU-Net raw dataset.

    Args:
        dataset_id: Numeric dataset identifier used by nnU-Net.
        dataset_name: Human-readable dataset suffix appended to ``DatasetXXX``.
        file_ending: Exported image file ending. The current implementation
            emits natural 2D images and labels as PNG files.
        image_reader_writer: Reader/writer class written into ``dataset.json``.
        lamina_point_radius_px: Disk radius used when rasterizing lamina-center
            point annotations into segmentation masks.

    Returns:
        Immutable export configuration.

    Raises:
        ValueError: Raised when identifiers or dimensions are invalid.

    Boundary behaviour:
        The configuration is intentionally narrow: only 2D natural-image export
        is supported because the current lamina-center and UCA training cases are
        based on coronal VPI projections rather than full volumetric nnU-Net
        inputs.
    """

    dataset_id: int
    dataset_name: str
    file_ending: str = ".png"
    image_reader_writer: str = "NaturalImage2DIO"
    lamina_point_radius_px: int = 3

    def validate(self) -> None:
        if self.dataset_id <= 0:
            raise ValueError("dataset_id must be positive")
        if not str(self.dataset_name).strip():
            raise ValueError("dataset_name must not be empty")
        if self.file_ending.lower() != ".png":
            raise ValueError("only .png export is currently supported")
        if self.lamina_point_radius_px < 1:
            raise ValueError("lamina_point_radius_px must be positive")

    @property
    def folder_name(self) -> str:
        return f"Dataset{self.dataset_id:03d}_{self.dataset_name}"


class NnUNetDatasetExportService:
    """Export exported spine-ultrasound datasets into nnU-Net raw format.

    The service converts the repository-owned lamina-center and UCA datasets into
    2D natural-image nnU-Net raw datasets. Exported images follow the official
    naming contract ``imagesTr/<case>_0000.png`` and ``labelsTr/<case>.png``
    while dataset metadata is emitted into ``dataset.json``.
    """

    def export_lamina_center_dataset(
        self,
        dataset_root: Path,
        split_file: Path,
        output_root: Path,
        *,
        config: NnUNetExportConfig,
    ) -> dict[str, Any]:
        """Export lamina-center annotations as an nnU-Net raw segmentation dataset.

        Args:
            dataset_root: Root directory of the exported lamina-center dataset.
            split_file: Patient-level split file.
            output_root: Root directory containing ``nnUNet_raw``.
            config: Export configuration.

        Returns:
            Conversion manifest describing the generated dataset.

        Raises:
            FileNotFoundError: Raised when the dataset root or split file does
                not exist.
            ValueError: Raised when the configuration is invalid or no training
                cases can be exported.

        Boundary behaviour:
            Test split cases are exported into ``imagesTs`` without labels.
            Cases missing annotations are skipped from the training set instead
            of producing empty segmentation masks, because nnU-Net expects valid
            labels for all training images.
        """
        config.validate()
        dataset_root = Path(dataset_root)
        split_file = Path(split_file)
        output_root = Path(output_root)
        if not dataset_root.exists():
            raise FileNotFoundError(dataset_root)
        if not split_file.exists():
            raise FileNotFoundError(split_file)
        split_payload = json.loads(split_file.read_text(encoding="utf-8"))
        target_dir = self._prepare_dataset_root(output_root, config)
        images_tr = ensure_dir(target_dir / "imagesTr")
        labels_tr = ensure_dir(target_dir / "labelsTr")
        images_ts = ensure_dir(target_dir / "imagesTs")

        exported_training: list[dict[str, Any]] = []
        exported_testing: list[dict[str, Any]] = []
        for split_name, is_training in (("train", True), ("val", True), ("test", False)):
            for case_id in [str(case_id) for case_id in split_payload.get(split_name, [])]:
                patient_id, session_id = LaminaCenterDataset._split_case_id(case_id)
                case_dir = dataset_root / "raw_cases" / patient_id / session_id
                if not case_dir.exists():
                    continue
                image = self._load_png_ready_image(case_dir / "coronal_vpi.npz")
                case_name = self._case_file_id(patient_id, session_id)
                image_path = (images_tr if is_training else images_ts) / f"{case_name}_0000{config.file_ending}"
                if is_training:
                    annotation_path = dataset_root / "annotations" / "lamina_centers" / f"{patient_id}__{session_id}.json"
                    if not annotation_path.exists():
                        continue
                    self._write_png(image_path, image)
                    label_mask = self._rasterize_lamina_mask(
                        image_shape=image.shape,
                        annotation_payload=json.loads(annotation_path.read_text(encoding="utf-8")),
                        point_radius_px=config.lamina_point_radius_px,
                    )
                    label_path = labels_tr / f"{case_name}{config.file_ending}"
                    self._write_png(label_path, label_mask)
                    exported_training.append({
                        "case_id": case_id,
                        "image_path": str(image_path),
                        "label_path": str(label_path),
                        "source_split": split_name,
                    })
                else:
                    self._write_png(image_path, image)
                    exported_testing.append({
                        "case_id": case_id,
                        "image_path": str(image_path),
                        "source_split": split_name,
                    })
        if not exported_training:
            raise ValueError("nnU-Net lamina export requires at least one annotated training case")

        dataset_json = {
            "name": config.folder_name,
            "description": "Spine ultrasound lamina-center segmentation export",
            "channel_names": {"0": "ultrasound"},
            "labels": {"background": 0, "left_lamina": 1, "right_lamina": 2},
            "numTraining": len(exported_training),
            "file_ending": config.file_ending,
            "overwrite_image_reader_writer": config.image_reader_writer,
        }
        (target_dir / "dataset.json").write_text(json.dumps(dataset_json, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest = {
            "generated_at": now_text(),
            "dataset_role": "lamina_center_nnunet",
            "dataset_root": str(dataset_root),
            "split_file": str(split_file),
            "nnunet_dataset_dir": str(target_dir),
            "dataset_id": config.dataset_id,
            "dataset_name": config.dataset_name,
            "training_cases": exported_training,
            "testing_cases": exported_testing,
            "dataset_json": dataset_json,
        }
        (target_dir / "conversion_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest

    def export_uca_bone_feature_dataset(
        self,
        dataset_root: Path,
        split_file: Path,
        output_root: Path,
        *,
        config: NnUNetExportConfig,
    ) -> dict[str, Any]:
        """Export UCA bone-feature masks as an nnU-Net raw segmentation dataset.

        Args:
            dataset_root: Root directory of the exported UCA dataset.
            split_file: Patient-level split file.
            output_root: Root directory containing ``nnUNet_raw``.
            config: Export configuration.

        Returns:
            Conversion manifest describing the generated dataset.

        Raises:
            FileNotFoundError: Raised when the dataset root or split file does
                not exist.
            ValueError: Raised when no annotated training masks can be exported.

        Boundary behaviour:
            The exporter writes one full-VPI image per case because the current
            UCA auxiliary dataset stores feature masks against the VPI canvas.
        """
        config.validate()
        dataset_root = Path(dataset_root)
        split_file = Path(split_file)
        output_root = Path(output_root)
        if not dataset_root.exists():
            raise FileNotFoundError(dataset_root)
        if not split_file.exists():
            raise FileNotFoundError(split_file)
        split_payload = json.loads(split_file.read_text(encoding="utf-8"))
        target_dir = self._prepare_dataset_root(output_root, config)
        images_tr = ensure_dir(target_dir / "imagesTr")
        labels_tr = ensure_dir(target_dir / "labelsTr")
        images_ts = ensure_dir(target_dir / "imagesTs")

        exported_training: list[dict[str, Any]] = []
        exported_testing: list[dict[str, Any]] = []
        for split_name, is_training in (("train", True), ("val", True), ("test", False)):
            for case_id in [str(case_id) for case_id in split_payload.get(split_name, [])]:
                patient_id, session_id = UCADataset._split_case_id(case_id)
                case_dir = dataset_root / "raw_cases" / patient_id / session_id
                if not case_dir.exists():
                    continue
                image = self._load_png_ready_image(case_dir / "coronal_vpi.npz")
                case_name = self._case_file_id(patient_id, session_id)
                image_path = (images_tr if is_training else images_ts) / f"{case_name}_0000{config.file_ending}"
                if is_training:
                    mask_path = dataset_root / "annotations" / "bone_feature_masks" / f"{patient_id}__{session_id}.npz"
                    if not mask_path.exists():
                        continue
                    self._write_png(image_path, image)
                    mask_array = self._load_mask_npz(mask_path, expected_shape=image.shape)
                    label_path = labels_tr / f"{case_name}{config.file_ending}"
                    self._write_png(label_path, mask_array.astype(np.uint8))
                    exported_training.append({
                        "case_id": case_id,
                        "image_path": str(image_path),
                        "label_path": str(label_path),
                        "source_split": split_name,
                    })
                else:
                    self._write_png(image_path, image)
                    exported_testing.append({
                        "case_id": case_id,
                        "image_path": str(image_path),
                        "source_split": split_name,
                    })
        if not exported_training:
            raise ValueError("nnU-Net UCA export requires at least one annotated training case")

        dataset_json = {
            "name": config.folder_name,
            "description": "Spine ultrasound UCA bone-feature segmentation export",
            "channel_names": {"0": "ultrasound"},
            "labels": {"background": 0, "bony_feature": 1},
            "numTraining": len(exported_training),
            "file_ending": config.file_ending,
            "overwrite_image_reader_writer": config.image_reader_writer,
        }
        (target_dir / "dataset.json").write_text(json.dumps(dataset_json, indent=2, ensure_ascii=False), encoding="utf-8")
        manifest = {
            "generated_at": now_text(),
            "dataset_role": "uca_bone_feature_nnunet",
            "dataset_root": str(dataset_root),
            "split_file": str(split_file),
            "nnunet_dataset_dir": str(target_dir),
            "dataset_id": config.dataset_id,
            "dataset_name": config.dataset_name,
            "training_cases": exported_training,
            "testing_cases": exported_testing,
            "dataset_json": dataset_json,
        }
        (target_dir / "conversion_manifest.json").write_text(json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8")
        return manifest

    @staticmethod
    def _prepare_dataset_root(output_root: Path, config: NnUNetExportConfig) -> Path:
        root = ensure_dir(Path(output_root)) / config.folder_name
        ensure_dir(root)
        return root

    @staticmethod
    def _case_file_id(patient_id: str, session_id: str) -> str:
        safe_patient = str(patient_id).replace("/", "_").replace("\\", "_")
        safe_session = str(session_id).replace("/", "_").replace("\\", "_")
        return f"{safe_patient}__{safe_session}"

    @staticmethod
    def _load_png_ready_image(vpi_path: Path) -> np.ndarray:
        payload = np.load(vpi_path, allow_pickle=False)
        if not payload.files:
            raise ValueError(f"VPI payload is empty: {vpi_path}")
        image = np.asarray(payload[payload.files[0]], dtype=np.float32)
        if image.ndim != 2 or image.size == 0:
            raise ValueError(f"VPI payload must be a non-empty 2D array: {vpi_path}")
        finite = np.nan_to_num(image, nan=0.0, posinf=0.0, neginf=0.0)
        low = float(finite.min())
        high = float(finite.max())
        if high <= low:
            return np.zeros_like(finite, dtype=np.uint8)
        scaled = ((finite - low) / (high - low) * 255.0).clip(0.0, 255.0)
        return scaled.astype(np.uint8)

    @staticmethod
    def _load_mask_npz(path: Path, *, expected_shape: tuple[int, ...]) -> np.ndarray:
        payload = np.load(path, allow_pickle=False)
        if not payload.files:
            return np.zeros(expected_shape, dtype=np.uint8)
        mask = np.asarray(payload[payload.files[0]], dtype=np.float32)
        if mask.shape != expected_shape:
            raise ValueError(f"mask shape {mask.shape} does not match expected shape {expected_shape}")
        return (mask > 0).astype(np.uint8)

    @staticmethod
    def _write_png(path: Path, array: np.ndarray) -> None:
        ensure_dir(path.parent)
        Image.fromarray(np.asarray(array)).save(path)

    @staticmethod
    def _rasterize_lamina_mask(
        *,
        image_shape: tuple[int, int],
        annotation_payload: dict[str, Any],
        point_radius_px: int,
    ) -> np.ndarray:
        rows, cols = image_shape
        image = Image.new("L", (cols, rows), 0)
        draw = ImageDraw.Draw(image)
        for point in annotation_payload.get("points", []):
            if not isinstance(point, dict):
                continue
            x_mm = float(point.get("x_mm", 0.0) or 0.0)
            y_mm = float(point.get("y_mm", 0.0) or 0.0)
            side = str(point.get("side", "")).strip().lower()
            label_value = 1 if side == "left" else 2 if side == "right" else 0
            if label_value == 0:
                continue
            col = int(np.clip(round((x_mm + 120.0) / 240.0 * max(1, cols - 1)), 0, cols - 1))
            row = int(np.clip(round((y_mm / 100.0) * max(1, rows - 1)), 0, rows - 1))
            draw.ellipse(
                (col - point_radius_px, row - point_radius_px, col + point_radius_px, row + point_radius_px),
                fill=int(label_value),
            )
        return np.asarray(image, dtype=np.uint8)
