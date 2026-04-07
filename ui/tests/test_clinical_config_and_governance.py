from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.session_governance_service import SessionGovernanceService


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_clinical_config_service_applies_mainline_defaults() -> None:
    service = ClinicalConfigService()
    config = RuntimeConfig(
        rt_mode="directTorque",
        preferred_link="wifi",
        sdk_robot_class="StandardRobot",
        axis_count=4,
        tool_name="",
        tcp_name="",
        remote_ip="10.0.0.2",
    )
    normalized = service.apply_mainline_defaults(config)
    report = service.build_report(normalized)
    assert normalized.rt_mode == "cartesianImpedance"
    assert normalized.preferred_link == "wired_direct"
    assert normalized.sdk_robot_class == "xMateRobot"
    assert normalized.axis_count == 6
    assert report["summary_state"] == "aligned"


def test_app_controller_blocks_scan_when_config_baseline_invalid(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    controller = AppController(tmp_path, backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.update_config(RuntimeConfig(pressure_lower=9.0, pressure_target=8.0, pressure_upper=7.0))
    controller.start_scan()
    assert controller.workflow_artifacts.session_locked is False
    assert controller.config_report["summary_state"] == "blocked"
    names = {item["name"] for item in controller.config_report["blockers"]}
    assert "压力工作带" in names


def test_export_governance_snapshot_contains_config_and_session_governance(tmp_path: Path) -> None:
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
    controller.run_preprocess()
    controller.run_reconstruction()
    controller.run_assessment()
    path = controller.export_governance_snapshot()
    assert path.exists()
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert "config_report" in payload
    assert "session_governance" in payload
    assert payload["session_governance"]["summary_state"] in {"ready", "warning", "blocked"}


def test_session_governance_service_summarizes_active_session(tmp_path: Path) -> None:
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
    controller.run_preprocess()
    controller.run_reconstruction()
    controller.run_assessment()
    service = SessionGovernanceService()
    snapshot = service.build(controller.session_service.current_session_dir)
    assert snapshot["summary_state"] in {"ready", "warning", "blocked"}
    assert snapshot["artifact_counts"]["registered"] > 0
    assert "release_gate" in snapshot
