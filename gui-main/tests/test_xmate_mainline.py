from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_xmate_profile_defaults_align_with_er3_mainline():
    profile = load_xmate_profile()
    assert profile.robot_model == 'xmate3'
    assert profile.sdk_robot_class == 'xMateRobot'
    assert profile.axis_count == 6
    assert profile.rt_loop_hz == 1000
    assert profile.direct_torque_in_clinical_mainline is False
    assert profile.rt_network_tolerance_percent == 15
    assert profile.fc_frame_type == 'path'
    assert len(profile.cartesian_impedance) == 6


def test_locked_session_freezes_xmate_profile_and_scan_protocol(tmp_path: Path):
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
    controller.save_results()
    controller.export_summary()

    session_dir = controller.session_service.current_session_dir
    assert session_dir is not None
    manifest = json.loads((session_dir / 'meta' / 'manifest.json').read_text(encoding='utf-8'))
    profile = json.loads((session_dir / 'meta' / 'xmate_profile.json').read_text(encoding='utf-8'))
    registration = json.loads((session_dir / 'meta' / 'patient_registration.json').read_text(encoding='utf-8'))
    protocol = json.loads((session_dir / 'derived' / 'preview' / 'scan_protocol.json').read_text(encoding='utf-8'))

    assert manifest['robot_profile']['axis_count'] == 6
    assert profile['sdk_robot_class'] == 'xMateRobot'
    assert registration['patient_frame']['name'] == 'patient_spine'
    assert registration['source'] == 'camera_backed_registration'
    assert 'camera_observations' in registration
    assert protocol['clinical_control_modes']['scan'] == controller.config.rt_mode
    assert protocol['rt_parameters']['rt_network_tolerance_percent'] == 15
    assert manifest['artifacts']['xmate_profile'] == 'meta/xmate_profile.json'
    assert manifest['artifacts']['scan_protocol'] == 'derived/preview/scan_protocol.json'
