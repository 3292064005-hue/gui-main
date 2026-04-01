from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mainline_runtime_doctor_service import MainlineRuntimeDoctorService
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService


def test_runtime_assets_include_safety_recovery_contract(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path)
    snapshot = SdkRuntimeAssetService().refresh(backend, RuntimeConfig())
    contract = snapshot["safety_recovery_contract"]
    assert contract["runtime_guard_enforced"] is True
    assert contract["operator_ack_required_for_fault_latched"] is True
    assert "L2_auto_recovery" in contract["policy_layers"]


def test_runtime_doctor_warns_when_authoritative_runtime_not_live_but_profile_requires_it() -> None:
    result = MainlineRuntimeDoctorService().inspect(
        config=RuntimeConfig(),
        sdk_runtime={
            "control_governance_contract": {"single_control_source_required": True, "session_binding_valid": True, "runtime_config_bound": True},
            "clinical_mainline_contract": {"clinical_mainline_mode": "cartesianImpedance"},
            "motion_contract": {"rt_mode": "cartesianImpedance", "nrt_contract": {}, "rt_contract": {}},
            "session_freeze": {"session_locked": True},
            "model_authority_contract": {"planner_supported": True, "xmate_model_supported": True, "authoritative_runtime": False},
            "runtime_alignment": {"sdk_available": True},
            "environment_doctor": {"summary_state": "ready", "detail": "ok"},
            "profile_matrix_contract": {"name": "clinical", "requires_hil_gate": True, "allows_write_commands": True},
            "safety_recovery_contract": {"summary_state": "ready", "runtime_guard_enforced": True},
        },
        backend_link={"mode": "core", "control_plane": {"control_authority": {"summary_state": "ready"}}},
        model_report={"final_verdict": {"accepted": True}},
        session_governance={"summary_state": "ready"},
    )
    assert any(item["name"] == "authoritative_runtime_not_live" for item in result["warnings"])


def test_runtime_doctor_blocks_when_safety_recovery_runtime_guard_missing() -> None:
    result = MainlineRuntimeDoctorService().inspect(
        config=RuntimeConfig(),
        sdk_runtime={
            "control_governance_contract": {"single_control_source_required": True, "session_binding_valid": True, "runtime_config_bound": True},
            "clinical_mainline_contract": {"clinical_mainline_mode": "cartesianImpedance"},
            "motion_contract": {"rt_mode": "cartesianImpedance", "nrt_contract": {}, "rt_contract": {}},
            "session_freeze": {"session_locked": True},
            "model_authority_contract": {"planner_supported": True, "xmate_model_supported": True, "authoritative_runtime": True},
            "runtime_alignment": {"sdk_available": True},
            "environment_doctor": {"summary_state": "ready", "detail": "ok"},
            "profile_matrix_contract": {"name": "research", "requires_hil_gate": False, "allows_write_commands": True},
            "safety_recovery_contract": {"summary_state": "ready", "runtime_guard_enforced": False, "detail": "runtime guards missing"},
        },
        backend_link={"mode": "core", "control_plane": {"control_authority": {"summary_state": "ready"}}},
        model_report={"final_verdict": {"accepted": True}},
        session_governance={"summary_state": "ready"},
    )
    assert any(item["name"] == "runtime_guard_missing" for item in result["blockers"])
