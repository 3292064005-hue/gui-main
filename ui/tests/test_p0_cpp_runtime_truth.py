from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_command_server_uses_deadline_driven_periodic_loop() -> None:
    source = _read('cpp_robot_core/src/command_server.cpp')
    assert 'PeriodicLoopController' in source
    assert 'sleep_until' in source
    assert 'recordRtLoopSample' in source


def test_sdk_robot_facade_reports_contract_shell_vs_live_binding() -> None:
    header = _read('cpp_robot_core/include/robot_core/sdk_robot_facade.h')
    source = _read('cpp_robot_core/src/sdk_robot_facade_state.cpp')
    assert 'liveBindingEstablished' in header
    assert 'liveTakeoverReady' in header
    assert 'vendored_sdk_contract_shell' in source
    assert 'xcore_sdk_contract_shell' in source


def test_sdk_robot_facade_controlled_ports_are_available_to_runtime_services() -> None:
    header = _read('cpp_robot_core/include/robot_core/sdk_robot_facade.h')
    for required in (
        'using LifecyclePort = SdkRobotLifecyclePort;',
        'using QueryPort = SdkRobotQueryPort;',
        'using NrtExecutionPort = SdkRobotNrtExecutionPort;',
        'using RtControlPort = SdkRobotRtControlPort;',
        'using CollaborationPort = SdkRobotCollaborationPort;',
    ):
        assert required in header

    ports_source = _read('cpp_robot_core/src/sdk_robot_facade_ports.cpp')
    assert 'LifecyclePort& SdkRobotFacade::lifecyclePort()' in ports_source
    assert 'QueryPort& SdkRobotFacade::queryPort()' in ports_source
    assert 'NrtExecutionPort& SdkRobotFacade::nrtExecutionPort()' in ports_source
    assert 'RtControlPort& SdkRobotFacade::rtControlPort()' in ports_source
    assert 'CollaborationPort& SdkRobotFacade::collaborationPort()' in ports_source


def test_sdk_robot_facade_connect_does_not_report_contract_shell_success_after_live_bind_failure() -> None:
    source = _read('cpp_robot_core/src/sdk_robot_facade.cpp')
    assert 'contract_shell_connected_after_live_bind_failure' not in source
    assert 'binding_detail_ = "live_binding_failed"' in source
    catch_region_start = source.find('bool SdkRobotFacade::connect')
    assert catch_region_start >= 0
    connect_region = source[catch_region_start:source.find('void SdkRobotFacade::disconnect', catch_region_start)]
    assert 'return false;' in connect_region


def test_sdk_robot_facade_connect_missing_ip_branch_clears_live_binding_state() -> None:
    source = _read('cpp_robot_core/src/sdk_robot_facade.cpp')
    connect_start = source.find('bool SdkRobotFacade::connect')
    assert connect_start >= 0
    missing_branch_start = source.find('if (remote_ip.empty() || local_ip.empty())', connect_start)
    assert missing_branch_start >= 0
    missing_branch_end = source.find('#ifdef ROBOT_CORE_WITH_XCORE_SDK', missing_branch_start)
    missing_branch = source[missing_branch_start:missing_branch_end]
    assert 'robot_.reset();' in missing_branch
    assert 'rt_controller_.reset();' in missing_branch
    assert 'live_binding_established_ = false;' in missing_branch
    assert 'state_channel_ready_ = false;' in missing_branch
    assert 'aux_channel_ready_ = false;' in missing_branch
    assert 'motion_channel_ready_ = false;' in missing_branch
    assert 'network_healthy_ = false;' in missing_branch


def test_vendor_boundary_detail_does_not_overstate_non_live_readiness() -> None:
    source = _read('cpp_robot_core/src/core_runtime_contracts.cpp')
    assert 'real live binding/lifecycle readiness/exclusive-control evidence is not yet established' in source
    assert 'Vendor boundary owns SDK binding, lifecycle readiness, exclusive control and fixed-period RT semantics.' not in source


def test_sdk_robot_facade_strict_live_write_gate_blocks_contract_shell_mutations() -> None:
    header = _read('cpp_robot_core/include/robot_core/sdk_robot_facade.h')
    lifecycle = _read('cpp_robot_core/src/sdk_robot_facade_lifecycle.cpp')
    nrt = _read('cpp_robot_core/src/sdk_robot_facade_nrt.cpp')
    rt = _read('cpp_robot_core/src/sdk_robot_facade_rt.cpp')
    assert 'requireLiveWrite' in header
    assert 'live_binding_required' in _read('cpp_robot_core/src/sdk_robot_facade.cpp')
    for token in ('setPowerState', 'setOperateMode(auto)', 'setMotionControlMode(NrtCommand)', 'executeMoveAbsJ', 'beginRtMainline'):
        assert token in lifecycle + nrt + rt



def test_rt_purity_gate_requires_jitter_and_overrun_tokens() -> None:
    source = _read('scripts/check_rt_purity_gate.py')
    for token in (
        'runtime_.recordRtLoopSample(sample.period_ms, sample.execution_ms, sample.wake_jitter_ms, sample.overrun);',
        'rt_snapshot.overrun_count == 0',
        'std::abs(rt_snapshot.last_wake_jitter_ms) <= rt_snapshot.jitter_budget_ms',
        'field("overrun_count"',
        'field("jitter_budget_ms"',
        'field("current_period_ms"',
        'field("rt_quality_gate_passed"',
    ):
        assert token in source


def test_rt_quality_gate_requires_runtime_doctor_budget_blockers() -> None:
    source = _read('scripts/check_rt_quality_gate.py')
    for token in (
        'rt_cycle_overrun_detected',
        'rt_wake_jitter_budget_exceeded',
        'rt_cycle_budget_exceeded',
        'rt_quality_gate_failed',
        'current_period_ms',
        'rt_quality_gate_passed',
    ):
        assert token in source
