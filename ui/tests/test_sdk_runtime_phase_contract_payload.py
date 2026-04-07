from __future__ import annotations

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mock_runtime.contract_surface import MockRuntimeContractSurfaceMixin


class Surface(MockRuntimeContractSurfaceMixin):
    def __init__(self) -> None:
        self.config = RuntimeConfig()


def test_mock_sdk_runtime_payload_exposes_rt_phase_contract() -> None:
    surface = Surface()
    payload = surface._sdk_runtime_config_payload()
    contract = payload.get("rt_phase_contract")
    assert isinstance(contract, dict)
    assert set(contract.keys()) == {"common", "seek_contact", "scan_follow", "pause_hold", "controlled_retract"}
    assert contract["scan_follow"]["scan_pose_trim_gain"] == surface.config.scan_pose_trim_gain
