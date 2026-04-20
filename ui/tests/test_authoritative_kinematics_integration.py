from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_session_runtime_runs_authoritative_plan_precheck_before_freeze() -> None:
    source = _read("cpp_robot_core/src/session_runtime.cpp")
    assert "validatePlanAuthoritativeKinematics(plan)" in source
    assert "authoritative_precheck.available && !authoritative_precheck.passed" in source


def test_sdk_facade_model_precheck_uses_official_xmate_model_methods() -> None:
    source = _read("cpp_robot_core/src/sdk_robot_facade_model.cpp")
    assert "robot_->model()" in source
    assert ".getJointPos(" in source
    assert ".jacobian(" in source
    assert ".getTorque(" in source


def test_model_authority_contract_reports_live_binding_requirement_for_authoritative_precheck() -> None:
    source = _read("cpp_robot_core/src/model_authority.cpp")
    assert "sdk.liveBindingEstablished()" in source
