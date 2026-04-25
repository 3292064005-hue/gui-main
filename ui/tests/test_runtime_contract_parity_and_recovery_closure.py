from __future__ import annotations

from pathlib import Path


ROOT = Path('.')


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding='utf-8')


def test_runtime_contract_parity_gate_is_wired_into_repo_scripts() -> None:
    source = _read('scripts/check_runtime_contract_parity.py')
    assert 'manifest/python command sets diverged' in source
    assert 'VALID_HANDLER_GROUPS' in source
    verify = _read('scripts/verify_mainline.sh')
    acceptance = _read('scripts/final_acceptance_audit.sh')
    assert 'scripts/check_runtime_contract_parity.py' in verify
    assert 'scripts/check_runtime_contract_parity.py' in acceptance


def test_safe_retreat_requires_completed_rt_retract_before_nrt_retreat() -> None:
    source = _read('cpp_robot_core/src/core_runtime_execution_commands.cpp')
    assert 'const auto rt_retract = self->procedure_executor_.rt_motion_service.controlledRetract();' in source
    assert 'if (!rt_retract.canProceedToNrtRetreat()) {' in source
    assert 'safe_retreat blocked before NRT retreat' in source
    assert 'self->procedure_executor_.nrt_motion_service.safeRetreat(&reason)' in source


def test_runtime_state_store_blocks_recovery_chain_on_incomplete_rt_retract() -> None:
    source = _read('cpp_robot_core/src/runtime_state_store.cpp')
    assert 'const auto rt_retract = procedure_executor_.rt_motion_service.controlledRetract();' in source
    assert 'CONTROLLED_RETRACT_INCOMPLETE' in source
    assert 'RT受控回撤未完成，已阻断后续恢复链' in source


def test_unified_mainline_launcher_wraps_prod_and_headless_entrypoints() -> None:
    start_mainline = _read('scripts/start_mainline.py')
    start_prod = _read('scripts/start_prod.sh')
    start_headless = _read('scripts/start_headless.sh')
    assert 'Unified operator-facing launcher' in start_mainline
    assert 'doctor_runtime.py' in start_mainline
    assert 'cmake -S' not in start_prod
    assert 'start_mainline.py' in start_prod
    assert 'start_mainline.py' in start_headless


def test_generated_runtime_dispatcher_and_registry_close_p1_and_p0_contracts() -> None:
    dispatcher = _read('cpp_robot_core/src/core_runtime_dispatcher.cpp')
    registry = _read('cpp_robot_core/src/command_registry.cpp')
    runtime = _read('cpp_robot_core/src/core_runtime.cpp')
    assert 'resolveHandler' in dispatcher
    assert 'validateRuntimeCommandGuard' in dispatcher
    assert 'dispatchTypedCommand(invocation)' in dispatcher
    assert 'return dispatch_with_contract(owner_.lanes_.command)' in dispatcher
    assert 'return dispatch_with_contract(owner_.lanes_.query)' in dispatcher
    assert 'return dispatch_with_contract(owner_.lanes_.rt)' in dispatcher
    assert 'commandRegistry()' in registry
    assert 'findCommandRegistryEntry' in registry
    assert 'commandAllowedInState' in registry
    assert 'runtime_dispatcher_->handleCommandJson(line)' in runtime


def test_runtime_authority_and_verdict_queries_are_runtime_sourced() -> None:
    backend_base = _read('spine_ultrasound_ui/services/backend_base.py')
    direct_backend = _read('spine_ultrasound_ui/services/robot_core_client.py')
    api_backend = _read('spine_ultrasound_ui/services/api_bridge_backend.py')
    assert 'resolve_authoritative_runtime_envelope' in backend_base
    assert 'resolve_control_authority' in backend_base
    assert 'resolve_final_verdict' in backend_base
    assert 'RobotCoreVerdictService' in direct_backend
    assert 'ApiBridgeVerdictService' in api_backend
    assert 'BackendAuthoritativeContractService' in direct_backend
    assert 'BackendAuthoritativeContractService' in api_backend


def test_xmate_model_compile_gate_is_profile_aware() -> None:
    cmake = _read('cpp_robot_core/CMakeLists.txt')
    verify = _read('scripts/verify_mainline.sh')
    acceptance = _read('scripts/final_acceptance_audit.sh')
    assert 'ROBOT_CORE_ENABLE_XMATE_MODEL_COMPILE_GATE' in cmake
    assert 'if(ROBOT_CORE_WITH_XCORE_SDK AND ROBOT_CORE_WITH_XMATE_MODEL AND VendoredRokaeSdk_FOUND AND TARGET Rokae::xMateModel)' in cmake
    assert 'cpp_test_targets_for_profile()' in verify
    assert 'cpp_test_targets_for_profile()' in acceptance
    assert 'test_xmate_model_compile_contract' in verify
    assert 'test_xmate_model_compile_contract' in acceptance


def test_backend_error_taxonomy_and_command_error_service_are_canonical() -> None:
    backend_errors = _read('spine_ultrasound_ui/services/backend_errors.py')
    error_service = _read('spine_ultrasound_ui/services/backend_command_error_service.py')
    direct_backend = _read('spine_ultrasound_ui/services/robot_core_client.py')
    api_backend = _read('spine_ultrasound_ui/services/api_bridge_backend.py')
    for token in [
        'LeaseConflictError',
        'ProfilePolicyError',
        'SchemaMismatchError',
        'RuntimeRejectedError',
        'TransportError',
        'TransportTimeoutError',
        'DependencyFailureError',
    ]:
        assert token in backend_errors
    assert 'normalize_backend_exception' in error_service
    assert 'BackendCommandErrorService.build_reply' in direct_backend
    assert 'BackendCommandErrorService.build_reply' in api_backend
