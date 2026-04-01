from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService
from spine_ultrasound_ui.services.ipc_protocol import protocol_schema


def test_protocol_schema_exposes_deployment_and_fault_contract_commands() -> None:
    schema = protocol_schema()
    assert "get_deployment_contract" in schema["commands"]
    assert "get_fault_injection_contract" in schema["commands"]
    assert "inject_fault" in schema["commands"]
    assert "clear_injected_faults" in schema["commands"]


def test_runtime_asset_service_collects_deployment_and_fault_contracts(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path)
    config = RuntimeConfig()
    snapshot = SdkRuntimeAssetService().refresh(backend, config)
    assert snapshot["deployment_contract"]["vendored_sdk_required"] is True
    assert snapshot["fault_injection_contract"]["enabled"] is True
    assert any(item["name"] == "pressure_stale" for item in snapshot["fault_injection_contract"]["catalog"])


def test_mock_backend_fault_injection_roundtrip() -> None:
    backend = MockBackend(Path("."))
    injected = backend.send_command("inject_fault", {"fault_name": "rt_jitter_high"})
    assert injected.ok, injected.message
    contract = backend.send_command("get_fault_injection_contract", {}).data
    assert "rt_jitter_high" in contract["active_injections"]
    release = backend.send_command("get_release_contract", {}).data
    assert "rt_jitter_high" in release["active_interlocks"] or "rt_jitter_high" in release.get("active_injections", [])
    cleared = backend.send_command("clear_injected_faults", {})
    assert cleared.ok, cleared.message
    contract = backend.send_command("get_fault_injection_contract", {}).data
    assert contract["active_injections"] == []
