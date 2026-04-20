
from pathlib import Path
import subprocess
import sys


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def _extract_shell_array(script: str, array_name: str) -> list[str]:
    marker = f"{array_name}=("
    start = script.index(marker) + len(marker)
    end = script.index(')\n', start)
    body = script[start:end]
    return [line.strip().strip('"') for line in body.splitlines() if line.strip()]


def test_verify_mainline_uses_ephemeral_build_dir_and_phase_dispatch() -> None:
    script = _read('scripts/verify_mainline.sh')
    assert 'mktemp -d /tmp/gui_main_cpp_mainline_build.' in script
    assert 'rm -rf "${BUILD_DIR}"' in script
    assert 'VERIFY_PHASE="${VERIFY_PHASE:-all}"' in script
    assert 'case "${VERIFY_PHASE}" in' in script
    assert 'run_cpp_profile_gate mock' in script or 'run_cpp_profile_gate "mock"' in script
    assert 'scripts/build_cpp_targets.py' in script
    assert '--jobs "${CMAKE_BUILD_PARALLEL_LEVEL}"' in script
    assert 'ctest --test-dir' in script


def test_start_real_and_demo_do_not_dirty_repo_build_tree() -> None:
    start_real = _read('scripts/start_real.sh')
    start_demo = _read('scripts/start_demo.sh')
    assert 'start_hil.sh' in start_real and 'start_prod.sh' in start_real
    assert 'trap ' in start_demo
    assert 'cd "$ROOT_DIR"' in start_demo


def test_cpp_profile_flags_are_build_type_aware() -> None:
    cmake_profile = _read('cpp_robot_core/cmake/RobotCoreProfiles.cmake')
    assert '-O3 -pthread' not in cmake_profile
    assert 'set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g3"' in cmake_profile
    assert 'set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG"' in cmake_profile
    build_options = _read('cpp_robot_core/cmake/RobotCoreBuildOptions.cmake')
    assert 'target_compile_options(${target_name} PRIVATE -pthread)' in build_options


def test_cpp_deployment_contract_no_longer_requires_system_protobuf_toolchain() -> None:
    contract_src = _read('cpp_robot_core/src/core_runtime_contracts.cpp')
    assert 'protobuf headers' not in contract_src
    assert 'required_host_dependencies", stringArray({"cmake", "g++/clang++", "openssl headers", "eigen headers"})' in contract_src


def test_mainline_pytest_entrypoint_disables_repo_cacheprovider_by_default() -> None:
    script = _read('scripts/run_pytest_mainline.py')
    assert 'no:cacheprovider' in script


def test_mainline_pytest_entrypoint_cleans_python_artifacts_after_run() -> None:
    script = _read('scripts/run_pytest_mainline.py')
    assert '_cleanup_generated_python_artifacts' in script
    assert "os.walk(ROOT, topdown=False)" in script


def test_mainline_cpp_gates_default_to_mock_without_sdk() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    acceptance_script = _read('scripts/final_acceptance_audit.sh')
    assert 'ROBOT_CORE_WITH_XCORE_SDK="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}"' in verify_script
    assert 'ROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}"' in verify_script
    assert 'run_cpp_profile_gate' in verify_script
    assert 'ROBOT_CORE_WITH_XCORE_SDK="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}"' in acceptance_script
    assert 'ROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}"' in acceptance_script


def test_cpp_profiles_override_release_flags_to_o2() -> None:
    profile = _read('cpp_robot_core/cmake/RobotCoreProfiles.cmake')
    assert 'set(CMAKE_CXX_FLAGS_RELEASE "-O2 -DNDEBUG"' in profile
    assert 'set(CMAKE_CXX_FLAGS_DEBUG "-O0 -g3"' in profile


def test_mainline_cpp_gate_scripts_retry_incremental_build_once() -> None:
    wrapper = _read('scripts/build_cpp_targets.py')
    assert 'retrying' in wrapper
    assert 'attempt in (1, 2)' in wrapper


def test_verify_and_acceptance_run_protocol_sync_gate() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    acceptance_script = _read('scripts/final_acceptance_audit.sh')
    assert 'scripts/check_protocol_sync.py' in verify_script
    assert 'scripts/check_protocol_sync.py' in acceptance_script


def test_convergence_audit_expands_budgets_to_hotspot_files() -> None:
    script = _read('scripts/strict_convergence_audit.py')
    assert "'spine_ultrasound_ui/services/mock_core_runtime.py': 1800" in script
    assert "'cpp_robot_core/src/core_runtime.cpp': 1400" in script
    assert "'spine_ultrasound_ui/services/api_bridge_backend.py': 500" in script
    assert "'spine_ultrasound_ui/services/session_intelligence_service.py': 550" in script




def test_strict_convergence_audit_current_repository_passes() -> None:
    result = subprocess.run([sys.executable, 'scripts/strict_convergence_audit.py'], cwd=Path('.').resolve(), capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr

def test_workflow_uses_converged_verify_script_and_no_longer_installs_system_protobuf() -> None:
    workflow = _read('.github/workflows/mainline.yml')
    assert './scripts/verify_mainline.sh' in workflow
    assert 'protobuf-compiler' not in workflow
    assert 'libprotobuf-dev' not in workflow


def test_protocol_sync_script_checks_proto_python_and_cpp_assets() -> None:
    script = _read('scripts/check_protocol_sync.py')
    assert 'ipc_messages.proto' in script
    assert 'ipc_messages_pb2.py' in script
    assert 'ipc_messages.pb.h' in script
    assert 'ipc_messages.pb.cpp' in script


def test_cpp_examples_are_not_built_by_default_in_mainline() -> None:
    cmake = _read('cpp_robot_core/CMakeLists.txt')
    assert 'option(ROBOT_CORE_BUILD_EXAMPLES' in cmake
    assert 'if(ROBOT_CORE_BUILD_EXAMPLES)' in cmake


def test_mainline_cpp_gate_uses_phase_isolated_build_directories() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    assert 'profile_build_dir()' in verify_script
    assert "${BUILD_DIR}" in verify_script
    assert 'assert_registered_cpp_tests' in verify_script
    assert 'EXPECTED_CPP_TEST_COUNT' in verify_script


def test_mainline_cpp_targets_include_contact_control_and_rt_truth_suite() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    for target in [
        'spine_robot_core_runtime',
        'spine_robot_core',
        'test_seqlock',
        'test_force_control',
        'test_normal_force_estimator',
        'test_normal_axis_admittance_controller',
        'test_tangential_scan_controller',
        'test_orientation_trim_controller',
        'test_contact_control_contract',
        'test_impedance_scan',
        'test_protocol_bridge',
        'test_recovery_manager',
        'test_recording_service',
        'test_rt_motion_service_truth',
    ]:
        assert target in verify_script


def test_mock_profile_overrides_target_optimization_for_stable_verification() -> None:
    profile = _read('cpp_robot_core/cmake/RobotCoreProfiles.cmake')
    assert 'ROBOT_CORE_PROFILE must be explicitly set' in profile
    assert 'target_compile_options(${target_name} PRIVATE -pthread)' in _read('cpp_robot_core/cmake/RobotCoreBuildOptions.cmake')


def test_mainline_cpp_gate_emits_build_heartbeat_for_long_compiles() -> None:
    wrapper = _read('scripts/build_cpp_targets.py')
    assert '[build] still building' in wrapper
    assert '[build] retrying' in wrapper


def test_cpp_build_wrapper_script_exists() -> None:
    script = _read('scripts/build_cpp_targets.py')
    assert 'still building' in script
    assert 'retrying' in script
    assert '--build-dir' in script


def test_systemd_cpp_service_points_to_installed_binary_not_build_tree() -> None:
    service = _read('configs/systemd/spine-cpp-core.service')
    assert '/opt/spine_ultrasound/cpp_robot_core/bin/spine_robot_core' in service
    assert '/opt/spine_ultrasound/cpp_robot_core/build/spine_robot_core' not in service


def test_cpp_prereq_script_uses_same_mock_mainline_defaults() -> None:
    script = _read('scripts/check_cpp_prereqs.sh')
    assert 'ROBOT_CORE_PROFILE="${ROBOT_CORE_PROFILE:-mock}"' in script
    assert 'ROBOT_CORE_WITH_XCORE_SDK="${ROBOT_CORE_WITH_XCORE_SDK:-OFF}"' in script
    assert 'ROBOT_CORE_WITH_XMATE_MODEL="${ROBOT_CORE_WITH_XMATE_MODEL:-OFF}"' in script


def test_acceptance_audit_batches_critical_regression_suite() -> None:
    script = _read('scripts/final_acceptance_audit.sh')
    assert 'run_pytest_batch()' in script
    for label in ['control-plane', 'release-state', 'sdk-and-doctor', 'xmate-mainline']:
        assert f'run_pytest_batch {label}' in script


def test_acceptance_audit_runs_hygiene_and_cpp_preflight_before_build() -> None:
    script = _read('scripts/final_acceptance_audit.sh')
    assert 'section "Repository hygiene"' in script
    assert 'bash scripts/check_repo_hygiene.sh' in script
    assert 'section "C++ preflight"' in script
    assert 'bash scripts/check_cpp_prereqs.sh' in script


def test_mainline_pytest_entrypoint_cleans_artifacts_with_bottom_up_walk() -> None:
    script = _read('scripts/run_pytest_mainline.py')
    assert 'os.walk(ROOT, topdown=False)' in script
    assert "dirname == '.pytest_cache'" in script or 'dirname == ".pytest_cache"' in script


def test_verify_and_acceptance_preclean_generated_python_artifacts_before_hygiene() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    acceptance_script = _read('scripts/final_acceptance_audit.sh')
    assert verify_script.index('cleanup_generated_artifacts') < verify_script.index('bash scripts/check_repo_hygiene.sh')
    assert acceptance_script.index('cleanup_generated_artifacts') < acceptance_script.index('section "Repository hygiene"')


def test_protocol_sync_and_doctor_scripts_disable_bytecode_writes() -> None:
    protocol_sync = _read('scripts/check_protocol_sync.py')
    doctor_runtime = _read('scripts/doctor_runtime.py')
    assert "sys.dont_write_bytecode = True" in protocol_sync
    assert "_cleanup_generated_python_artifacts" in protocol_sync
    assert "sys.dont_write_bytecode = True" in doctor_runtime



def test_cpp_prereq_script_uses_ephemeral_build_dir_and_cleans_it() -> None:
    script = _read('scripts/check_cpp_prereqs.sh')
    assert 'mktemp -d /tmp/gui_main_cpp_prereqs.' in script
    assert 'trap cleanup_build_dir EXIT' in script



def test_readme_and_deployment_document_tls_bootstrap_before_doctor() -> None:
    readme = _read('README.md')
    deployment = _read('docs/04_profiles_and_release/RELEASE_READINESS.md')
    assert './scripts/generate_dev_tls_cert.sh' in readme
    assert './scripts/generate_dev_tls_cert.sh' in deployment


def test_cpp_prereq_script_enforces_cmake_minimum_version() -> None:
    script = _read('scripts/check_cpp_prereqs.sh')
    assert "cmake>=3.24" in script
    assert "cmake --version" in script



def test_readme_and_deployment_document_current_runtime_version_policy() -> None:
    readme = _read('README.md')
    deployment = _read('docs/04_profiles_and_release/RELEASE_READINESS.md')
    requirements = _read('requirements.txt')
    assert "PySide6 >= 6.7" in readme
    assert "protobuf>=3.20.3,<8" in readme
    assert "PySide6 >= 6.7" in deployment
    assert "protobuf>=3.20.3,<8" in deployment
    assert "protobuf>=3.20.3,<8" in requirements


def test_verify_mainline_emits_phase_scoped_failure_context_and_rejects_unknown_phase() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    assert '[FAIL] verify_mainline.sh phase=' in verify_script
    assert 'Unsupported VERIFY_PHASE=' in verify_script
    assert 'Expected one of: python, mock, hil, prod, all' in verify_script


def test_verify_mainline_batches_default_python_gate_for_constrained_envs() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    assert 'run_python_pytest_batch' in verify_script
    for label in ['control-plane', 'release-state', 'repository-gates', 'preweight-closure']:
        assert f'run_python_pytest_batch {label}' in verify_script


def test_verify_mainline_keeps_archive_compat_out_of_default_python_gate() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    assert 'INCLUDE_ARCHIVE_COMPAT' in verify_script
    assert 'run_python_pytest_batch archive-compat' in verify_script


def test_verify_mainline_prod_phase_builds_tests_and_installs() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    assert 'run_cpp_profile_install_check' in verify_script
    assert 'run_prod_profile_release_smoke' in verify_script
    assert 'scripts/deployment_smoke_test.py' in verify_script
    assert 'EXPECTED_CPP_TEST_COUNT="${EXPECTED_CPP_TEST_COUNT:-${#CPP_TEST_TARGETS[@]}}"' in verify_script



def test_p2_acceptance_artifacts_are_generated_outside_repository_payload() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    generator_script = _read('scripts/generate_p2_acceptance_artifacts.py')
    checker_script = _read('scripts/check_p2_acceptance.py')
    hygiene_script = _read('scripts/check_repo_hygiene.sh')
    assert 'P2_ACCEPTANCE_OUTPUT_ROOT="${BUILD_DIR}/p2_acceptance"' in verify_script
    assert 'tempfile.gettempdir()' in generator_script
    assert '/tmp/spine_p2_acceptance_static' not in checker_script
    assert 'missing P2 acceptance artifacts in configured output root' in checker_script
    assert 'derived/postprocess/postprocess_stage_manifest.json' in hygiene_script
    assert 'derived/session/session_intelligence_manifest.json' in hygiene_script


def test_verify_mainline_uses_configured_python_interpreter_for_build_and_smoke_scripts() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    assert 'PYTHON_BIN="${PYTHON_BIN:-python3}"' in verify_script
    assert '"$PYTHON_BIN" scripts/build_cpp_targets.py' in verify_script
    assert 'SPINE_DEPLOYMENT_PROFILE=clinical "$PYTHON_BIN" scripts/deployment_smoke_test.py' in verify_script


def test_verify_mainline_can_emit_claim_safe_verification_report() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    assert 'VERIFICATION_REPORT' in verify_script
    assert 'scripts/write_verification_report.py' in verify_script


def test_acceptance_audit_emits_claim_safe_verification_report_and_does_not_overclaim() -> None:
    script = _read('scripts/final_acceptance_audit.sh')
    assert 'verification_execution_report.json' in script
    assert 'Live-controller/HIL validation is not implied' in script


def test_acceptance_audit_forces_mock_profile_bindings_off_even_when_live_flags_are_enabled() -> None:
    script = _read('scripts/final_acceptance_audit.sh')
    assert 'if [[ "$PROFILE" == "mock" ]]; then' in script
    assert 'PROFILE_WITH_SDK=OFF' in script
    assert 'PROFILE_WITH_MODEL=OFF' in script


def test_verification_report_script_disables_bytecode_writes() -> None:
    script = _read('scripts/write_verification_report.py')
    assert 'sys.dont_write_bytecode = True' in script
    assert '--write-readiness-manifest' in script


def test_verify_and_acceptance_run_robot_identity_registry_gate() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    acceptance_script = _read('scripts/final_acceptance_audit.sh')
    assert 'scripts/check_robot_identity_registry.py' in verify_script
    assert 'scripts/check_robot_identity_registry.py' in acceptance_script
    assert 'scripts/check_python_compile.py' in verify_script
    assert 'scripts/check_python_compile.py' in acceptance_script


def test_acceptance_audit_runs_the_same_repository_gates_as_verify_python_phase() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    acceptance_script = _read('scripts/final_acceptance_audit.sh')
    for gate in [
        'bash scripts/check_repo_hygiene.sh',
        'scripts/strict_convergence_audit.py',
        'scripts/check_protocol_sync.py',
        'scripts/check_robot_identity_registry.py',
        'scripts/check_python_compile.py',
        'scripts/check_canonical_imports.py',
        'scripts/check_repository_gates.py',
        'scripts/check_architecture_fitness.py',
        'scripts/check_verification_boundary.py',
        'scripts/generate_p2_acceptance_artifacts.py',
        'scripts/check_p2_acceptance.py',
    ]:
        assert gate in verify_script
        assert gate in acceptance_script
    assert 'P2_ACCEPTANCE_OUTPUT_ROOT="$BUILD_DIR/p2_acceptance"' in acceptance_script
    assert 'Repository/profile acceptance gates passed for the checks executed by final_acceptance_audit.sh' in acceptance_script


def test_live_evidence_bundle_mode_does_not_mix_external_readiness_manifest_flags() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    acceptance_script = _read('scripts/final_acceptance_audit.sh')
    assert 'elif [[ -n "${READINESS_MANIFEST_REPORT}" ]]; then' in verify_script
    assert 'if [[ -n "$LIVE_EVIDENCE_BUNDLE" ]]; then' in acceptance_script
    assert 'WRITE_ARGS+=(--live-evidence-bundle "$LIVE_EVIDENCE_BUNDLE")' in acceptance_script
    assert 'WRITE_ARGS+=(--write-readiness-manifest "$READINESS_MANIFEST_REPORT")' in acceptance_script
    assert 'if [[ -z "$LIVE_EVIDENCE_BUNDLE" ]]; then SUMMARY_ARGS+=(--readiness-manifest "$READINESS_MANIFEST_REPORT"); fi' in acceptance_script
    assert 'LEDGER_ARGS+=(--readiness-manifest "$READINESS_MANIFEST_REPORT")' in acceptance_script
    assert 'LEDGER_ARGS+=(--live-evidence-bundle "$LIVE_EVIDENCE_BUNDLE")' in acceptance_script





def test_acceptance_audit_builds_and_registers_the_same_cpp_test_set_as_mainline() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    acceptance_script = _read('scripts/final_acceptance_audit.sh')
    verify_targets = _extract_shell_array(verify_script, 'CPP_TEST_TARGETS')
    acceptance_targets = _extract_shell_array(acceptance_script, 'CPP_TEST_TARGETS')
    assert acceptance_targets == verify_targets
    assert 'EXPECTED_CPP_TEST_COUNT="${EXPECTED_CPP_TEST_COUNT:-${#CPP_TEST_TARGETS[@]}}"' in acceptance_script
    assert 'count_registered_cpp_tests' in acceptance_script
    assert 'ctest registered $REGISTERED_CPP_TESTS' in acceptance_script
def test_acceptance_audit_emits_build_evidence_and_summary_reports() -> None:
    script = _read('scripts/final_acceptance_audit.sh')
    assert 'BUILD_EVIDENCE_REPORT="$BUILD_DIR/build_evidence_report.json"' in script
    assert 'ACCEPTANCE_SUMMARY_REPORT="$BUILD_DIR/acceptance_summary.json"' in script
    assert 'scripts/verify_cpp_build_evidence.py' in script
    assert 'scripts/write_acceptance_summary.py' in script


def test_robot_identity_service_uses_structured_default_model_contract() -> None:
    source = _read('spine_ultrasound_ui/services/robot_identity_service.py')
    assert 'self.default_model = normalized or XMATE3_IDENTITY.robot_model' in source
    assert 'model = (robot_model or self.default_model or XMATE3_IDENTITY.robot_model).strip().lower()' in source


def test_start_headless_script_delegates_default_backend_resolution_to_runtime_policy() -> None:
    script = _read('scripts/start_headless.sh')
    assert 'scripts/resolve_headless_backend.py' in script
    assert 'SPINE_HEADLESS_BACKEND' in script




def test_readme_and_profile_matrix_align_review_headless_policy() -> None:
    readme = _read('README.md')
    profile_matrix = _read('docs/04_profiles_and_release/PROFILE_MATRIX.md')
    runtime_policy = _read('spine_ultrasound_ui/services/runtime_mode_policy.py')
    assert 'headless 默认后端由 deployment profile 决定：`dev -> mock`，`review/lab/research/clinical -> core`；其中 `review` 仅允许在只读 evidence / replay / contract inspection 场景显式切到 `mock`。' in readme
    assert 'headless review may use `mock` **only** for read-only evidence / replay / contract inspection flows' in profile_matrix
    assert '"review": frozenset({"mock", "core"})' in runtime_policy
    assert '"review": "core"' in runtime_policy
def test_readme_documents_runtime_policy_backed_headless_resolution() -> None:
    readme = _read('README.md')
    assert 'runtime_mode_policy' in readme
    assert 'start_headless.sh' in readme


def test_verify_and_acceptance_critical_regression_batches_do_not_use_archive_wrapper_tests() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    acceptance_script = _read('scripts/final_acceptance_audit.sh')
    for disallowed in [
        'tests/test_api_contract.py',
        'tests/test_api_security.py',
        'tests/test_control_plane.py',
        'tests/test_headless_runtime.py',
        'tests/test_profile_policy.py',
        'tests/test_release_gate.py',
        'tests/test_replay_determinism.py',
        'tests/test_spawned_core_integration.py',
    ]:
        assert disallowed not in verify_script
        assert disallowed not in acceptance_script
        assert not Path(disallowed).exists()
    for required in [
        'tests/test_runtime_refactor_guards.py',
        'tests/test_backend_link_and_api_bridge.py',
        'tests/test_api_bridge_verdict_service.py',
        'tests/test_headless_adapter_surface_refactor.py',
        'tests/test_runtime_verdict_authority_contract.py',
        'tests/test_control_authority_claims.py',
        'tests/test_guidance_freeze_contracts.py',
        'tests/test_architecture_fitness.py',
    ]:
        assert required in verify_script
        assert required in acceptance_script
