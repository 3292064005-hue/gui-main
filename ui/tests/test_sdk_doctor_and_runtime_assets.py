from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.sdk_environment_doctor_service import SdkEnvironmentDoctorService
from spine_ultrasound_ui.services.sdk_runtime_asset_service import SdkRuntimeAssetService


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_sdk_environment_doctor_reports_local_snapshot(tmp_path: Path) -> None:
    service = SdkEnvironmentDoctorService(tmp_path)
    snapshot = service.inspect(RuntimeConfig())
    assert snapshot["summary_state"] in {"ready", "warning", "blocked"}
    assert snapshot["toolchain"]["python"]
    assert snapshot["sdk_paths"]["source"] in {"vendored", "env:XCORE_SDK_ROOT", "env:ROKAE_SDK_ROOT", "missing"}
    assert any(item["name"] == "remote/local IP 配置" for item in snapshot["checks"])
    assert any(item["name"] == "Python protobuf runtime" for item in snapshot["checks"])


def test_environment_doctor_reports_protocol_assets() -> None:
    snapshot = SdkEnvironmentDoctorService(Path('.')).inspect(RuntimeConfig())
    names = {item['name'] for item in snapshot['checks']}
    assert 'Protocol proto source' in names
    assert 'Python pb2 asset' in names
    assert 'C++ wire codec header' in names
    assert 'C++ wire codec source' in names
    assert 'Protocol sync gate script' in names


def test_sdk_runtime_assets_include_alignment_model_and_doctor(tmp_path: Path) -> None:
    _app()
    backend = MockBackend(tmp_path)
    service = SdkRuntimeAssetService()
    snapshot = service.refresh(backend, RuntimeConfig())
    assert snapshot["runtime_alignment"]["sdk_family"] == "ROKAE xCore SDK (C++)"
    assert snapshot["xmate_model_summary"]["robot_model"] == "xmate3"
    assert "registers" in snapshot["register_snapshot"]
    assert snapshot["runtime_config_snapshot"]["axis_count"] == 6
    assert snapshot["environment_doctor"]["summary_state"] in {"ready", "warning", "blocked"}


def test_environment_doctor_reports_runtime_version_policy_checks() -> None:
    snapshot = SdkEnvironmentDoctorService(Path('.')).inspect(RuntimeConfig())
    checks = {item['name']: item for item in snapshot['checks']}
    assert 'Ubuntu 22.04 基线' in checks
    assert 'PySide6' in checks
    assert 'Python protobuf runtime' in checks
    assert '>=3.20.3, <8' in checks['Python protobuf runtime']['detail']



def test_runtime_readiness_manifest_downgrades_top_level_state_when_doctor_blocked(monkeypatch) -> None:
    from spine_ultrasound_ui.services.runtime_readiness_manifest_service import RuntimeReadinessManifestService

    class _ModeDecision:
        requires_live_sdk = False

        def to_dict(self):
            return {'mode': 'mock', 'requires_live_sdk': False}

    monkeypatch.setattr(
        'spine_ultrasound_ui.services.runtime_readiness_manifest_service.SdkEnvironmentDoctorService.inspect',
        lambda self, config: {'summary_state': 'blocked', 'blockers': [{'name': 'TLS runtime 目录', 'detail': 'configs/tls/runtime'}], 'warnings': []},
    )
    monkeypatch.setattr(
        'spine_ultrasound_ui.services.runtime_readiness_manifest_service.DeploymentProfileService.build_snapshot',
        lambda self, config: {'name': 'dev', 'requires_hil_gate': False},
    )
    monkeypatch.setattr(
        'spine_ultrasound_ui.services.runtime_readiness_manifest_service.resolve_runtime_mode',
        lambda explicit_mode, surface, config, env: _ModeDecision(),
    )
    payload = RuntimeReadinessManifestService(Path('.')).build(config=RuntimeConfig(), surface='desktop')
    assert payload['summary_state'] == 'warning'
    assert payload['verification']['live_runtime_ready'] is False
    assert payload['verification']['verification_boundary'] == 'environment_blocked'
