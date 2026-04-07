from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
HEADLESS_ADAPTER = ROOT / 'spine_ultrasound_ui' / 'services' / 'headless_adapter.py'
CORE_RUNTIME_HEADER = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'core_runtime.h'
SDK_FACADE_HEADER = ROOT / 'cpp_robot_core' / 'include' / 'robot_core' / 'sdk_robot_facade.h'
CORE_RUNTIME_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'core_runtime.cpp'
NRT_MOTION_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'nrt_motion_service.cpp'
RT_MOTION_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'rt_motion_service.cpp'
SESSION_EXECUTION_SOURCE = ROOT / 'cpp_robot_core' / 'src' / 'core_runtime_session_execution.cpp'
CONFIG_MANAGER = ROOT / 'spine_ultrasound_ui' / 'services' / 'config_manager.py'
IGNORED_TOP_LEVEL_DIRS = frozenset({'.git', '.pytest_cache', 'archive', 'repo'})
_MAX_MAINLINE_FILE_LINES = {
    'cpp_robot_core/src/sdk_robot_facade.cpp': 1650,
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

    runtime_source = CORE_RUNTIME_SOURCE.read_text(encoding='utf-8')
    for required in (
        '{"seek_contact", RuntimeLane::RtControl}',
        '{"start_scan", RuntimeLane::RtControl}',
        '{"pause_scan", RuntimeLane::RtControl}',
        '{"resume_scan", RuntimeLane::RtControl}',
        '{"safe_retreat", RuntimeLane::RtControl}',
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
