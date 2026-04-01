from __future__ import annotations

import ast
import re
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]

CHECKS = []


def record(name: str, ok: bool, detail: str) -> None:
    CHECKS.append((name, ok, detail))


def class_methods(path: Path, class_name: str) -> set[str]:
    tree = ast.parse(path.read_text(encoding='utf-8'))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            return {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
    return set()


def file_lines(rel: str) -> int:
    return sum(1 for _ in (ROOT / rel).open('r', encoding='utf-8'))


def file_contains(rel: str, pattern: str) -> bool:
    return re.search(pattern, (ROOT / rel).read_text(encoding='utf-8'), re.MULTILINE) is not None


def main() -> int:
    limits = {
        'spine_ultrasound_ui/core/app_controller.py': 250,
        'spine_ultrasound_ui/services/headless_adapter.py': 300,
        'spine_ultrasound_ui/main_window.py': 350,
        'spine_ultrasound_ui/services/api_bridge_backend.py': 500,
        'spine_ultrasound_ui/services/session_intelligence_service.py': 550,
        'spine_ultrasound_ui/services/mock_core_runtime.py': 1800,
        'cpp_robot_core/src/core_runtime.cpp': 1400,
    }
    for rel, limit in limits.items():
        count = file_lines(rel)
        record(f'line-budget:{rel}', count < limit, f'{count} lines (limit < {limit})')

    robot_methods = class_methods(ROOT / 'spine_ultrasound_ui/services/robot_core_client.py', 'RobotCoreClientBackend')
    api_methods = class_methods(ROOT / 'spine_ultrasound_ui/services/api_bridge_backend.py', 'ApiBridgeBackend')
    record('robot-core-final-verdict', 'get_final_verdict' in robot_methods, f'methods={sorted(robot_methods)}')
    record('api-bridge-final-verdict', 'get_final_verdict' in api_methods, f'methods={sorted(api_methods)}')

    history_files = list((ROOT / 'archive/docs_history').glob('*.md'))
    root_history_leaks = sorted((ROOT / 'docs').glob('*WAVE*.md')) + sorted((ROOT / 'docs').glob('*MAINLINE*.md'))
    record('docs-history-populated', bool(history_files), f'{len(history_files)} history docs')
    record('docs-root-clean', not root_history_leaks, f'leaks={[p.name for p in root_history_leaks]}')

    tls_cert = ROOT / 'configs/tls/robot_core_server.crt'
    record('tls-repo-clean', not tls_cert.exists(), f'committed_cert_present={tls_cert.exists()}')
    record('protocol-compile-command', file_contains('spine_ultrasound_ui/services/runtime_command_catalog.py', r'"compile_scan_plan"\s*:\s*\{') and file_contains('spine_ultrasound_ui/services/runtime_command_catalog.py', r'"query_final_verdict"\s*:\s*\{'), 'compile/query contract commands registered in canonical command catalog')
    runtime_final_verdict_files = ['cpp_robot_core/src/core_runtime.cpp', 'cpp_robot_core/src/core_runtime_power_validation.cpp']
    compile_present = any(file_contains(rel, r'command == "compile_scan_plan"') for rel in runtime_final_verdict_files)
    query_present = any(file_contains(rel, r'command == "query_final_verdict"') for rel in runtime_final_verdict_files)
    record('core-runtime-final-verdict', compile_present and query_present, 'cpp core runtime handles compile/query final verdict across split handler files')
    record('protocol-sync-script', (ROOT / 'scripts/check_protocol_sync.py').exists(), 'protocol sync script present')
    record('protocol-proto-source', (ROOT / 'cpp_robot_core/proto/ipc_messages.proto').exists(), 'canonical proto source present')
    record('protocol-python-pb2', (ROOT / 'spine_ultrasound_ui/services/ipc_messages_pb2.py').exists(), 'python pb2 asset present')
    record('protocol-cpp-wire-codec', (ROOT / 'cpp_robot_core/include/ipc_messages.pb.h').exists() and (ROOT / 'cpp_robot_core/src/ipc_messages.pb.cpp').exists(), 'cpp wire codec assets present')

    stable_tests = {
        'test_api_contract.py',
        'test_api_security.py',
        'test_control_plane.py',
        'test_control_ownership.py',
        'test_runtime_verdict.py',
        'test_headless_runtime.py',
        'test_release_gate.py',
        'test_replay_determinism.py',
        'test_profile_policy.py',
        'test_spawned_core_integration.py',
    }
    tests_root = ROOT / 'tests'
    root_test_names = {p.name for p in tests_root.glob('test_*.py')}
    versioned_root_tests = sorted(name for name in root_test_names if re.search(r'_v\d+|_wave_', name))
    history_test_files = list((tests_root / 'archive').glob('test_*.py'))
    record('tests-archive-populated', bool(history_test_files), f'{len(history_test_files)} archived history tests')
    record('tests-stable-surface', stable_tests.issubset(root_test_names), f'missing={sorted(stable_tests - root_test_names)}')
    record('tests-root-clean', not versioned_root_tests, f'leaks={versioned_root_tests}')
    record('event-bus-canonical-names', (ROOT / 'spine_ultrasound_ui/core/ui_local_bus.py').exists() and (ROOT / 'spine_ultrasound_ui/services/event_bus.py').exists() and (ROOT / 'spine_ultrasound_ui/services/event_replay_bus.py').exists(), 'canonical ui/runtime bus modules available without shim wrappers')

    failures = 0
    for name, ok, detail in CHECKS:
        status = 'PASS' if ok else 'FAIL'
        print(f'[{status}] {name}: {detail}')
        failures += 0 if ok else 1
    return failures


if __name__ == '__main__':
    raise SystemExit(main())
