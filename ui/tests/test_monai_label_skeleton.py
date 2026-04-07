from pathlib import Path

from tools.monai_label_app.app import SpineUltrasoundMonaiLabelSkeleton
from tools.monai_label_app.config import MonaiLabelAppConfig


def test_monai_label_skeleton_manifest_and_validation(tmp_path: Path) -> None:
    dataset_root = tmp_path / 'datasets' / 'lamina_center'
    (dataset_root / 'raw_cases').mkdir(parents=True, exist_ok=True)
    app = SpineUltrasoundMonaiLabelSkeleton(MonaiLabelAppConfig(dataset_root=dataset_root))
    manifest = app.build_manifest()
    assert manifest['studies_path'].endswith('raw_cases')
    task_names = {task['name'] for task in manifest['tasks']}
    assert {'lamina_center', 'uca_auxiliary'} <= task_names
    validation = app.validate_dataset_layout()
    assert validation['dataset_root_exists'] is True
    output_path = tmp_path / 'annotation_manifest.json'
    app.write_manifest(output_path)
    assert output_path.exists()
