from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.mainline_runtime_doctor_service import MainlineRuntimeDoctorService
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.robot_family_registry_service import RobotFamilyRegistryService
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService


def test_robot_family_registry_resolves_collaborative_7_axis() -> None:
    descriptor = RobotFamilyRegistryService().resolve(robot_model="xmate_er7_pro", sdk_robot_class="xMateErProRobot", axis_count=7)
    assert descriptor.family_key == "xmate_7_collaborative"
    assert descriptor.axis_count == 7
    assert descriptor.clinical_rt_mode == "cartesianImpedance"
    assert "scan_follow" in descriptor.allowed_rt_phases


def test_deployment_profile_service_supports_lab_profile() -> None:
    profile = DeploymentProfileService({"SPINE_LAB_MODE": "1"}).build_snapshot(RuntimeConfig())
    assert profile["name"] == "lab"
    assert profile["allows_lab_port"] is True
    assert profile["requires_strict_control_authority"] is True


def test_runtime_assets_include_robot_family_and_vendor_boundary(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path)
    snapshot = SdkRuntimeAssetService().refresh(backend, RuntimeConfig())
    assert snapshot["robot_family_contract"]["descriptor"]["family_key"] == "xmate_6_collaborative"
    assert snapshot["vendor_boundary_contract"]["binding_mode"] == "contract_only"
    assert "lab" in snapshot["profile_matrix_contract"]["profile_matrix"]


def test_runtime_doctor_sections_include_family_vendor_and_profile() -> None:
    result = MainlineRuntimeDoctorService().inspect(
        config=RuntimeConfig(),
        sdk_runtime={
            "control_governance_contract": {"single_control_source_required": True, "session_binding_valid": True, "runtime_config_bound": True},
            "clinical_mainline_contract": {"clinical_mainline_mode": "cartesianImpedance"},
            "motion_contract": {"rt_mode": "cartesianImpedance", "nrt_contract": {}, "rt_contract": {}},
            "session_freeze": {"session_locked": True},
            "model_authority_contract": {"planner_supported": True, "xmate_model_supported": True},
            "runtime_alignment": {"sdk_available": True, "source": "xcore"},
            "environment_doctor": {"summary_state": "ready", "detail": "ok"},
            "robot_family_contract": {"family_label": "xMate collaborative 6-axis", "clinical_rt_mode": "cartesianImpedance", "requires_single_control_source": True},
            "vendor_boundary_contract": {"summary_label": "Vendor Boundary", "detail": "ok", "binding_mode": "contract_only", "control_source_exclusive": True, "fixed_period_enforced": True, "single_control_source_required": True},
            "profile_matrix_contract": {"name": "research", "description": "research", "requires_hil_gate": True, "allows_write_commands": True},
        },
        backend_link={"mode": "core", "control_plane": {"control_authority": {"summary_state": "ready"}}},
        model_report={"final_verdict": {"accepted": True}},
        session_governance={"summary_state": "ready"},
    )
    assert "robot_family" in result["sections"]
    assert "vendor_boundary" in result["sections"]
    assert "deployment_profile" in result["sections"]
