from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_runtime_asset_service_exposes_identity_and_contracts(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    service = SdkRuntimeAssetService()
    snapshot = service.refresh(backend, RuntimeConfig())
    assert snapshot["identity_contract"]["robot_model"] == "xmate3"
    assert snapshot["clinical_mainline_contract"]["rt_loop_hz"] == 1000
    assert snapshot["clinical_mainline_contract"]["required_sequence"] == ["connect_robot", "power_on", "set_auto_mode", "lock_session", "load_scan_plan", "start_procedure", "safe_retreat"]
    assert snapshot["clinical_mainline_contract"]["runtime_owned_phase_sequence"] == ["approach_prescan", "seek_contact", "contact_hold", "scan_follow", "controlled_retract"]
    assert snapshot["recovery_contract"]["safe_retreat_enabled"] is True
    assert snapshot["session_freeze"]["session_locked"] is False


def test_session_freeze_reflects_locked_runtime_config(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    cfg = RuntimeConfig(cartesian_impedance=[1200.0, 1100.0, 900.0, 80.0, 70.0, 60.0], desired_wrench_n=[0.0, 0.0, 10.0, 0.0, 0.0, 0.0])
    backend.send_command("connect_robot", {})
    backend.send_command("power_on", {})
    backend.send_command("set_auto_mode", {})
    reply = backend.send_command("lock_session", {
        "session_id": "sess-001",
        "session_dir": str(tmp_path / "session"),
        "config_snapshot": cfg.to_dict(),
        "device_roster": {},
        "scan_plan_hash": "hash-001",
    })
    assert reply.ok is True
    service = SdkRuntimeAssetService()
    snapshot = service.refresh(backend, cfg)
    assert snapshot["session_freeze"]["session_locked"] is True
    assert snapshot["session_freeze"]["session_id"] == "sess-001"
    assert snapshot["session_freeze"]["cartesian_impedance"][0] == 1200.0



def test_runtime_asset_service_exposes_authority_and_release_contracts(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    service = SdkRuntimeAssetService()
    snapshot = service.refresh(backend, RuntimeConfig())
    assert snapshot["capability_contract"]["sdk_family"] == "ROKAE xCore SDK (C++)"
    assert snapshot["model_authority_contract"]["authoritative_kernel"] == "cpp_robot_core"
    assert snapshot["release_contract"]["session_locked"] is False
    assert snapshot["release_contract"]["runtime_source"] == "mock_runtime_contract"
