from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_mainline_runtime_doctor_uses_verdict_unavailable_not_legacy_python_fallback() -> None:
    text = _read("spine_ultrasound_ui/services/mainline_runtime_doctor_service.py")
    assert "python_advisory_fallback" not in text
    assert "verdict_unavailable" in text


def test_backend_error_mapper_is_used_by_core_and_api_backends() -> None:
    core = _read("spine_ultrasound_ui/services/robot_core_client.py")
    api = _read("spine_ultrasound_ui/services/api_bridge_backend.py")
    assert "BackendErrorMapper" in core
    assert "BackendErrorMapper" in api
