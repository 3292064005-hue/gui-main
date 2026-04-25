from __future__ import annotations

import json
from pathlib import Path

from spine_ultrasound_ui.services.ipc_protocol import protocol_schema
from spine_ultrasound_ui.services.runtime_command_contracts import contract_for, export_contract_document
from spine_ultrasound_ui.services.runtime_payload_validator import validate_command_payload


def test_runtime_command_contract_exposes_typed_fields() -> None:
    contract = contract_for('validate_scan_plan')
    field_names = {field.name for field in contract.fields}
    assert {'scan_plan', 'config_snapshot'} <= field_names
    scan_plan_field = next(field for field in contract.fields if field.name == 'scan_plan')
    assert scan_plan_field.required is True
    assert scan_plan_field.field_type == 'object'
    assert 'plan_id' in scan_plan_field.nested_required_fields


def test_protocol_schema_exposes_typed_command_contracts() -> None:
    schema = protocol_schema()
    assert 'command_contracts' in schema
    commands = {item['name']: item for item in schema['command_contracts']['commands']}
    assert 'validate_scan_plan' in commands
    assert commands['validate_scan_plan']['capability_claim'] == 'plan_compile'


def test_generated_runtime_command_contracts_match_export_surface() -> None:
    generated = json.loads(Path('spine_ultrasound_ui/contracts/generated/runtime_command_contracts.json').read_text(encoding='utf-8'))
    assert generated == export_contract_document()


def test_runtime_payload_validator_uses_typed_nested_field_contracts() -> None:
    try:
        validate_command_payload('validate_scan_plan', {'scan_plan': {'segments': []}})
    except ValueError as exc:
        assert "missing required fields" in str(exc)
    else:
        raise AssertionError('validate_scan_plan without typed nested plan_id should fail')


def test_runtime_command_contracts_expose_response_and_guard_contracts() -> None:
    contract = contract_for('validate_scan_plan')
    assert contract.request_contract.required_fields == ('scan_plan',)
    assert contract.response_contract.data_contract_token == 'final_verdict'
    assert 'final_verdict' in contract.response_contract.data_required_fields
    response_fields = {field.name: field for field in contract.response_contract.data_fields}
    assert response_fields['final_verdict'].field_type == 'object'
    assert 'accepted' in response_fields['final_verdict'].nested_required_fields
    assert contract.guard_contract.lane == 'query'
    assert 'AUTO_READY' in contract.guard_contract.allowed_states


def test_generated_cpp_typed_runtime_command_contracts_exist() -> None:
    generated = Path('cpp_robot_core/include/robot_core/generated_runtime_command_contracts.inc').read_text(encoding='utf-8')
    assert 'RuntimeCommandResponseContract' in generated
    assert 'RuntimeCommandGuardContract' in generated
    assert 'validate_scan_plan' in generated



def test_cpp_dispatcher_enforces_guard_and_reply_contracts() -> None:
    source = Path('cpp_robot_core/src/core_runtime_dispatcher.cpp').read_text(encoding='utf-8')
    assert 'validateRuntimeCommandGuard' in source
    assert 'validateRuntimeCommandReplyEnvelope' in source


def test_cpp_typed_runtime_contract_surface_exposes_guard_and_reply_validation_apis() -> None:
    header = Path('cpp_robot_core/include/robot_core/runtime_command_contracts.h').read_text(encoding='utf-8')
    source = Path('cpp_robot_core/src/runtime_command_contracts.cpp').read_text(encoding='utf-8')
    for required in (
        'validateRuntimeCommandGuard',
        'validateRuntimeCommandReplyEnvelope',
        'commandRegistryStateName',
    ):
        assert required in header or required in source



def test_cpp_runtime_handlers_consume_typed_invocation_surface() -> None:
    header = Path('cpp_robot_core/include/robot_core/core_runtime.h').read_text(encoding='utf-8')
    dispatcher_header = Path('cpp_robot_core/include/robot_core/core_runtime_dispatcher.h').read_text(encoding='utf-8')
    source = Path('cpp_robot_core/src/core_runtime_dispatcher.cpp').read_text(encoding='utf-8')
    adapters = Path('cpp_robot_core/include/robot_core/generated_runtime_command_typed_handlers.inc').read_text(encoding='utf-8')
    assert 'RuntimeCommandInvocation' in header
    assert 'handleConnectionCommand(const RuntimeCommandInvocation& invocation)' in header
    assert 'handleExecutionCommand(const RuntimeCommandInvocation& invocation)' in header
    assert 'template <typename RequestT>' in header
    assert 'handleTypedCommand(const RuntimeCommandContext& context, const RequestT& request)' in header
    assert 'using CommandHandler = std::string (CoreRuntime::*)(const RuntimeCommandInvocation&);' in dispatcher_header
    assert 'buildRuntimeCommandInvocation(line, &invocation, &payload_error)' in source
    assert 'dispatchTypedCommand(invocation)' in source
    assert 'handleTypedCommand<ConnectRobotRequest>' in adapters


def test_runtime_command_contracts_capture_optional_typed_request_fields() -> None:
    connect = contract_for('connect_robot')
    connect_types = {field.name: field.field_type for field in connect.fields}
    assert connect_types['remote_ip'] == 'string'
    assert connect_types['local_ip'] == 'string'
    replay = contract_for('replay_path')
    replay_types = {field.name: field.field_type for field in replay.fields}
    assert replay_types['name'] == 'string'
    assert replay_types['rate'] == 'double'
    record = contract_for('start_record_path')
    record_types = {field.name: field.field_type for field in record.fields}
    assert record_types['duration_s'] == 'integer'


def test_cpp_runtime_handlers_no_longer_parse_payload_json_directly() -> None:
    session_exec = Path('cpp_robot_core/src/core_runtime_session_commands.cpp').read_text(encoding='utf-8')
    power_validation = Path('cpp_robot_core/src/core_runtime_power_validation.cpp').read_text(encoding='utf-8')
    core_runtime = Path('cpp_robot_core/src/core_runtime.cpp').read_text(encoding='utf-8')
    assert 'payload_json' not in session_exec
    assert 'payload_json' not in power_validation
    assert 'payload_json' not in core_runtime


def test_cpp_runtime_contract_surface_exposes_runtime_command_request_struct() -> None:
    header = Path('cpp_robot_core/include/robot_core/runtime_command_contracts.h').read_text(encoding='utf-8')
    assert 'struct RuntimeCommandRequest' in header
    assert 'intField(const std::string& name, int fallback = 0) const;' in header
    assert 'doubleField(const std::string& name, double fallback = 0.0) const;' in header


def test_generated_cpp_typed_request_family_exists() -> None:
    header = Path('cpp_robot_core/include/robot_core/generated_runtime_command_request_types.h').read_text(encoding='utf-8')
    parsers = Path('cpp_robot_core/include/robot_core/generated_runtime_command_request_parsers.inc').read_text(encoding='utf-8')
    contracts_header = Path('cpp_robot_core/include/robot_core/runtime_command_contracts.h').read_text(encoding='utf-8')
    assert 'using RuntimeTypedRequestVariant = std::variant<' in header
    for required in ('ConnectRobotRequest', 'ValidateScanPlanRequest', 'LockSessionRequest', 'RunRlProjectRequest'):
        assert required in header
    for required in ('if (command == "connect_robot")', 'if (command == "lock_session")', 'if (command == "validate_scan_plan")'):
        assert required in parsers
    assert 'RuntimeTypedRequestVariant typed_request;' in contracts_header
    assert 'buildTypedRuntimeCommandRequest' in contracts_header


def test_cpp_runtime_handlers_resolve_generated_typed_requests_instead_of_generic_field_reads() -> None:
    for rel in (
        'cpp_robot_core/src/core_runtime.cpp',
        'cpp_robot_core/src/core_runtime_power_validation.cpp',
        'cpp_robot_core/src/core_runtime_session_commands.cpp',
        'cpp_robot_core/src/core_runtime_execution_commands.cpp',
    ):
        source = Path(rel).read_text(encoding='utf-8')
        assert 'requestAs<' in source
        assert '.stringField(' not in source
        assert '.objectFieldJson(' not in source
        assert '.intField(' not in source
        assert '.doubleField(' not in source


def test_cpp_reply_contracts_enforce_required_data_fields() -> None:
    generated = Path('cpp_robot_core/include/robot_core/generated_runtime_command_contracts.inc').read_text(encoding='utf-8')
    source = Path('cpp_robot_core/src/runtime_command_contracts.cpp').read_text(encoding='utf-8')
    assert 'RuntimeCommandResponseContract{"query_controller_log", "controller_log", "logs", {' in generated
    assert 'data_required_fields_signature' in source
    assert 'reply data missing required field' in source
    assert 'reply data field validation failed for' in source


def test_generated_cpp_typed_handler_family_exists() -> None:
    decls = Path('cpp_robot_core/include/robot_core/generated_runtime_command_typed_handler_decls.inc').read_text(encoding='utf-8')
    adapters = Path('cpp_robot_core/include/robot_core/generated_runtime_command_typed_handlers.inc').read_text(encoding='utf-8')
    for required in ('handleTypedCommand<ConnectRobotRequest>', 'handleTypedCommand<LockSessionRequest>', 'handleTypedCommand<ValidateScanPlanRequest>'):
        assert required in adapters
    for required in ('handleConnectRobotTyped', 'handleLockSessionTyped', 'handleValidateScanPlanTyped'):
        assert required in decls
        assert required in adapters
    assert 'return handleConnectRobotTyped(context, request);' in adapters
    assert 'return handleLockSessionTyped(context, request);' in adapters
    assert 'return handleValidateScanPlanTyped(context, request);' in adapters


def test_rt_quality_observed_fixture_exists_and_contains_loop_samples() -> None:
    observed = json.loads(Path('artifacts/verification/current_delivery_fix/rt_quality_observed.json').read_text(encoding='utf-8'))
    assert observed['rt_quality_gate_passed'] is True
    assert observed['fixed_period_enforced'] is True
    assert len(observed['loop_samples']) >= 1
    assert all(sample['overrun'] is False for sample in observed['loop_samples'])


def test_write_and_plan_compile_commands_expose_command_context_contract() -> None:
    start_procedure = contract_for('start_procedure')
    compile_plan = contract_for('validate_scan_plan')
    start_fields = {field.name: field for field in start_procedure.request_contract.fields}
    compile_fields = {field.name: field for field in compile_plan.request_contract.fields}
    assert '_command_context' in start_fields
    assert start_fields['_command_context'].field_type == 'object'
    assert '_command_context' in compile_fields
    assert compile_fields['_command_context'].field_type == 'object'

