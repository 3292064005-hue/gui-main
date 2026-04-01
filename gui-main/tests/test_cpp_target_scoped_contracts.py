from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_cmake_exports_runtime_usage_requirements_and_test_support() -> None:
    cmake = _read('cpp_robot_core/CMakeLists.txt')
    assert 'add_library(robot_core_test_support INTERFACE)' in cmake
    assert 'target_link_libraries(spine_robot_core_runtime\n  PUBLIC' in cmake
    assert 'robot_core_build_settings' in cmake
    assert 'robot_core_proto_deps' in cmake
    assert 'robot_core_sdk_binding' in cmake



def test_cpp_tests_use_target_scoped_helper_instead_of_manual_include_plumbing() -> None:
    cmake = _read('cpp_robot_core/CMakeLists.txt')
    for target in (
        'test_seqlock',
        'test_force_control',
        'test_impedance_scan',
        'test_protocol_bridge',
        'test_recovery_manager',
    ):
        assert f'robot_core_add_cpp_test({target} ' in cmake
