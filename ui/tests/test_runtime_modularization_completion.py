from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_sdk_robot_facade_ports_are_top_level_modules() -> None:
    header = _read("cpp_robot_core/include/robot_core/sdk_robot_facade.h")
    assert "class LifecyclePort" not in header
    assert "class SdkRobotLifecyclePort" in header
    assert "class SdkRobotRtControlPort" in header
    assert "std::unique_ptr<SdkRobotLifecyclePort>" in header


def test_core_runtime_dispatcher_and_contract_publisher_are_externalized() -> None:
    header = _read("cpp_robot_core/include/robot_core/core_runtime.h")
    dispatcher = _read("cpp_robot_core/src/core_runtime_dispatcher.cpp")
    publisher = _read("cpp_robot_core/src/core_runtime_contract_publisher.cpp")
    assert "RuntimeDispatcherAdapter" not in header
    assert "RuntimeContractPublisherAdapter" not in header
    assert "class CoreRuntimeDispatcher" in header
    assert "class CoreRuntimeContractPublisher" in header
    assert "commandHandlerGroup" in dispatcher
    assert "state_mutex_" in publisher


def test_recording_consumers_materialize_derived_outputs() -> None:
    source = _read("cpp_robot_core/src/recording_service.cpp")
    assert "materializeConsumerArtifacts" in source
    assert "telemetry_replay_index.json" in source
    assert "alarm_review_index.json" in source
    assert "audit_timeline_index.json" in source
