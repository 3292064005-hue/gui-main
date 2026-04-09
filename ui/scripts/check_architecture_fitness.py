#!/usr/bin/env python3
from __future__ import annotations

from pathlib import Path
from typing import Iterator

ROOT = Path(__file__).resolve().parents[1]
HEADLESS_ADAPTER = ROOT / 'spine_ultrasound_ui' / 'services' / 'headless_adapter.py'
CORE_RUNTIME_HEADER = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'core_runtime.h'
CORE_RUNTIME_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'core_runtime.cpp'
SDK_FACADE_HEADER = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'sdk_robot_facade.h'
NRT_MOTION_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'nrt_motion_service.cpp'
RT_MOTION_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'rt_motion_service.cpp'
SESSION_EXECUTION_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'core_runtime_session_execution.cpp'
APP_CONTROLLER_RUNTIME_MIXIN = ROOT / 'spine_ultrasound_ui' / 'core' / 'app_controller_runtime_mixin.py'
APP_RUNTIME_BRIDGE = ROOT / 'spine_ultrasound_ui' / 'core' / 'app_runtime_bridge.py'
CONFIG_MANAGER = ROOT / 'spine_ultrasound_ui' / 'services' / 'config_manager.py'
MAIN_WINDOW_LAYOUT = ROOT / 'spine_ultrasound_ui' / 'views' / 'main_window_layout.py'
RUNTIME_READINESS_SERVICE = ROOT / 'spine_ultrasound_ui' / 'services' / 'runtime_readiness_manifest_service.py'
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
    'cpp_robot_core/src/core_runtime_contracts.cpp': 840,
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
    for required in (
        'commandCapabilityClaim',
        'capability_claim == "rt_motion_write"',
        'std::lock_guard<std::mutex> lane_lock(rt_lane_mutex_)',
        'queryPort().controllerLogs()',
        'lifecyclePort().connect',
    ):
        if required not in runtime_source:
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
