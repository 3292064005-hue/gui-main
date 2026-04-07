from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter
from spine_ultrasound_ui.services.runtime_verdict_kernel_service import RuntimeVerdictKernelService
from spine_ultrasound_ui.services.session_governance_service import SessionGovernanceService


class _FailingVerdictBackend:
    def get_final_verdict(self, plan, config):
        raise TimeoutError("runtime verdict timed out")


def test_headless_adapter_uses_explicit_session_product_surface() -> None:
    source = Path('spine_ultrasound_ui/services/headless_adapter.py').read_text(encoding='utf-8')
    assert '_bind_session_product_method' not in source
    assert 'setattr(HeadlessAdapter' not in source

    adapter = HeadlessAdapter(
        mode='mock',
        command_host='127.0.0.1',
        command_port=5656,
        telemetry_host='127.0.0.1',
        telemetry_port=5657,
    )
    assert callable(adapter.current_session)
    assert callable(adapter.current_report)


def test_runtime_verdict_unavailable_exposes_typed_runtime_error() -> None:
    payload = RuntimeVerdictKernelService().resolve(_FailingVerdictBackend(), None, RuntimeConfig())
    assert payload['verdict_kind'] == 'unavailable'
    assert payload['runtime_error']['error_type'] == 'transport_timeout'
    assert payload['runtime_error']['retryable'] is True


def test_session_governance_reports_artifact_read_errors(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True, exist_ok=True)
    (session_dir / 'export').mkdir(parents=True, exist_ok=True)
    (session_dir / 'derived' / 'events').mkdir(parents=True, exist_ok=True)
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps({'session_id': 'S1', 'artifact_registry': {}}), encoding='utf-8')
    (session_dir / 'export' / 'release_gate_decision.json').write_text('{broken', encoding='utf-8')

    payload = SessionGovernanceService().build(session_dir)
    assert payload['summary_state'] == 'warning'
    assert payload['artifact_errors']
    assert payload['artifact_errors'][0]['error_type'] in {'schema_mismatch', 'invalid_payload'}


def test_verify_mainline_runs_architecture_fitness_gate() -> None:
    script = Path("scripts/verify_mainline.sh").read_text(encoding="utf-8")
    assert "python scripts/check_architecture_fitness.py" in script


def test_sdk_robot_facade_exposes_controlled_ports_and_call_sites_use_them() -> None:
    header = Path('cpp_robot_core/include/robot_core/sdk_robot_facade.h').read_text(encoding='utf-8')
    for required in (
        'class LifecyclePort',
        'class QueryPort',
        'class NrtExecutionPort',
        'class RtControlPort',
        'class CollaborationPort',
        'LifecyclePort& lifecyclePort()',
        'QueryPort& queryPort()',
        'NrtExecutionPort& nrtExecutionPort()',
        'RtControlPort& rtControlPort()',
        'CollaborationPort& collaborationPort()',
    ):
        assert required in header

    assert 'nrtExecutionPort().' in Path('cpp_robot_core/src/nrt_motion_service.cpp').read_text(encoding='utf-8')
    assert 'rtControlPort().' in Path('cpp_robot_core/src/rt_motion_service.cpp').read_text(encoding='utf-8')
    assert 'collaborationPort().' in Path('cpp_robot_core/src/core_runtime_session_execution.cpp').read_text(encoding='utf-8')
    assert 'queryPort().' in Path('cpp_robot_core/src/core_runtime.cpp').read_text(encoding='utf-8')
    assert 'lifecyclePort().' in Path('cpp_robot_core/src/core_runtime.cpp').read_text(encoding='utf-8')


def test_runtime_lane_routes_rt_commands_to_rt_control_mutex() -> None:
    source = Path('cpp_robot_core/src/core_runtime.cpp').read_text(encoding='utf-8')
    for required in (
        '{"seek_contact", RuntimeLane::RtControl}',
        '{"start_scan", RuntimeLane::RtControl}',
        '{"pause_scan", RuntimeLane::RtControl}',
        '{"resume_scan", RuntimeLane::RtControl}',
        '{"safe_retreat", RuntimeLane::RtControl}',
        'if (lane == RuntimeLane::RtControl)',
        'std::lock_guard<std::mutex> lane_lock(rt_lane_mutex_)',
    ):
        assert required in source


def test_config_manager_supports_legacy_dotted_aliases_and_sections() -> None:
    from spine_ultrasound_ui.services.config_manager import ConfigManager

    manager = ConfigManager()
    original_remote = manager.get('remote_ip')
    original_local = manager.get('local_ip')
    try:
        manager.set('robot.remote_ip', '192.168.0.160', save=False)
        manager.set_section('robot', {'local_ip': '192.168.0.22'}, save=False)
        assert manager.get('remote_ip') == '192.168.0.160'
        assert manager.get('robot.remote_ip') == '192.168.0.160'
        assert manager.get('robot.local_ip') == '192.168.0.22'
        assert manager.get_section('robot')['remote_ip'] == '192.168.0.160'
        assert manager.get_section('robot')['local_ip'] == '192.168.0.22'
    finally:
        manager.set('remote_ip', original_remote, save=False)
        manager.set('local_ip', original_local, save=False)


def test_architecture_fitness_uses_relative_skip_rules_and_nonzero_scan_guard() -> None:
    script = Path("scripts/check_architecture_fitness.py").read_text(encoding="utf-8")
    assert '_relative_python_path' in script
    assert '_should_skip_python_file' in script
    assert 'scanned_python_files' in script
    assert 'Architecture fitness gate scanned zero Python files' in script
    assert 'any(part in ignored_roots for part in path.parts)' not in script
    assert '_MAX_MAINLINE_FILE_LINES' in script
