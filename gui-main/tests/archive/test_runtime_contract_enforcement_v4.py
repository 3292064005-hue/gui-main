from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.ipc_protocol import protocol_schema


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_protocol_schema_exposes_v4_contract_queries() -> None:
    schema = protocol_schema()
    assert "get_capability_contract" in schema["commands"]
    assert "get_model_authority_contract" in schema["commands"]
    assert "get_release_contract" in schema["commands"]


def test_lock_session_rejects_non_mainline_control_source(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    backend.send_command("connect_robot", {})
    backend.send_command("power_on", {})
    backend.send_command("set_auto_mode", {})
    cfg = RuntimeConfig(requires_single_control_source=False)
    reply = backend.send_command("lock_session", {
        "session_id": "sess-bad",
        "session_dir": str(tmp_path / "session"),
        "config_snapshot": cfg.to_dict(),
        "device_roster": {},
        "scan_plan_hash": "hash-001",
    })
    assert reply.ok is False
    assert "单控制源" in reply.message or "single control source" in reply.message


def test_release_contract_reflects_compile_and_freeze_consistency(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    backend.send_command("connect_robot", {})
    backend.send_command("power_on", {})
    backend.send_command("set_auto_mode", {})
    good_cfg = RuntimeConfig()
    lock_reply = backend.send_command("lock_session", {
        "session_id": "sess-ok",
        "session_dir": str(tmp_path / "session-ok"),
        "config_snapshot": good_cfg.to_dict(),
        "device_roster": {},
        "scan_plan_hash": "frozen-hash",
    })
    assert lock_reply.ok is True
    release_before = backend.send_command("get_release_contract", {}).data
    assert release_before["session_locked"] is True
    assert release_before["session_freeze_consistent"] is True
    assert release_before["compile_ready"] is False
