from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.algorithms import PluginExecutor, PluginPlane, PluginRegistry
from spine_ultrasound_ui.services.device_readiness import build_device_readiness
from spine_ultrasound_ui.services.mock_backend import MockBackend


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_device_readiness_contract(tmp_path: Path):
    _app()
    backend = MockBackend(tmp_path)
    controller = AppController(tmp_path, backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()
    session_dir = controller.session_service.current_session_dir
    assert session_dir is not None
    readiness = json.loads((session_dir / 'meta' / 'device_readiness.json').read_text(encoding='utf-8'))
    assert readiness['robot_ready'] is True
    assert readiness['protocol_match'] is True


def test_plugin_executor_caches_processing_steps(tmp_path: Path):
    session_dir = tmp_path / 'session'
    session_dir.mkdir(parents=True)
    plane = PluginPlane()
    registry = PluginRegistry(plane.all_plugins())
    executor = PluginExecutor()
    inputs = {'input_artifacts': ['a'], 'output_artifacts': ['b']}
    step1 = executor.run(registry.get('preprocess'), session_dir, inputs)
    step2 = executor.run(registry.get('preprocess'), session_dir, inputs)
    assert step1.step_id == 'preprocess'
    assert step1.to_dict() == step2.to_dict()
    cache_dir = session_dir / 'derived' / '.plugin_cache' / 'preprocess'
    assert cache_dir.exists()


def test_build_device_readiness_from_roster():
    class _Cfg:
        tool_name = 'tool'
        tcp_name = 'tcp'
        load_kg = 1.0
        software_version = '1.0.0'
        build_id = 'build-1'
    readiness = build_device_readiness(
        config=_Cfg(),
        device_roster={
            'robot': {'online': True},
            'camera': {'online': True},
            'ultrasound': {'online': True},
            'pressure': {'online': True},
        },
        protocol_version=1,
    )
    assert readiness['ready_to_lock'] is True
