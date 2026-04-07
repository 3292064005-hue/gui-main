from __future__ import annotations

import importlib
import json
from pathlib import Path
from typing import Any, Iterable

from spine_ultrasound_ui.training.datasets.lamina_center_dataset import LaminaCenterDataset
from spine_ultrasound_ui.training.datasets.uca_dataset import UCADataset
from spine_ultrasound_ui.training.specs.lamina_center_training_spec import LaminaCenterTrainingSpec
from spine_ultrasound_ui.training.specs.uca_training_spec import UCATrainingSpec
from spine_ultrasound_ui.training.exporters.nnunet_dataset_export_service import NnUNetDatasetExportService, NnUNetExportConfig
from spine_ultrasound_ui.utils import ensure_dir, now_text


class BackendTrainingAdapter:
    """Build framework-backed training requests without polluting the runtime path.

    Args:
        backend_name: Canonical backend identifier.
        required_modules: Python modules required by the backend.
        runner_module: Python entrypoint module capable of consuming a training
            request file.

    Returns:
        Adapter instance used by trainer facades.

    Raises:
        No exceptions are raised at construction time.

    Boundary behaviour:
        Backends remain import-safe when optional dependencies are absent. The
        adapter records dependency status and emits a deterministic training
        request so operators can execute the job inside a dedicated training
        environment.
    """

    def __init__(self, backend_name: str, required_modules: Iterable[str], runner_module: str) -> None:
        self.backend_name = str(backend_name)
        self.required_modules = tuple(str(module) for module in required_modules)
        self.runner_module = str(runner_module)

    def build_training_request(
        self,
        *,
        task_name: str,
        spec: dict[str, Any],
        dataset_summary: dict[str, Any],
        output_dir: Path,
        runtime_target: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Create a serialized training request for an external backend.

        Args:
            task_name: Human-readable task name.
            spec: Normalized training specification.
            dataset_summary: Dataset summary produced by a dataset adapter.
            output_dir: Backend request directory.
            runtime_target: Runtime package identifier such as ``lamina_seg``.
            extra: Optional backend-specific payload.

        Returns:
            Backend request manifest including dependency status and launch plan.

        Raises:
            No exceptions are raised when optional dependencies are missing.

        Boundary behaviour:
            The request is always emitted to disk. Missing dependencies are
            reflected in ``dependency_status`` rather than hidden behind a false
            success signal.
        """
        dependency_status = self.dependency_status()
        request_dir = ensure_dir(Path(output_dir) / self.backend_name)
        request_path = request_dir / f'{task_name}_{self.backend_name}_training_request.json'
        command_preview = [
            'python',
            '-m',
            self.runner_module,
            '--request',
            str(request_path),
        ]
        payload = {
            'generated_at': now_text(),
            'task_name': task_name,
            'trainer_backend': self.backend_name,
            'runner_module': self.runner_module,
            'runtime_target': runtime_target,
            'spec': spec,
            'dataset_summary': dataset_summary,
            'dependency_status': dependency_status,
            'launch_plan': {
                'command': command_preview,
                'working_directory': str(request_dir),
            },
            'backend_payload': dict(extra or {}),
        }
        request_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        payload['training_request_path'] = str(request_path)
        return payload

    def dependency_status(self) -> dict[str, Any]:
        """Report import availability for backend dependencies."""
        status = []
        missing = []
        for module_name in self.required_modules:
            available, version = _module_status(module_name)
            status.append({'module': module_name, 'available': available, 'version': version})
            if not available:
                missing.append(module_name)
        return {
            'available': not missing,
            'missing_modules': missing,
            'modules': status,
        }


def summarize_lamina_dataset(dataset: LaminaCenterDataset) -> dict[str, Any]:
    """Summarize lamina-center dataset content for backend requests."""
    case_ids = dataset.case_ids()
    point_counts = [len(dataset[index]['lamina_points'].get('points', [])) for index in range(len(dataset))]
    pair_counts = [len(dataset[index]['vertebra_pairs'].get('pairs', [])) for index in range(len(dataset))]
    return {
        'case_count': len(dataset),
        'case_ids': case_ids,
        'min_point_count': min(point_counts) if point_counts else 0,
        'max_point_count': max(point_counts) if point_counts else 0,
        'min_pair_count': min(pair_counts) if pair_counts else 0,
        'max_pair_count': max(pair_counts) if pair_counts else 0,
    }


def summarize_uca_dataset(dataset: UCADataset) -> dict[str, Any]:
    """Summarize UCA dataset content for backend requests."""
    case_ids = dataset.case_ids()
    best_indices = [int(dataset[index]['best_slice_index']) for index in range(len(dataset))]
    return {
        'case_count': len(dataset),
        'case_ids': case_ids,
        'min_best_slice_index': min(best_indices) if best_indices else 0,
        'max_best_slice_index': max(best_indices) if best_indices else 0,
    }


def build_monai_seg_request(spec: LaminaCenterTrainingSpec, dataset: LaminaCenterDataset) -> dict[str, Any]:
    adapter = BackendTrainingAdapter('monai', ('torch', 'monai'), 'spine_ultrasound_ui.training.backends.monai_runner')
    return adapter.build_training_request(
        task_name=spec.task_name,
        spec=spec.to_dict(),
        dataset_summary=summarize_lamina_dataset(dataset),
        output_dir=spec.output_dir,
        runtime_target='lamina_seg',
        extra={
            'task': 'lamina_segmentation',
            'label_schema': 'schemas/datasets/lamina_center_annotation.schema.json',
            'backbone': spec.segmentation_backbone,
            'backend_options': dict(spec.backend_options),
        },
    )


def build_monai_keypoint_request(spec: LaminaCenterTrainingSpec, dataset: LaminaCenterDataset) -> dict[str, Any]:
    adapter = BackendTrainingAdapter('monai', ('torch', 'monai'), 'spine_ultrasound_ui.training.backends.monai_runner')
    return adapter.build_training_request(
        task_name=spec.task_name,
        spec=spec.to_dict(),
        dataset_summary=summarize_lamina_dataset(dataset),
        output_dir=spec.output_dir,
        runtime_target='lamina_keypoint',
        extra={
            'task': 'lamina_keypoint',
            'label_schema': 'schemas/datasets/lamina_center_annotation.schema.json',
            'head': spec.keypoint_head,
            'backend_options': dict(spec.backend_options),
        },
    )


def build_monai_uca_rank_request(spec: UCATrainingSpec, dataset: UCADataset) -> dict[str, Any]:
    adapter = BackendTrainingAdapter('monai', ('torch', 'monai'), 'spine_ultrasound_ui.training.backends.monai_runner')
    return adapter.build_training_request(
        task_name=spec.task_name,
        spec=spec.to_dict(),
        dataset_summary=summarize_uca_dataset(dataset),
        output_dir=spec.output_dir,
        runtime_target='uca_rank',
        extra={
            'task': 'uca_slice_rank',
            'label_schema': 'schemas/datasets/uca_label.schema.json',
            'ranking_model': spec.ranking_model,
            'backend_options': dict(spec.backend_options),
        },
    )


def build_nnunet_seg_request(spec: LaminaCenterTrainingSpec, dataset: LaminaCenterDataset) -> dict[str, Any]:
    export_service = NnUNetDatasetExportService()
    dataset_id = int(spec.backend_options.get('dataset_id', 601) or 601)
    dataset_name = str(spec.backend_options.get('dataset_name', 'SpineUSLaminaCenter') or 'SpineUSLaminaCenter')
    export_root = Path(spec.backend_options.get('nnunet_raw_root', spec.output_dir / 'nnunet_raw'))
    export_manifest = export_service.export_lamina_center_dataset(
        spec.dataset_root,
        spec.split_file,
        export_root,
        config=NnUNetExportConfig(
            dataset_id=dataset_id,
            dataset_name=dataset_name,
            lamina_point_radius_px=int(spec.backend_options.get('lamina_point_radius_px', 3) or 3),
        ),
    )
    adapter = BackendTrainingAdapter('nnunetv2', ('torch', 'nnunetv2'), 'spine_ultrasound_ui.training.backends.nnunet_runner')
    return adapter.build_training_request(
        task_name=spec.task_name,
        spec=spec.to_dict(),
        dataset_summary=summarize_lamina_dataset(dataset),
        output_dir=spec.output_dir,
        runtime_target='lamina_seg',
        extra={
            'task': 'lamina_segmentation',
            'dataset_json_schema': 'schemas/datasets/lamina_center_annotation.schema.json',
            'plans': str(spec.backend_options.get('plans', 'nnUNetPlans') or 'nnUNetPlans'),
            'configuration': str(spec.backend_options.get('configuration', '2d') or '2d'),
            'fold': str(spec.backend_options.get('fold', '0') or '0'),
            'dataset_id': dataset_id,
            'dataset_name': dataset_name,
            'nnunet_raw_root': str(export_root),
            'nnunet_dataset_dir': str(export_manifest['nnunet_dataset_dir']),
            'conversion_manifest_path': str(Path(export_manifest['nnunet_dataset_dir']) / 'conversion_manifest.json'),
            'backend_options': dict(spec.backend_options),
        },
    )


def _module_status(module_name: str) -> tuple[bool, str]:
    try:
        module = importlib.import_module(module_name)
    except Exception:
        return False, ''
    return True, str(getattr(module, '__version__', '') or '')
