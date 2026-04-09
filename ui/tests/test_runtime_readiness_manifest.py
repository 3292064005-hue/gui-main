from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.runtime_readiness_manifest_service import RuntimeReadinessManifestService


def _write(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text('', encoding='utf-8')


def test_runtime_readiness_manifest_separates_static_and_live_verification(tmp_path: Path) -> None:
    for rel in (
        'scripts/check_architecture_fitness.py',
        'scripts/check_protocol_sync.py',
        'scripts/check_repository_gates.py',
        'scripts/check_canonical_imports.py',
        'cpp_robot_core/proto/ipc_messages.proto',
        'spine_ultrasound_ui/services/ipc_messages_pb2.py',
        'cpp_robot_core/include/ipc_messages.pb.h',
        'cpp_robot_core/src/ipc_messages.pb.cpp',
    ):
        _write(tmp_path / rel)
    manifest = RuntimeReadinessManifestService(tmp_path).build(config=RuntimeConfig(), surface='desktop', env={'SPINE_PROFILE': 'research'})
    assert manifest['schema_version'] == 'runtime.environment_readiness_manifest.v1'
    assert manifest['verification']['static_contract_ready'] is True
    assert manifest['verification']['sandbox_validation_possible'] is True
    assert manifest['verification']['live_runtime_verified'] is False
    assert manifest['verification']['live_runtime_ready'] is False
    assert manifest['summary_state'] == 'warning'
    assert manifest['verification']['verification_boundary'] == 'environment_blocked'


def test_runtime_readiness_manifest_reports_mode_and_profile_without_env_leak(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv('SPINE_DEPLOYMENT_PROFILE', 'clinical')
    manifest = RuntimeReadinessManifestService(tmp_path).build(config=RuntimeConfig(), surface='headless', env={})
    assert manifest['surface'] == 'headless'
    assert manifest['deployment_profile']['name'] == 'dev'
    assert manifest['runtime_mode_decision']['surface'] == 'headless'


def test_runtime_readiness_manifest_reports_explicit_profile_from_supplied_env(tmp_path: Path) -> None:
    manifest = RuntimeReadinessManifestService(
        tmp_path,
    ).build(config=RuntimeConfig(), surface='headless', env={'SPINE_PROFILE': 'review'})
    assert manifest['deployment_profile']['name'] == 'review'
    assert manifest['runtime_mode_decision']['profile_name'] == 'review'
