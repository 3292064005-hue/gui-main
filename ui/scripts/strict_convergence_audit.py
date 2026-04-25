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
    record(
        'protocol-plan-compile-command',
        file_contains('schemas/runtime_command_manifest.json', r'"name"\s*:\s*"validate_scan_plan"')
        and not file_contains('schemas/runtime_command_manifest.json', r'"name"\s*:\s*"compile_scan_plan"')
        and file_contains('schemas/runtime_command_compat_manifest.json', r'"name"\s*:\s*"compile_scan_plan"')
        and file_contains('schemas/runtime_command_manifest.json', r'"canonical_command"\s*:\s*"validate_scan_plan"')
        and file_contains('schemas/runtime_command_manifest.json', r'"name"\s*:\s*"query_final_verdict"'),
        'validate/query contract commands registered in canonical manifest; compile alias retired into compat manifest',
    )
    runtime_final_verdict_patterns = {
        'validate_scan_plan': [
            r'command == "validate_scan_plan"',
            r'"validate_scan_plan"\s*,\s*&CoreRuntime::handleValidationCommand',
            r'"validate_scan_plan"\s*,\s*\[\]\(CoreRuntime\* self',
        ],
        'query_final_verdict': [
            r'command == "query_final_verdict"',
            r'"query_final_verdict"\s*,\s*&CoreRuntime::handleValidationCommand',
            r'"query_final_verdict"\s*,\s*\[\]\(CoreRuntime\* self',
        ],
    }
    runtime_final_verdict_files = [
        'cpp_robot_core/src/core_runtime.cpp',
        'cpp_robot_core/src/core_runtime_power_validation.cpp',
        'cpp_robot_core/src/command_registry.cpp',
    ]
    validate_present = any(
        file_contains(rel, pattern)
        for rel in runtime_final_verdict_files
        for pattern in runtime_final_verdict_patterns['validate_scan_plan']
    )
    compile_alias_present = not any(file_contains(rel, 'compile_scan_plan') for rel in runtime_final_verdict_files)
    query_present = any(
        file_contains(rel, pattern)
        for rel in runtime_final_verdict_files
        for pattern in runtime_final_verdict_patterns['query_final_verdict']
    )
    record('core-runtime-final-verdict', validate_present and compile_alias_present and query_present, 'cpp core runtime handles validate/query final verdict without active compile_scan_plan alias')
    record('protocol-sync-script', (ROOT / 'scripts/check_protocol_sync.py').exists(), 'protocol sync script present')
    record('protocol-proto-source', (ROOT / 'cpp_robot_core/proto/ipc_messages.proto').exists(), 'canonical proto source present')
    record('protocol-python-pb2', (ROOT / 'spine_ultrasound_ui/services/ipc_messages_pb2.py').exists(), 'python pb2 asset present')
    record('protocol-cpp-wire-codec', (ROOT / 'cpp_robot_core/include/ipc_messages.pb.h').exists() and (ROOT / 'cpp_robot_core/src/ipc_messages.pb.cpp').exists(), 'cpp wire codec assets present')

    stable_tests = {
        'test_runtime_refactor_guards.py',
        'test_backend_link_and_api_bridge.py',
        'test_api_bridge_verdict_service.py',
        'test_control_ownership.py',
        'test_runtime_verdict.py',
        'test_headless_adapter_surface_refactor.py',
        'test_runtime_verdict_authority_contract.py',
        'test_control_authority_claims.py',
        'test_guidance_freeze_contracts.py',
        'test_runtime_mode_policy.py',
        'test_vendor_sdk_and_identity.py',
        'test_architecture_fitness.py',
    }
    tests_root = ROOT / 'tests'
    root_test_names = {p.name for p in tests_root.glob('test_*.py')}
    versioned_root_tests = sorted(name for name in root_test_names if re.search(r'_v\d+|_wave_', name))
    history_test_files = list((tests_root / 'archive').glob('test_*.py'))
    record('tests-archive-populated', bool(history_test_files), f'{len(history_test_files)} archived history tests')
    record('tests-stable-surface', stable_tests.issubset(root_test_names), f'missing={sorted(stable_tests - root_test_names)}')
    record('tests-root-clean', not versioned_root_tests, f'leaks={versioned_root_tests}')
    record('event-bus-canonical-names', (ROOT / 'spine_ultrasound_ui/core/ui_local_bus.py').exists() and (ROOT / 'spine_ultrasound_ui/services/event_bus.py').exists() and (ROOT / 'spine_ultrasound_ui/services/event_replay_bus.py').exists(), 'canonical ui/runtime bus modules available without shim wrappers')


    api_bridge_text = (ROOT / 'spine_ultrasound_ui/services/api_bridge_backend.py').read_text(encoding='utf-8')
    api_component_files = [
        'spine_ultrasound_ui/services/api_bridge_transport_client.py',
        'spine_ultrasound_ui/services/api_bridge_authority_projection_reader.py',
        'spine_ultrasound_ui/services/api_bridge_telemetry_client.py',
        'spine_ultrasound_ui/services/api_bridge_media_client.py',
    ]
    record('api-bridge-component-files', all((ROOT / rel).exists() for rel in api_component_files), f'components={api_component_files}')
    forbidden_api_backend_methods = ['def _health_loop', 'def _telemetry_ws_loop', 'def _media_ws_loop', 'def _pull_snapshot_once', 'def _capture_reply_contracts', 'def _push_runtime_config']
    leaks = [name for name in forbidden_api_backend_methods if name in api_bridge_text]
    record('api-bridge-facade-thin', not leaks, f'backend_method_leaks={leaks}')

    core_runtime_header = (ROOT / 'cpp_robot_core/include/robot_core/core_runtime.h').read_text(encoding='utf-8')
    required_runtime_components = [
        'RuntimeStateStore state_store_',
        'RuntimeAuthorityKernel authority_kernel_',
        'RuntimeEvidenceProjector evidence_projector_',
        'RuntimeProcedureExecutor procedure_executor_',
        'RuntimeQueryProjector query_projector_',
    ]
    record('core-runtime-kernel-components', all(token in core_runtime_header for token in required_runtime_components), f'required={required_runtime_components}')
    direct_runtime_member_leaks = [
        'RuntimeAuthorityLease authority_lease_',
        'RecordingService recording_service_',
        'NrtMotionService nrt_motion_service_',
        'RtMotionService rt_motion_service_',
        'RecoveryManager recovery_manager_',
        'SdkRobotFacade sdk_robot_',
    ]
    leaks = [token for token in direct_runtime_member_leaks if token in core_runtime_header]
    record('core-runtime-direct-member-retired', not leaks, f'direct_member_leaks={leaks}')


    helper_text = (ROOT / 'cpp_robot_core/src/core_runtime_command_helpers.h').read_text(encoding='utf-8')
    command_sources = [
        ROOT / 'cpp_robot_core/src/core_runtime_session_commands.cpp',
        ROOT / 'cpp_robot_core/src/core_runtime_execution_commands.cpp',
        ROOT / 'cpp_robot_core/src/core_runtime_authority.cpp',
    ]
    command_source_text = '\n'.join(path.read_text(encoding='utf-8') for path in command_sources)
    helper_contract_ok = (
        'normalizeAuthorityToken' in helper_text
        and 'joinClaims' in helper_text
        and 'Pure helper' in helper_text
        and command_source_text.count('normalizeAuthorityToken(') >= 5
        and 'std::string normalizeAuthorityToken' not in command_source_text
    )
    record('core-runtime-command-helper-closure', helper_contract_ok, 'authority token and claim formatting helpers centralized outside command handlers')

    artifact_registry_text = (ROOT / 'spine_ultrasound_ui/core/artifact_lifecycle_registry.py').read_text(encoding='utf-8')
    formal_placeholder_leak = 'materialized_or_declared_placeholder' in artifact_registry_text
    artifact_gate_text = (ROOT / 'scripts/check_artifact_lifecycle_registry.py').read_text(encoding='utf-8')
    record(
        'formal-evidence-chain-no-placeholder-policy',
        not formal_placeholder_leak and 'formal evidence-chain artifact must not use placeholder materialization policy' in artifact_gate_text,
        f'formal_placeholder_leak={formal_placeholder_leak}',
    )

    claim_boundary_script = ROOT / 'scripts/check_mainline_claim_boundary.py'
    claim_boundary_wired = all(
        token in (ROOT / rel).read_text(encoding='utf-8')
        for rel, token in (
            ('.github/workflows/mainline.yml', 'scripts/check_mainline_claim_boundary.py'),
            ('scripts/verify_mainline.sh', 'scripts/check_mainline_claim_boundary.py'),
            ('scripts/final_acceptance_audit.sh', 'scripts/check_mainline_claim_boundary.py'),
        )
    )
    record('mainline-claim-boundary-gate-wired', claim_boundary_script.exists() and claim_boundary_wired, 'claim boundary gate is present in workflow, verify_mainline, and final acceptance audit')

    failures = 0
    for name, ok, detail in CHECKS:
        status = 'PASS' if ok else 'FAIL'
        print(f'[{status}] {name}: {detail}')
        failures += 0 if ok else 1
    return failures


if __name__ == '__main__':
    raise SystemExit(main())
