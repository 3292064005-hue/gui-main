from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.sdk_capability_service import SdkCapabilityService


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_sdk_alignment_blocks_direct_torque_and_missing_single_source():
    service = SdkCapabilityService()
    config = RuntimeConfig(rt_mode="directTorque", requires_single_control_source=False)
    payload = service.build(config, {"operate_mode": "manual"})
    assert payload["summary_state"] == "blocked"
    names = {item["name"] for item in payload["blockers"]}
    assert "直接力矩控制" in names
    assert "单控制源" in names


def test_sdk_alignment_accepts_er3_cartesian_impedance_mainline():
    service = SdkCapabilityService()
    config = RuntimeConfig()
    payload = service.build(config, {"operate_mode": "automatic"})
    assert payload["summary_state"] == "aligned"
    assert payload["feature_coverage"]["coverage_percent"] == 100


def test_runtime_config_carries_sdk_network_fields():
    config = RuntimeConfig(remote_ip="192.168.0.160", local_ip="192.168.0.22")
    payload = config.to_dict()
    roundtrip = RuntimeConfig.from_dict(payload)
    assert roundtrip.remote_ip == "192.168.0.160"
    assert roundtrip.local_ip == "192.168.0.22"


def test_view_state_contains_sdk_alignment(tmp_path: Path):
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    payloads = []
    controller.status_updated.connect(payloads.append)
    controller._emit_status()
    assert payloads
    assert "sdk_alignment" in payloads[-1]
    assert payloads[-1]["sdk_alignment"]["sdk_family"] == "ROKAE xCore SDK (C++)"
