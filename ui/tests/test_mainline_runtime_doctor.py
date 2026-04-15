from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mainline_runtime_doctor_service import MainlineRuntimeDoctorService
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_sdk_runtime_assets_include_governance_contracts_and_doctor(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    service = SdkRuntimeAssetService()
    snapshot = service.refresh(backend, RuntimeConfig())

    assert snapshot["control_governance_contract"]["single_control_source_required"] is True
    assert snapshot["controller_evidence"]["runtime_source"] == "mock_runtime_contract"
    assert snapshot["mainline_runtime_doctor"]["summary_state"] in {"ready", "warning", "blocked"}
    assert "session_freeze" in snapshot["mainline_runtime_doctor"]["sections"]


def test_mainline_runtime_doctor_recomputes_with_runtime_verdict_and_session(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    controller = AppController(tmp_path, backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.refresh_sdk_assets()

    doctor = controller.sdk_runtime_snapshot["mainline_runtime_doctor"]
    assert doctor["expected_rt_mode"] == "cartesianImpedance"
    assert doctor["final_verdict_accepted"] is True
    assert doctor["sections"]["clinical_mainline"]["summary_state"] == "ready"
    assert doctor["sections"]["session_freeze"]["summary_state"] == "warning"


def test_startup_blockers_ignore_mock_environment_only_blockers(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    controller = AppController(tmp_path, backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()

    blockers = controller.control_plane_reader.collect_startup_blockers()
    assert all(item.get("section") not in {"environment", "runtime_doctor"} for item in blockers)


def test_mainline_runtime_doctor_flags_rejected_runtime_verdict() -> None:
    service = MainlineRuntimeDoctorService()
    config = RuntimeConfig()
    result = service.inspect(
        config=config,
        sdk_runtime={
            "control_governance_contract": {"single_control_source_required": True, "session_binding_valid": True, "runtime_config_bound": True},
            "clinical_mainline_contract": {"clinical_mainline_mode": "cartesianImpedance"},
            "motion_contract": {"rt_mode": "cartesianImpedance", "nrt_contract": {}, "rt_contract": {}},
            "session_freeze": {"session_locked": True},
            "model_authority_contract": {"planner_supported": True, "xmate_model_supported": True},
            "runtime_alignment": {"sdk_available": True},
            "environment_doctor": {"summary_state": "ready", "summary_label": "ok", "detail": "ok"},
        },
        backend_link={"mode": "core", "control_plane": {"control_authority": {"summary_state": "ready"}}},
        model_report={"final_verdict": {"accepted": False, "reason": "force band violated"}},
        session_governance={"summary_state": "ready"},
    )
    assert result["summary_state"] == "blocked"
    assert any(item["name"] == "final_verdict_rejected" for item in result["blockers"])


def test_mainline_runtime_doctor_blocks_mock_runtime_when_profile_requires_live_sdk() -> None:
    service = MainlineRuntimeDoctorService()
    config = RuntimeConfig()
    result = service.inspect(
        config=config,
        sdk_runtime={
            'control_governance_contract': {'single_control_source_required': True, 'session_binding_valid': True, 'runtime_config_bound': True},
            'clinical_mainline_contract': {'clinical_mainline_mode': 'cartesianImpedance'},
            'motion_contract': {'rt_mode': 'cartesianImpedance', 'nrt_contract': {}, 'rt_contract': {}},
            'session_freeze': {'session_locked': True},
            'model_authority_contract': {'planner_supported': True, 'xmate_model_supported': True, 'authoritative_runtime': True},
            'runtime_alignment': {'sdk_available': False},
            'environment_doctor': {'summary_state': 'ready', 'summary_label': 'ok', 'detail': 'ok'},
            'profile_matrix_contract': {'name': 'research', 'requires_live_sdk': True},
            'vendor_boundary_contract': {'binding_mode': 'contract_only', 'single_control_source_required': True, 'control_source_exclusive': True, 'fixed_period_enforced': True},
            'hardware_lifecycle_contract': {'summary_state': 'warning', 'detail': 'contract shell', 'network_healthy': True, 'control_source_exclusive': True, 'lifecycle_state': 'contract_shell_ready'},
        },
        backend_link={'mode': 'mock', 'control_plane': {'control_authority': {'summary_state': 'ready'}}},
        model_report={'final_verdict': {'accepted': True}},
        session_governance={'summary_state': 'ready'},
    )
    assert result['summary_state'] == 'blocked'
    names = {item['name'] for item in result['blockers']}
    assert 'sdk_not_live' in names or 'vendor_boundary_not_live' in names


def test_mainline_runtime_doctor_blocks_rt_quality_budget_violations() -> None:
    service = MainlineRuntimeDoctorService()
    config = RuntimeConfig()
    result = service.inspect(
        config=config,
        sdk_runtime={
            "control_governance_contract": {"single_control_source_required": True, "session_binding_valid": True, "runtime_config_bound": True},
            "clinical_mainline_contract": {"clinical_mainline_mode": "cartesianImpedance"},
            "motion_contract": {"rt_mode": "cartesianImpedance", "nrt_contract": {}, "rt_contract": {}},
            "session_freeze": {"session_locked": True},
            "model_authority_contract": {"planner_supported": True, "xmate_model_supported": True},
            "runtime_alignment": {"sdk_available": True},
            "environment_doctor": {"summary_state": "ready", "summary_label": "ok", "detail": "ok"},
            "rt_kernel_contract": {
                "summary_state": "ready",
                "monitors": {"reference_limiter": True, "freshness_guard": True, "jitter_monitor": True, "network_guard": True},
                "fixed_period_enforced": True,
                "network_healthy": True,
                "overrun_count": 1,
                "current_period_ms": 1.0,
                "max_cycle_ms": 1.35,
                "last_wake_jitter_ms": 0.45,
                "jitter_budget_ms": 0.2,
                "rt_quality_gate_passed": False,
            },
        },
        backend_link={"mode": "core", "control_plane": {"control_authority": {"summary_state": "ready"}}},
        model_report={"final_verdict": {"accepted": True}},
        session_governance={"summary_state": "ready"},
    )
    names = {item["name"] for item in result["blockers"]}
    assert {"rt_cycle_overrun_detected", "rt_wake_jitter_budget_exceeded", "rt_cycle_budget_exceeded", "rt_quality_gate_failed"} <= names
