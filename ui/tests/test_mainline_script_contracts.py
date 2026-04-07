
from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_verify_mainline_uses_ephemeral_build_dir_and_phase_dispatch() -> None:
    script = _read('scripts/verify_mainline.sh')
    assert 'mktemp -d /tmp/gui_main_cpp_mainline_build.' in script
    assert 'rm -rf "${BUILD_DIR}"' in script
    assert 'VERIFY_PHASE="${VERIFY_PHASE:-all}"' in script
    assert 'case "${VERIFY_PHASE}" in' in script
    assert 'run_cpp_profile_gate mock' in script or 'run_cpp_profile_gate "mock"' in script
    assert 'python scripts/build_cpp_targets.py' in script
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
    assert 'python scripts/check_protocol_sync.py' in verify_script
    assert 'scripts/check_protocol_sync.py' in acceptance_script


def test_convergence_audit_expands_budgets_to_hotspot_files() -> None:
    script = _read('scripts/strict_convergence_audit.py')
    assert "'spine_ultrasound_ui/services/mock_core_runtime.py': 1800" in script
    assert "'cpp_robot_core/src/core_runtime.cpp': 1400" in script
    assert "'spine_ultrasound_ui/services/api_bridge_backend.py': 500" in script
    assert "'spine_ultrasound_ui/services/session_intelligence_service.py': 550" in script


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


def test_acceptance_audit_runs_hygiene_and_cpp_preflight_before_build() -> None:
    script = _read('scripts/final_acceptance_audit.sh')
    assert 'section "Repository hygiene"' in script
    assert './scripts/check_repo_hygiene.sh' in script
    assert 'section "C++ preflight"' in script
    assert './scripts/check_cpp_prereqs.sh' in script


def test_mainline_pytest_entrypoint_cleans_artifacts_with_bottom_up_walk() -> None:
    script = _read('scripts/run_pytest_mainline.py')
    assert 'os.walk(ROOT, topdown=False)' in script
    assert "dirname == '.pytest_cache'" in script or 'dirname == ".pytest_cache"' in script


def test_verify_and_acceptance_preclean_generated_python_artifacts_before_hygiene() -> None:
    verify_script = _read('scripts/verify_mainline.sh')
    acceptance_script = _read('scripts/final_acceptance_audit.sh')
    assert verify_script.index('cleanup_generated_artifacts') < verify_script.index('./scripts/check_repo_hygiene.sh')
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
    deployment = _read('DEPLOYMENT.md')
    assert './scripts/generate_dev_tls_cert.sh' in readme
    assert './scripts/generate_dev_tls_cert.sh' in deployment


def test_cpp_prereq_script_enforces_cmake_minimum_version() -> None:
    script = _read('scripts/check_cpp_prereqs.sh')
    assert "cmake>=3.24" in script
    assert "cmake --version" in script



def test_readme_and_deployment_document_current_runtime_version_policy() -> None:
    readme = _read('README.md')
    deployment = _read('DEPLOYMENT.md')
    requirements = _read('requirements.txt')
    assert "PySide6 >= 6.7" in readme
    assert "protobuf>=3.20.3,<8" in readme
    assert "PySide6>=6.7" in deployment
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
    for label in ['control-plane', 'release-state', 'repository-gates', 'archive-compat']:
        assert f'run_python_pytest_batch {label}' in verify_script
