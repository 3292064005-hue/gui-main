import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend


def _app() -> QApplication:
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_dataset_export_services_materialize_cases_and_manifest(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_procedure()
    controller.safe_retreat()
    controller.save_results()
    controller.export_summary()
    controller.run_preprocess()
    controller.run_reconstruction()
    controller.run_assessment()

    dataset_root = tmp_path / 'datasets' / 'lamina_center'
    export_payload = controller.export_lamina_training_case(dataset_root)
    assert Path(export_payload['case_dir']).exists()
    manifest = controller.build_annotation_manifest(dataset_root)
    assert manifest['case_count'] >= 1
    assert (dataset_root / 'annotation_manifest.json').exists()
    split = json.loads((dataset_root / 'splits' / 'split_v1.json').read_text(encoding='utf-8'))
    assert set(split.keys()) == {'train', 'val', 'test'}

    uca_root = tmp_path / 'datasets' / 'uca'
    uca_payload = controller.export_uca_training_case(uca_root)
    assert Path(uca_payload['case_dir']).exists()
    assert Path(uca_payload['coronal_slice_dir']).exists()
