from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_command_registry_uses_indexed_lookup_contract() -> None:
    header = _read('cpp_robot_core/include/robot_core/command_registry.h')
    source = _read('cpp_robot_core/src/command_registry.cpp')
    assert 'findCommandRegistryEntry' in header
    assert 'unordered_map' in source
    assert 'commandRegistryIndex' in source


def test_transport_and_runtime_buffers_are_bounded() -> None:
    proto = _read('spine_ultrasound_ui/services/protobuf_transport.py')
    transport = _read('spine_ultrasound_ui/services/core_transport.py')
    audit = _read('spine_ultrasound_ui/services/command_audit_service.py')
    robot_core_client = _read('spine_ultrasound_ui/services/robot_core_client.py')
    api_backend = _read('spine_ultrasound_ui/services/api_bridge_backend.py')
    assert 'MAX_FRAME_BYTES' in proto
    assert 'TCP_NODELAY' in transport
    assert 'deque(maxlen=RECENT_COMMAND_HISTORY_LIMIT)' in audit
    assert 'RECENT_TOPIC_LIMIT' in robot_core_client
    assert 'INITIAL_WS_RECONNECT_DELAY_S' in api_backend


def test_core_runtime_dispatch_uses_handler_registry() -> None:
    source = _read('cpp_robot_core/src/core_runtime.cpp')
    assert "command_handlers" in source
    assert "handler_it = command_handlers.find(command)" in source
    assert "handleConnectionCommand" in source
    assert "handleQueryCommand" in source
    assert "handleExecutionCommand" in source
    assert "commandCapabilityClaim" in source


def test_recording_service_decouples_rt_capture_from_flush() -> None:
    header = _read('cpp_robot_core/include/robot_core/recording_service.h')
    source = _read('cpp_robot_core/src/recording_service.cpp')
    assert "recordQueuedSample" in header
    assert "SPSCQueue" in header
    assert "recorder_thread_" in header
    assert "sample_queue_.try_enqueue" in source
    assert "recorderLoop" in source
    assert "stopWorker(true)" in source


def test_cpp_cmake_baseline_matches_readme_contract() -> None:
    readme = _read('README.md')
    cmake_lists = _read('cpp_robot_core/CMakeLists.txt')
    assert "CMake 3.24+" in readme
    assert "cmake_minimum_required(VERSION 3.24)" in cmake_lists
