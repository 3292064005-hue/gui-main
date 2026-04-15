#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
HEADLESS_ADAPTER = ROOT / 'spine_ultrasound_ui' / 'services' / 'headless_adapter.py'
CORE_RUNTIME_HEADER = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'core_runtime.h'
CORE_RUNTIME_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'core_runtime.cpp'
CORE_RUNTIME_DISPATCHER_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'core_runtime_dispatcher.cpp'
SDK_FACADE_HEADER = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'sdk_robot_facade.h'
NRT_MOTION_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'nrt_motion_service.cpp'
RT_MOTION_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'rt_motion_service.cpp'
SESSION_EXECUTION_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'core_runtime_session_execution.cpp'
APP_CONTROLLER_RUNTIME_MIXIN = ROOT / 'spine_ultrasound_ui' / 'core' / 'app_controller_runtime_mixin.py'
APP_RUNTIME_BRIDGE = ROOT / 'spine_ultrasound_ui' / 'core' / 'app_runtime_bridge.py'
CONFIG_MANAGER = ROOT / 'spine_ultrasound_ui' / 'services' / 'config_manager.py'
MAIN_WINDOW_LAYOUT = ROOT / 'spine_ultrasound_ui' / 'views' / 'main_window_layout.py'
RUNTIME_READINESS_SERVICE = ROOT / 'spine_ultrasound_ui' / 'services' / 'runtime_readiness_manifest_service.py'
RUNTIME_COMMAND_CATALOG = ROOT / 'spine_ultrasound_ui' / 'services' / 'runtime_command_catalog.py'
GENERATED_COMMAND_MANIFEST = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'generated_command_manifest.inc'
RUNTIME_COMMAND_CONTRACTS_HEADER = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'runtime_command_contracts.h'
RUNTIME_COMMAND_CONTRACTS_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'runtime_command_contracts.cpp'
GENERATED_RUNTIME_COMMAND_CONTRACTS = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'generated_runtime_command_contracts.inc'
GENERATED_RUNTIME_TYPED_HANDLER_DECLS = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'generated_runtime_command_typed_handler_decls.inc'
GENERATED_RUNTIME_TYPED_HANDLER_ADAPTERS = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'generated_runtime_command_typed_handlers.inc'
API_SERVER = ROOT / 'spine_ultrasound_ui' / 'api_server.py'
MAIN_WINDOW = ROOT / 'spine_ultrasound_ui' / 'main_window.py'
CONTROL_OWNERSHIP_TEST = ROOT / 'tests' / 'test_control_ownership.py'
RUNTIME_VERDICT_TEST = ROOT / 'tests' / 'test_runtime_verdict.py'
LEGACY_ARCHIVE_WRAPPER_BASENAMES = (
    'test_api_contract.py',
    'test_api_security.py',
    'test_control_plane.py',
    'test_headless_runtime.py',
    'test_profile_policy.py',
    'test_release_gate.py',
    'test_replay_determinism.py',
    'test_spawned_core_integration.py',
)
IGNORED_TOP_LEVEL_DIRS = frozenset({'.git', '.pytest_cache', 'archive', 'repo'})
_MAX_MAINLINE_FILE_LINES = {
    'spine_ultrasound_ui/services/api_bridge_lease_service.py': 220,
    'spine_ultrasound_ui/services/api_bridge_verdict_service.py': 220,
    'cpp_robot_core/src/sdk_robot_facade.cpp': 300,
    'cpp_robot_core/src/sdk_robot_facade_lifecycle.cpp': 420,
    'cpp_robot_core/src/sdk_robot_facade_nrt.cpp': 420,
    'cpp_robot_core/src/sdk_robot_facade_rt.cpp': 760,
    'cpp_robot_core/src/sdk_robot_facade_cache.cpp': 220,
    'cpp_robot_core/src/core_runtime.cpp': 820,
    'cpp_robot_core/src/core_runtime_contracts.cpp': 880,
    'spine_ultrasound_ui/core/postprocess_service.py': 920,
    'spine_ultrasound_ui/core/session_service.py': 660,
    'spine_ultrasound_ui/services/api_bridge_backend.py': 560,
}


def _relative_python_path(path: Path, *, root: Path) -> Path:
    """Return a Python source path relative to the repository root.

    Args:
        path: Candidate Python source path.
        root: Repository root used to anchor the scan.

    Returns:
        The repository-relative path.

    Raises:
        ValueError: If ``path`` is not located under ``root``.
    """
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    try:
        return resolved_path.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError(f'python source is not inside repository root: {path}') from exc



def _should_skip_python_file(path: Path, *, root: Path, self_path: Path, config_manager: Path) -> bool:
    """Decide whether a Python file is out-of-scope for mainline gate scanning.

    Args:
        path: Candidate Python file discovered during repository traversal.
        root: Repository root used for relative-path checks.
        self_path: This gate script, skipped to avoid self-references.
        config_manager: Legacy compatibility module still allowed to reference
            ``ConfigManager``.

    Returns:
        ``True`` when the file must be skipped by the ConfigManager leakage scan.

    Raises:
        ValueError: If ``path`` is outside the repository root.

    Boundary behavior:
        - Only top-level mirror/archival directories are ignored.
        - ``tests`` and ``__pycache__`` are ignored wherever they appear.
        - Mainline package files remain scannable even if an ancestor directory
          elsewhere in the execution environment is named ``repo``.
    """
    resolved_path = path.resolve()
    if resolved_path == config_manager.resolve() or resolved_path == self_path.resolve():
        return True

    relative_path = _relative_python_path(path, root=root)
    if not relative_path.parts:
        return False

    if relative_path.parts[0] in IGNORED_TOP_LEVEL_DIRS:
        return True
    if 'tests' in relative_path.parts or '__pycache__' in relative_path.parts:
        return True
    return False



def _iter_scannable_python_sources(*, root: Path, self_path: Path, config_manager: Path) -> Iterator[Path]:
    """Yield mainline Python sources that must satisfy the architecture gate.

    Args:
        root: Repository root.
        self_path: Current script path.
        config_manager: Legacy compatibility module exempt from leakage checks.

    Yields:
        Repository Python files that remain in-scope for mainline scanning.
    """
    for path in root.rglob('*.py'):
        if _should_skip_python_file(path, root=root, self_path=self_path, config_manager=config_manager):
            continue
        yield path



def main() -> int:
    failures: list[str] = []

    headless_text = HEADLESS_ADAPTER.read_text(encoding='utf-8')
    if '_bind_session_product_method' in headless_text or 'setattr(HeadlessAdapter' in headless_text:
        failures.append('HeadlessAdapter must expose an explicit session-product surface; dynamic method injection is forbidden')

    runtime_text = CORE_RUNTIME_HEADER.read_text(encoding='utf-8')
    for required in (
        'enum class RuntimeLane',
        'command_lane_mutex_',
        'query_lane_mutex_',
        'rt_lane_mutex_',
        'state_mutex_',
    ):
        if required not in runtime_text:
            failures.append(f'CoreRuntime lane contract missing: {required}')

    facade_text = SDK_FACADE_HEADER.read_text(encoding='utf-8')
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
        if required not in facade_text:
            failures.append(f'SdkRobotFacade controlled port contract missing: {required}')

    for required in (
        'cpp_robot_core/include/robot_core/sdk_robot_facade_internal.h',
        'cpp_robot_core/src/sdk_robot_facade_lifecycle.cpp',
        'cpp_robot_core/src/sdk_robot_facade_nrt.cpp',
        'cpp_robot_core/src/sdk_robot_facade_rt.cpp',
        'cpp_robot_core/src/sdk_robot_facade_cache.cpp',
    ):
        if not (ROOT / required).exists():
            failures.append(f'SdkRobotFacade split-unit missing: {required}')

    runtime_source = CORE_RUNTIME_SOURCE.read_text(encoding='utf-8')
    dispatcher_source = CORE_RUNTIME_DISPATCHER_SOURCE.read_text(encoding='utf-8')
    for required in (
        'queryPort().controllerLogs()',
        'lifecyclePort().connect',
    ):
        if required not in runtime_source:
            failures.append(f'CoreRuntime controlled-lane/port usage missing: {required}')
    for required in (
        'runtimeLaneForCommand',
        'findRuntimeCommandGuardContract',
        'validateRuntimeCommandGuard',
        'validateRuntimeCommandReplyEnvelope',
        'return dispatch_with_contract(owner_.rt_lane_mutex_)',
    ):
        if required not in dispatcher_source:
            failures.append(f'CoreRuntime controlled-lane/port usage missing: {required}')

    nrt_source = NRT_MOTION_SOURCE.read_text(encoding='utf-8')
    if 'nrtExecutionPort().' not in nrt_source:
        failures.append('NrtMotionService must consume the restricted NrtExecutionPort surface')

    rt_source = RT_MOTION_SOURCE.read_text(encoding='utf-8')
    if 'rtControlPort().' not in rt_source:
        failures.append('RtMotionService must consume the restricted RtControlPort surface')

    session_source = SESSION_EXECUTION_SOURCE.read_text(encoding='utf-8')
    if 'collaborationPort().' not in session_source:
        failures.append('Session execution must consume the restricted CollaborationPort surface')

    controller_runtime_text = APP_CONTROLLER_RUNTIME_MIXIN.read_text(encoding='utf-8')
    for required in (
        'telemetry_received.connect(self._handle_telemetry, Qt.QueuedConnection)',
        'log_generated.connect(self._forward_log, Qt.QueuedConnection)',
        'camera_pixmap_ready.connect(self._on_camera_pixmap, Qt.QueuedConnection)',
        'ultrasound_pixmap_ready.connect(self._on_ultrasound_pixmap, Qt.QueuedConnection)',
    ):
        if required not in APP_CONTROLLER_RUNTIME_MIXIN.read_text(encoding='utf-8'):
            failures.append(f'AppControllerRuntimeMixin Qt queued connection contract missing: {required}')

    if 'self.runtime_bridge.refresh_governance(force_sdk_assets=False)' in controller_runtime_text:
        failures.append('_emit_status must not trigger a full governance refresh')
    for required in (
        'must stay side-effect-light',
        'must not trigger governance recomputation',
    ):
        if required not in controller_runtime_text:
            failures.append(f'AppControllerRuntimeMixin status emission contract missing: {required}')

    session_service_text = (ROOT / 'spine_ultrasound_ui' / 'core' / 'session_service.py').read_text(encoding='utf-8')
    if 'SESSION_SERVICE_PUBLIC_API' not in session_service_text:
        failures.append('SessionService compatibility surface freeze missing: SESSION_SERVICE_PUBLIC_API')

    runtime_bridge_text = APP_RUNTIME_BRIDGE.read_text(encoding='utf-8')
    if 'refresh_bridge_projection' not in runtime_bridge_text:
        failures.append('AppRuntimeBridge must route telemetry status updates through the lightweight bridge projection path')

    api_bridge_backend_text = (ROOT / 'spine_ultrasound_ui' / 'services' / 'api_bridge_backend.py').read_text(encoding='utf-8')
    for required in (
        'ApiBridgeLeaseService',
        'ApiBridgeVerdictService',
        'def _lease_allowed(self) -> bool:',
        'if self._lease_allowed():',
        'effective_include_lease = include_lease and self._lease_allowed()',
        'self._lease_service.ensure_control_lease(',
        'self._verdict_service.resolve_final_verdict(',
    ):
        if required not in api_bridge_backend_text:
            failures.append(f'ApiBridgeBackend service split missing: {required}')

    runtime_command_catalog_text = RUNTIME_COMMAND_CATALOG.read_text(encoding='utf-8')
    runtime_contracts_header = RUNTIME_COMMAND_CONTRACTS_HEADER.read_text(encoding='utf-8')
    runtime_contracts_source = RUNTIME_COMMAND_CONTRACTS_SOURCE.read_text(encoding='utf-8')
    generated_typed_contracts = GENERATED_RUNTIME_COMMAND_CONTRACTS.read_text(encoding='utf-8')
    generated_typed_requests = (ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'generated_runtime_command_request_types.h').read_text(encoding='utf-8')
    generated_typed_parsers = (ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'generated_runtime_command_request_parsers.inc').read_text(encoding='utf-8')
    generated_typed_handler_decls = GENERATED_RUNTIME_TYPED_HANDLER_DECLS.read_text(encoding='utf-8')
    generated_typed_handler_adapters = GENERATED_RUNTIME_TYPED_HANDLER_ADAPTERS.read_text(encoding='utf-8')
    for required in (
        'struct RuntimeCommandRequest',
        'RuntimeTypedRequestVariant typed_request;',
        'bool buildTypedRuntimeCommandRequest',
        'struct RuntimeCommandRequestContract',
        'struct RuntimeCommandResponseContract',
        'struct RuntimeCommandGuardContract',
        'struct RuntimeCommandDispatchContract',
        'validateAndParseRuntimeCommandPayload',
    ):
        if required not in runtime_contracts_header:
            failures.append(f'Runtime typed command contract header missing: {required}')
    for required in (
        'buildRuntimeCommandInvocation(line, &invocation, &payload_error)',
        'auto reply = owner_.dispatchTypedCommand(invocation);',
        'return owner_.replyJson(invocation.request_id, false, payload_error.empty() ? "invalid command payload" : payload_error);',
    ):
        if required not in dispatcher_source:
            failures.append(f'CoreRuntime dispatcher must validate typed payload contracts before handler dispatch: {required}')
    for required in (
        'findRuntimeCommandTypedContract',
        'RuntimeCommandDispatchContract',
        'generated_runtime_command_contracts.inc',
        'generated_runtime_command_request_parsers.inc',
        'buildTypedRuntimeCommandRequest',
    ):
        if required not in runtime_contracts_source and required not in CORE_RUNTIME_SOURCE.read_text(encoding='utf-8'):
            failures.append(f'Runtime typed command contract source missing: {required}')
    if 'RuntimeCommandResponseContract' not in generated_typed_contracts:
        failures.append('Generated typed C++ runtime command contracts must advertise response contracts')

    for required in (
        'using RuntimeTypedRequestVariant = std::variant<',
        'ConnectRobotRequest',
        'LockSessionRequest',
        'ValidateScanPlanRequest',
    ):
        if required not in generated_typed_requests:
            failures.append(f'Generated typed request family missing: {required}')
    for required in (
        'if (command == "connect_robot")',
        'if (command == "lock_session")',
        'if (command == "validate_scan_plan")',
    ):
        if required not in generated_typed_parsers:
            failures.append(f'Generated typed request parser coverage missing: {required}')

    for required in (
        'handleConnectRobotTyped',
        'handleLockSessionTyped',
        'handleValidateScanPlanTyped',
    ):
        if required not in generated_typed_handler_decls:
            failures.append(f'Generated typed handler declaration family missing: {required}')
        if required not in generated_typed_handler_adapters:
            failures.append(f'Generated typed handler adapter family missing: {required}')

    if 'runtime_command_manifest.json' not in runtime_command_catalog_text or 'json.loads' not in runtime_command_catalog_text:
        failures.append('Runtime command catalog must load from the shared JSON manifest')

    generated_manifest_text = GENERATED_COMMAND_MANIFEST.read_text(encoding='utf-8')
    if 'Generated from schemas/runtime_command_manifest.json' not in generated_manifest_text:
        failures.append('Generated C++ command manifest must advertise the shared manifest origin')

    api_server_text = API_SERVER.read_text(encoding='utf-8')
    if '_runtime_container =' in api_server_text or 'adapter: HeadlessAdapter | None = None' in api_server_text:
        failures.append('api_server must not retain module-level runtime singleton fallbacks')
    if 'fastapi_app.state.runtime_container = resolved_container' not in api_server_text:
        failures.append('api_server must resolve dependencies through app.state runtime_container')

    main_window_text = MAIN_WINDOW.read_text(encoding='utf-8')
    for required in (
        '@Slot(object)\n    def _update_camera_pixmap',
        '@Slot(object)\n    def _update_ultrasound_pixmap',
        '@Slot(object)\n    def _update_reconstruction_pixmap',
    ):
        if required not in main_window_text:
            failures.append(f'MainWindow pixmap slot contract missing: {required}')

    if 'tests.archive' in CONTROL_OWNERSHIP_TEST.read_text(encoding='utf-8'):
        failures.append('Stable control ownership surface must not import archived compatibility tests')
    if 'tests.archive' in RUNTIME_VERDICT_TEST.read_text(encoding='utf-8'):
        failures.append('Stable runtime verdict surface must not import archived compatibility tests')
    verify_mainline_text = (ROOT / 'scripts' / 'verify_mainline.sh').read_text(encoding='utf-8')
    rt_quality_observed_fixture = ROOT / 'artifacts' / 'verification' / 'current_delivery_fix' / 'rt_quality_observed.json'
    if not rt_quality_observed_fixture.exists():
        failures.append('RT quality observed fixture must exist for mainline evidence gating')
    acceptance_text = (ROOT / 'scripts' / 'final_acceptance_audit.sh').read_text(encoding='utf-8')
    run_pytest_mainline_text = (ROOT / 'scripts' / 'run_pytest_mainline.py').read_text(encoding='utf-8')
    legacy_wrapper_paths = [ROOT / 'tests' / name for name in LEGACY_ARCHIVE_WRAPPER_BASENAMES]
    for wrapper_path in legacy_wrapper_paths:
        relative_wrapper = str(wrapper_path.relative_to(ROOT))
        if wrapper_path.exists():
            failures.append(f'Legacy archive wrapper must not exist in top-level tests surface: {relative_wrapper}')
        if relative_wrapper in verify_mainline_text:
            failures.append(f'Active verify gate must not schedule archive wrapper test: {relative_wrapper}')
        if relative_wrapper in acceptance_text:
            failures.append(f'Acceptance audit must not schedule archive wrapper test: {relative_wrapper}')
        if relative_wrapper in run_pytest_mainline_text:
            failures.append(f'run_pytest_mainline must not hardcode legacy archive wrapper ignores once wrappers are removed: {relative_wrapper}')


    runtime_verdict_text = (ROOT / 'spine_ultrasound_ui' / 'services' / 'runtime_verdict_kernel_service.py').read_text(encoding='utf-8')
    api_bridge_verdict_text = (ROOT / 'spine_ultrasound_ui' / 'services' / 'api_bridge_verdict_service.py').read_text(encoding='utf-8')
    for required in (
        'resolve_final_verdict',
        'read_only=not refresh_runtime_verdict',
    ):
        if required not in runtime_verdict_text:
            failures.append(f'Runtime verdict kernel canonical API missing: {required}')
    for forbidden in (
        'query_final_verdict_snapshot',
        'compile_final_verdict',
        'get_final_verdict',
    ):
        if forbidden in runtime_verdict_text:
            failures.append(f'Runtime verdict kernel must not use legacy backend verdict APIs directly: {forbidden}')

    for required in (
        '_raise_if_reply_failed',
        'Failed read/compile attempts do not fall back to cached verdicts',
    ):
        if required not in api_bridge_verdict_text:
            failures.append(f'ApiBridgeVerdictService reply-failure contract missing: {required}')

    recording_header_text = (ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'recording_service.h').read_text(encoding='utf-8')
    recording_source_text = (ROOT / 'cpp_robot_core' / 'src' / 'recording_service.cpp').read_text(encoding='utf-8')
    runtime_state_store_text = (ROOT / 'cpp_robot_core' / 'src' / 'runtime_state_store.cpp').read_text(encoding='utf-8')
    for required in (
        'SampleKind::AlarmEvent',
        'sample.alarm_event = alarm',
        'alarmJson(sample.alarm_event)',
    ):
        if required not in recording_source_text and required not in recording_header_text:
            failures.append(f'RecordingService async alarm persistence contract missing: {required}')
    if 'recording_service_.recordAlarm(alarm);' not in runtime_state_store_text:
        failures.append('CoreRuntime must enqueue alarms through RecordingService')

    for required in (
        'PendingRecordBundle record_bundle{};',
        'record_bundle = buildRecordBundleLocked();',
        'flushRecordBundle(record_bundle);',
    ):
        if required not in runtime_state_store_text:
            failures.append(f'CoreRuntime RT recording lock-scope contract missing: {required}')

    runtime_readiness_text = RUNTIME_READINESS_SERVICE.read_text(encoding='utf-8')
    for required in (
        'RuntimeReadinessManifestService',
        'static_contract_ready',
        'live_runtime_verified',
        'environment_blocked',
    ):
        if required not in runtime_readiness_text:
            failures.append(f'Runtime readiness manifest contract missing: {required}')

    headless_surface_text = (ROOT / 'spine_ultrasound_ui' / 'services' / 'headless_adapter_surface.py').read_text(encoding='utf-8')
    if '._session_product_update_envelopes(' in headless_surface_text:
        failures.append('HeadlessAdapterSurface must not reach into private event-surface helpers; use the public session_product_update_envelopes surface')

    for worker_name in (
        'preprocess_worker.py',
        'reconstruction_worker.py',
        'assessment_worker.py',
    ):
        worker_text = (ROOT / 'spine_ultrasound_ui' / 'workers' / worker_name).read_text(encoding='utf-8')
        if 'spine_ultrasound_ui.imaging.' in worker_text:
            failures.append(f'Demo worker must not import imaging modules directly: spine_ultrasound_ui/workers/{worker_name}')

    main_window_layout_text = MAIN_WINDOW_LAYOUT.read_text(encoding='utf-8')
    if 'w.backend.' in main_window_layout_text:
        failures.append('MainWindowLayout must not bind widgets directly to backend methods; route through MainWindowActionRouter')

    self_path = Path(__file__).resolve()
    scanned_python_files = 0
    for path in _iter_scannable_python_sources(root=ROOT, self_path=self_path, config_manager=CONFIG_MANAGER):
        scanned_python_files += 1
        text = path.read_text(encoding='utf-8')
        if 'ConfigManager' in text or 'config_manager' in text:
            failures.append(f'Legacy ConfigManager reference leaked into mainline: {path.relative_to(ROOT)}')

    if scanned_python_files == 0:
        failures.append('Architecture fitness gate scanned zero Python files; ignore rules are invalid')

    for relative_path, max_lines in _MAX_MAINLINE_FILE_LINES.items():
        file_path = ROOT / relative_path
        line_count = sum(1 for _ in file_path.open('r', encoding='utf-8'))
        if line_count > max_lines:
            failures.append(
                f'Mainline file size regression: {relative_path} has {line_count} lines (limit={max_lines})'
            )

    if failures:
        for item in failures:
            print(f'[FAIL] {item}')
        return 1
    print(f'[PASS] architecture fitness checks satisfied (scanned_python_files={scanned_python_files})')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
