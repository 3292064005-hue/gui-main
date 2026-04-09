from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter
from spine_ultrasound_ui.services.runtime_verdict_kernel_service import RuntimeVerdictKernelService
from spine_ultrasound_ui.services.session_governance_service import SessionGovernanceService


class _FailingVerdictBackend:
    def resolve_final_verdict(self, plan, config, *, read_only: bool):
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
        'commandCapabilityClaim',
        'capability_claim == "rt_motion_write"',
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


class _SnapshotOnlyVerdictBackend:
    def __init__(self) -> None:
        self.snapshot_calls = 0
        self.compile_calls = 0

    def resolve_final_verdict(self, plan, config, *, read_only: bool):
        if read_only:
            self.snapshot_calls += 1
            return {
                'summary_state': 'ready',
                'authority_source': 'cpp_robot_core',
                'verdict_kind': 'final',
                'detail': 'snapshot',
                'final_verdict': {'accepted': True, 'source': 'cpp_robot_core'},
            }
        self.compile_calls += 1
        return {}


def test_runtime_verdict_prefers_snapshot_query_until_explicit_refresh() -> None:
    backend = _SnapshotOnlyVerdictBackend()
    service = RuntimeVerdictKernelService()
    payload = service.resolve(backend, None, RuntimeConfig(), refresh_runtime_verdict=False)
    assert payload['verdict_kind'] == 'final'
    assert backend.snapshot_calls == 1
    assert backend.compile_calls == 0

    service.resolve(backend, None, RuntimeConfig(), refresh_runtime_verdict=True)
    assert backend.compile_calls == 1


def test_session_governance_caches_unchanged_sessions(tmp_path: Path) -> None:
    session_dir = tmp_path / 'session'
    (session_dir / 'meta').mkdir(parents=True, exist_ok=True)
    (session_dir / 'export').mkdir(parents=True, exist_ok=True)
    (session_dir / 'derived' / 'events').mkdir(parents=True, exist_ok=True)
    (session_dir / 'meta' / 'manifest.json').write_text(json.dumps({'session_id': 'S1', 'artifact_registry': {}}), encoding='utf-8')

    service = SessionGovernanceService()
    first = service.build(session_dir)
    sentinel = dict(first)
    service._cached_payload = sentinel
    second = service.build(session_dir)
    assert second == sentinel


def test_emit_status_does_not_force_governance_refresh(tmp_path: Path) -> None:
    from PySide6.QtWidgets import QApplication
    from spine_ultrasound_ui.core.app_controller import AppController
    from spine_ultrasound_ui.services.mock_backend import MockBackend

    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    controller = AppController(tmp_path, MockBackend(tmp_path / 'backend'))
    payloads: list[dict] = []
    controller.status_updated.connect(payloads.append)

    def _forbidden(*args, **kwargs):
        raise AssertionError('_emit_status unexpectedly triggered refresh_governance')

    controller.runtime_bridge.refresh_governance = _forbidden
    controller._emit_status()
    assert payloads
    controller.shutdown()


def test_runtime_verdict_kernel_requires_canonical_backend_api() -> None:
    class _LegacyOnlyBackend:
        def get_final_verdict(self, plan, config):
            return {"verdict_kind": "final"}

    payload = RuntimeVerdictKernelService().resolve(_LegacyOnlyBackend(), None, RuntimeConfig())
    assert payload['verdict_kind'] == 'unavailable'
    assert payload['runtime_error']['error_type'] == 'runtime_unavailable'


def test_session_service_declares_frozen_public_api_surface() -> None:
    source = Path('spine_ultrasound_ui/core/session_service.py').read_text(encoding='utf-8')
    assert 'SESSION_SERVICE_PUBLIC_API' in source
    assert 'new feature work must land in delegated collaborators' in source


def test_api_bridge_backend_uses_split_lease_and_verdict_services() -> None:
    source = Path('spine_ultrasound_ui/services/api_bridge_backend.py').read_text(encoding='utf-8')
    assert 'ApiBridgeLeaseService' in source
    assert 'ApiBridgeVerdictService' in source
    assert 'def _lease_allowed(self) -> bool:' in source
    assert 'if self._lease_allowed():' in source
    assert 'effective_include_lease = include_lease and self._lease_allowed()' in source
    assert 'self._lease_service.ensure_control_lease(' in source
    assert 'self._verdict_service.resolve_final_verdict(' in source

    verdict_source = Path('spine_ultrasound_ui/services/api_bridge_verdict_service.py').read_text(encoding='utf-8')
    assert '_raise_if_reply_failed' in verdict_source
    assert 'Failed read/compile attempts do not fall back to cached verdicts' in verdict_source


def test_app_controller_runtime_mixin_uses_queued_qt_connections() -> None:
    source = Path('spine_ultrasound_ui/core/app_controller_runtime_mixin.py').read_text(encoding='utf-8')
    assert 'telemetry_received.connect(self._handle_telemetry, Qt.QueuedConnection)' in source
    assert 'log_generated.connect(self._forward_log, Qt.QueuedConnection)' in source
    assert 'camera_pixmap_ready.connect(self._on_camera_pixmap, Qt.QueuedConnection)' in source
    assert 'ultrasound_pixmap_ready.connect(self._on_ultrasound_pixmap, Qt.QueuedConnection)' in source
