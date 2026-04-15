from __future__ import annotations

import json
import ast
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
        'class SdkRobotLifecyclePort',
        'class SdkRobotQueryPort',
        'class SdkRobotNrtExecutionPort',
        'class SdkRobotRtControlPort',
        'class SdkRobotCollaborationPort',
        'using LifecyclePort = SdkRobotLifecyclePort;',
        'using QueryPort = SdkRobotQueryPort;',
        'using NrtExecutionPort = SdkRobotNrtExecutionPort;',
        'using RtControlPort = SdkRobotRtControlPort;',
        'using CollaborationPort = SdkRobotCollaborationPort;',
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
    source = Path('cpp_robot_core/src/core_runtime_dispatcher.cpp').read_text(encoding='utf-8')
    for required in (
        'runtimeLaneForCommand',
        'findRuntimeCommandGuardContract',
        'if (lane == CoreRuntime::RuntimeLane::RtControl)',
        'return dispatch_with_contract(owner_.rt_lane_mutex_)',
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




def test_runtime_command_catalog_is_manifest_backed_and_generated_cpp_registry_exists() -> None:
    source = Path('spine_ultrasound_ui/services/runtime_command_catalog.py').read_text(encoding='utf-8')
    assert 'runtime_command_manifest.json' in source
    assert 'json.loads' in source
    generated = Path('cpp_robot_core/include/robot_core/generated_command_manifest.inc').read_text(encoding='utf-8')
    assert 'Generated from schemas/runtime_command_manifest.json' in generated


def test_api_server_uses_app_state_composition_root_without_module_singletons() -> None:
    source = Path('spine_ultrasound_ui/api_server.py').read_text(encoding='utf-8')
    assert 'fastapi_app.state.runtime_container = resolved_container' in source
    assert '_runtime_container =' not in source
    assert 'adapter: HeadlessAdapter | None = None' not in source


def test_main_window_pixmap_receivers_are_explicit_slots() -> None:
    source = Path('spine_ultrasound_ui/main_window.py').read_text(encoding='utf-8')
    assert '@Slot(object)\n    def _update_camera_pixmap' in source
    assert '@Slot(object)\n    def _update_ultrasound_pixmap' in source
    assert '@Slot(object)\n    def _update_reconstruction_pixmap' in source




def _contains_archive_import(path: str) -> bool:
    """Return whether a module imports historical archive tests directly.

    The mainline top-level surface must not import the archived compatibility
    tree directly. This helper checks actual import nodes instead of grepping
    for a brittle literal path string.
    """
    tree = ast.parse(Path(path).read_text(encoding='utf-8'))
    archive_prefix = '.'.join(('tests', 'archive'))
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            module = node.module or ''
            if module == archive_prefix or module.startswith(f'{archive_prefix}.'):
                return True
    return False

def test_rt_state_store_flushes_recording_after_unlock() -> None:
    source = Path('cpp_robot_core/src/runtime_state_store.cpp').read_text(encoding='utf-8')
    assert 'PendingRecordBundle record_bundle{};' in source
    assert 'record_bundle = buildRecordBundleLocked();' in source
    assert 'flushRecordBundle(record_bundle);' in source


def test_stable_control_ownership_surface_no_longer_imports_archive_wrapper() -> None:
    assert not _contains_archive_import('tests/test_control_ownership.py')


def test_stable_runtime_verdict_surface_no_longer_imports_archive_wrapper() -> None:
    assert not _contains_archive_import('tests/test_runtime_verdict.py')

def test_app_controller_runtime_mixin_uses_queued_qt_connections() -> None:
    source = Path('spine_ultrasound_ui/core/app_controller_runtime_mixin.py').read_text(encoding='utf-8')
    assert 'telemetry_received.connect(self._handle_telemetry, Qt.QueuedConnection)' in source
    assert 'log_generated.connect(self._forward_log, Qt.QueuedConnection)' in source
    assert 'camera_pixmap_ready.connect(self._on_camera_pixmap, Qt.QueuedConnection)' in source
    assert 'ultrasound_pixmap_ready.connect(self._on_ultrasound_pixmap, Qt.QueuedConnection)' in source


def test_legacy_archive_wrappers_are_removed_from_top_level_tests_surface() -> None:
    for rel_path in (
        'tests/test_api_contract.py',
        'tests/test_api_security.py',
        'tests/test_control_plane.py',
        'tests/test_headless_runtime.py',
        'tests/test_profile_policy.py',
        'tests/test_release_gate.py',
        'tests/test_replay_determinism.py',
        'tests/test_spawned_core_integration.py',
    ):
        assert not Path(rel_path).exists()


def test_architecture_gate_enforces_removed_archive_wrappers() -> None:
    source = Path('scripts/check_architecture_fitness.py').read_text(encoding='utf-8')
    assert 'LEGACY_ARCHIVE_WRAPPER_BASENAMES' in source
    assert 'Legacy archive wrapper must not exist in top-level tests surface' in source
    assert 'run_pytest_mainline must not hardcode legacy archive wrapper ignores once wrappers are removed' in source


def test_run_pytest_mainline_only_opt_in_adds_archive_compat_suite() -> None:
    source = Path('scripts/run_pytest_mainline.py').read_text(encoding='utf-8')
    assert 'ARCHIVE_COMPAT_DIR' in source
    assert '--include-archive-compat' in source
    assert "Path('tests') / 'archive'" in source
    assert 'ACTIVE_GATE_ARCHIVE_WRAPPERS' not in source


def test_robot_core_verdict_service_fail_hard_contract_matches_api_bridge() -> None:
    source = Path('spine_ultrasound_ui/services/robot_core_verdict_service.py').read_text(encoding='utf-8')
    assert '_raise_if_reply_failed' in source
    assert 'Failed replies never' in source
    assert 'self._raise_if_reply_failed(reply, command="query_final_verdict")' in source
    assert 'self._raise_if_reply_failed(reply, command="validate_scan_plan")' in source


def test_verify_cpp_build_evidence_tracks_current_core_runtime_sources() -> None:
    source = Path('scripts/verify_cpp_build_evidence.py').read_text(encoding='utf-8')
    assert 'cpp_robot_core/src/command_registry.cpp' in source
    assert 'cpp_robot_core/src/core_runtime.cpp' in source
    assert 'cpp_robot_core/src/runtime_state_store.cpp' in source


def test_verify_and_acceptance_generate_runtime_command_artifacts_before_sync_gate() -> None:
    verify_script = Path('scripts/verify_mainline.sh').read_text(encoding='utf-8')
    acceptance_script = Path('scripts/final_acceptance_audit.sh').read_text(encoding='utf-8')
    assert 'scripts/generate_runtime_command_artifacts.py' in verify_script
    assert 'scripts/generate_runtime_command_artifacts.py' in acceptance_script


def test_verify_mainline_runs_rt_purity_and_quality_gates() -> None:
    script = Path("scripts/verify_mainline.sh").read_text(encoding="utf-8")
    assert "scripts/check_rt_purity_gate.py" in script
    assert "scripts/check_rt_quality_gate.py" in script


def test_repo_payload_declares_codeowners() -> None:
    codeowners = Path('.github/CODEOWNERS')
    assert codeowners.exists()
    assert '@runtime-architecture' in codeowners.read_text(encoding='utf-8')


def test_runtime_command_contracts_generate_cpp_typed_request_response_and_guard_artifacts() -> None:
    generated = Path('cpp_robot_core/include/robot_core/generated_runtime_command_contracts.inc').read_text(encoding='utf-8')
    header = Path('cpp_robot_core/include/robot_core/runtime_command_contracts.h').read_text(encoding='utf-8')
    source = Path('cpp_robot_core/src/runtime_command_contracts.cpp').read_text(encoding='utf-8')
    dispatcher = Path('cpp_robot_core/src/core_runtime_dispatcher.cpp').read_text(encoding='utf-8')
    assert 'RuntimeCommandRequestContract' in header
    assert 'RuntimeCommandResponseContract' in header
    assert 'RuntimeCommandGuardContract' in header
    assert 'validateAndParseRuntimeCommandPayload' in source
    assert 'generated_runtime_command_contracts.inc' in source
    assert 'RuntimeCommandResponseContract' in generated
    assert 'RuntimeCommandGuardContract' in generated
    assert 'buildRuntimeCommandInvocation(line, &invocation, &payload_error)' in dispatcher
    assert 'dispatchTypedCommand(invocation)' in dispatcher


def test_runtime_command_contracts_generate_cpp_typed_request_family() -> None:
    request_types = Path('cpp_robot_core/include/robot_core/generated_runtime_command_request_types.h').read_text(encoding='utf-8')
    request_parsers = Path('cpp_robot_core/include/robot_core/generated_runtime_command_request_parsers.inc').read_text(encoding='utf-8')
    dispatcher = Path('cpp_robot_core/src/core_runtime_dispatcher.cpp').read_text(encoding='utf-8')
    assert 'using RuntimeTypedRequestVariant = std::variant<' in request_types
    assert 'ConnectRobotRequest' in request_types
    assert 'LockSessionRequest' in request_types
    assert 'ValidateScanPlanRequest' in request_types
    assert 'if (command == "connect_robot")' in request_parsers
    assert 'if (command == "lock_session")' in request_parsers
    assert 'buildTypedRuntimeCommandRequest' in dispatcher or 'buildTypedRuntimeCommandRequest' in Path('cpp_robot_core/src/runtime_command_contracts.cpp').read_text(encoding='utf-8')


def test_runtime_command_contracts_generate_cpp_typed_handler_adapter_family() -> None:
    decls = Path('cpp_robot_core/include/robot_core/generated_runtime_command_typed_handler_decls.inc').read_text(encoding='utf-8')
    adapters = Path('cpp_robot_core/include/robot_core/generated_runtime_command_typed_handlers.inc').read_text(encoding='utf-8')
    script = Path('scripts/check_architecture_fitness.py').read_text(encoding='utf-8')
    assert 'generated_runtime_command_typed_handlers.inc' in script
    assert 'generated_runtime_command_typed_handler_decls.inc' in script
    for required in ('handleTypedCommand<ConnectRobotRequest>', 'handleTypedCommand<LockSessionRequest>', 'handleTypedCommand<ValidateScanPlanRequest>'):
        assert required in adapters
    for required in ('handleConnectRobotTyped', 'handleLockSessionTyped', 'handleValidateScanPlanTyped'):
        assert required in decls
        assert required in adapters
