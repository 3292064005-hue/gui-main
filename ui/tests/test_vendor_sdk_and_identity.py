from __future__ import annotations

import os
from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.robot_identity_service import RobotIdentityService
from spine_ultrasound_ui.services.sdk_vendor_locator import SdkVendorLocator


def test_vendor_sdk_locator_prefers_repo_copy() -> None:
    layout = SdkVendorLocator(Path(__file__).resolve().parents[1]).locate()
    assert layout.source in {"vendored", "env:XCORE_SDK_ROOT", "env:ROKAE_SDK_ROOT"}
    assert layout.found is True
    assert layout.include_dir and layout.include_dir.exists()
    assert layout.static_lib and layout.static_lib.exists()


def test_robot_identity_service_resolves_xmate3() -> None:
    identity = RobotIdentityService().resolve("xmate3", "xMateRobot", 6)
    assert identity.robot_model == "xmate3"
    assert identity.axis_count == 6
    assert len(identity.official_dh_parameters) == 6
    assert identity.cartesian_impedance_limits[0] == 1500.0


def test_clinical_config_report_blocks_official_limit_violations() -> None:
    config = RuntimeConfig(cartesian_impedance=[2200.0, 2200.0, 1400.0, 45.0, 45.0, 35.0])
    report = ClinicalConfigService().build_report(config)
    assert report["summary_state"] == "blocked"
    names = {item["name"] for item in report["blockers"]}
    assert "笛卡尔阻抗官方上限" in names


def _make_sdk_layout(root: Path) -> Path:
    sdk_root = root / "robot"
    (sdk_root / "include").mkdir(parents=True, exist_ok=True)
    (sdk_root / "external").mkdir(parents=True, exist_ok=True)
    lib_dir = sdk_root / "lib" / "Linux" / "cpp" / "x86_64"
    lib_dir.mkdir(parents=True, exist_ok=True)
    (lib_dir / "libxCoreSDK.a").write_bytes(b"stub")
    return sdk_root


def test_vendor_sdk_locator_honors_explicit_env_override(monkeypatch, tmp_path: Path) -> None:
    sdk_root = _make_sdk_layout(tmp_path)
    monkeypatch.setenv("XCORE_SDK_ROOT", str(sdk_root))
    layout = SdkVendorLocator(Path(__file__).resolve().parents[1]).locate()
    assert layout.source == "env:XCORE_SDK_ROOT"
    assert layout.sdk_root == sdk_root
    assert layout.static_lib and layout.static_lib.exists()
