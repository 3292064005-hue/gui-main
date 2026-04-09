from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.core.runtime_persistence_service import RuntimePersistenceService
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.config_service import ConfigService
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



def test_restore_default_config_resets_to_profile_baseline(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    controller = AppController(tmp_path, backend)
    controller.update_config(RuntimeConfig(rt_mode='directTorque', preferred_link='wifi', requires_single_control_source=False))
    controller.restore_default_config()
    assert controller.config.rt_mode == 'cartesianImpedance'
    assert controller.config.preferred_link == 'wired_direct'
    assert controller.config.requires_single_control_source is True


def test_clinical_config_service_blocks_mainline_drift() -> None:
    service = ClinicalConfigService()
    report = service.build_report(RuntimeConfig(rt_mode='directTorque', preferred_link='wifi', requires_single_control_source=False))
    assert report['summary_state'] == 'blocked'
    names = {item['name'] for item in report['blockers']}
    assert '主线配置贴合度' in names


def test_runtime_persistence_clamps_drifted_startup_config_to_profile_baseline(tmp_path: Path) -> None:
    runtime_config_path = tmp_path / 'runtime_config.json'
    ui_prefs_path = tmp_path / 'ui_prefs.json'
    session_meta_path = tmp_path / 'session_meta.json'
    ConfigService().save(
        runtime_config_path,
        RuntimeConfig(rt_mode='jointPosition', preferred_link='wifi', requires_single_control_source=False),
    )
    service = RuntimePersistenceService(
        config_service=ConfigService(),
        runtime_config_path=runtime_config_path,
        ui_prefs_path=ui_prefs_path,
        session_meta_path=session_meta_path,
        profile_service=ClinicalConfigService(),
    )

    config = service.load_initial_config()

    assert config.rt_mode == 'cartesianImpedance'
    assert config.preferred_link == 'wired_direct'
    assert config.requires_single_control_source is True
    persisted = RuntimeConfig.from_dict(json.loads(runtime_config_path.read_text(encoding='utf-8')))
    assert persisted.rt_mode == 'cartesianImpedance'
    assert persisted.preferred_link == 'wired_direct'
    assert persisted.requires_single_control_source is True


def test_runtime_persistence_reload_clamps_drifted_config_before_return(tmp_path: Path) -> None:
    runtime_config_path = tmp_path / 'runtime_config.json'
    ui_prefs_path = tmp_path / 'ui_prefs.json'
    session_meta_path = tmp_path / 'session_meta.json'
    ConfigService().save(
        runtime_config_path,
        RuntimeConfig(rt_mode='jointPosition', preferred_link='wifi', requires_single_control_source=False),
    )
    service = RuntimePersistenceService(
        config_service=ConfigService(),
        runtime_config_path=runtime_config_path,
        ui_prefs_path=ui_prefs_path,
        session_meta_path=session_meta_path,
        profile_service=ClinicalConfigService(),
    )

    config = service.reload_runtime_config()

    assert config.rt_mode == 'cartesianImpedance'
    assert config.preferred_link == 'wired_direct'
    assert config.requires_single_control_source is True


def test_app_controller_reload_persisted_config_keeps_current_config_when_file_is_corrupt(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    controller = AppController(tmp_path, backend)
    controller.update_config(RuntimeConfig(pressure_target=2.2))
    controller.runtime_config_path.write_text('{not-json}', encoding='utf-8')

    controller.reload_persisted_config()

    assert controller.config.pressure_target == 2.2
    repaired = RuntimeConfig.from_dict(json.loads(controller.runtime_config_path.read_text(encoding='utf-8')))
    assert repaired.rt_mode == 'cartesianImpedance'
    assert repaired.preferred_link == 'wired_direct'
    assert repaired.requires_single_control_source is True
