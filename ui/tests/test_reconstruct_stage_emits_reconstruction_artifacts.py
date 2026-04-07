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


def _build_session(tmp_path: Path) -> Path:
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()
    controller.safe_retreat()
    controller.save_results()
    controller.export_summary()
    controller.run_preprocess()
    controller.run_reconstruction()
    assert controller.session_service.current_session_dir is not None
    return controller.session_service.current_session_dir


def test_reconstruct_stage_emits_reconstruction_artifacts(tmp_path: Path) -> None:
    session_dir = _build_session(tmp_path)
    expected = {
        "reconstruction_input_index": session_dir / "derived" / "reconstruction" / "reconstruction_input_index.json",
        "coronal_vpi": session_dir / "derived" / "reconstruction" / "coronal_vpi.npz",
        "vpi_preview": session_dir / "derived" / "reconstruction" / "vpi_preview.png",
        "bone_mask": session_dir / "derived" / "reconstruction" / "bone_mask.npz",
        "frame_anatomy_points": session_dir / "derived" / "reconstruction" / "frame_anatomy_points.json",
        "lamina_candidates": session_dir / "derived" / "reconstruction" / "lamina_candidates.json",
        "pose_series": session_dir / "derived" / "reconstruction" / "pose_series.json",
        "reconstruction_evidence": session_dir / "derived" / "reconstruction" / "reconstruction_evidence.json",
        "spine_curve": session_dir / "derived" / "reconstruction" / "spine_curve.json",
        "landmark_track": session_dir / "derived" / "reconstruction" / "landmark_track.json",
        "reconstruction_summary": session_dir / "derived" / "reconstruction" / "reconstruction_summary.json",
    }
    for target in expected.values():
        assert target.exists(), target

    manifest = json.loads((session_dir / "meta" / "manifest.json").read_text(encoding="utf-8"))
    for name, target in expected.items():
        assert manifest["artifacts"][name] == str(target.relative_to(session_dir)).replace("\\", "/")

    summary = json.loads(expected["reconstruction_summary"].read_text(encoding="utf-8"))
    assert summary["point_count"] >= 0
    assert 0.0 <= summary["confidence"] <= 1.0
    assert "measurement_source" in summary
