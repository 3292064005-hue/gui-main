// Generated from schemas/runtime_command_manifest.json via runtime_command_contracts.py. Do not edit manually.

      {"acquire_control_lease", RuntimeCommandRequestContract{"acquire_control_lease", {
          {"actor_id", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"intent_reason", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"lease_id", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"preempt", false, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"preempt_reason", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"profile", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"requested_claims", false, RuntimeContractFieldType::Array, "", RuntimeContractFieldType::Any, ""},
          {"role", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"session_id", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"source", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"ttl_s", false, RuntimeContractFieldType::Integer, "", RuntimeContractFieldType::Any, ""},
          {"workspace", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"acquire_control_lease", "control_authority", "summary_state|detail|lease", {
          {"summary_state", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"lease", true, RuntimeContractFieldType::Object, "lease_id|actor_id|workspace|role", RuntimeContractFieldType::Any, ""},
          {"control_authority", false, RuntimeContractFieldType::Object, "summary_state|detail", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"acquire_control_lease", "*", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"acquire_control_lease", "acquire_control_lease", "handleSessionCommand"}},
      {"approach_prescan", RuntimeCommandRequestContract{"approach_prescan", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"approach_prescan", "rt_command_ack", "rt_command_ack", {
          {"rt_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"approach_prescan", "PATH_VALIDATED", CommandRuntimeLane::RtControl}, RuntimeCommandDispatchContract{"approach_prescan", "approach_prescan", "handleExecutionCommand"}},
      {"cancel_record_path", RuntimeCommandRequestContract{"cancel_record_path", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"cancel_record_path", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"cancel_record_path", "CONNECTED", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"cancel_record_path", "cancel_record_path", "handleExecutionCommand"}},
      {"clear_fault", RuntimeCommandRequestContract{"clear_fault", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"clear_fault", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"clear_fault", "FAULT", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"clear_fault", "clear_fault", "handleExecutionCommand"}},
      {"clear_injected_faults", RuntimeCommandRequestContract{"clear_injected_faults", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"clear_injected_faults", "command_ack", "command_ack", {
          {"command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"clear_injected_faults", "*", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"clear_injected_faults", "clear_injected_faults", "handleFaultInjectionCommand"}},
      {"compile_scan_plan", RuntimeCommandRequestContract{"compile_scan_plan", {
          {"config_snapshot", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"scan_plan", true, RuntimeContractFieldType::Object, "plan_id|segments|plan_hash", RuntimeContractFieldType::Any, ""},
          {"scan_plan_hash", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"compile_scan_plan", "final_verdict", "final_verdict", {
          {"final_verdict", true, RuntimeContractFieldType::Object, "accepted|authoritative|reason", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"compile_scan_plan", "AUTO_READY|SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"compile_scan_plan", "validate_scan_plan", "handleValidationCommand"}},
      {"connect_robot", RuntimeCommandRequestContract{"connect_robot", {
          {"local_ip", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"remote_ip", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"connect_robot", "command_ack", "command_ack", {
          {"command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"connect_robot", "BOOT|DISCONNECTED", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"connect_robot", "connect_robot", "handleConnectionCommand"}},
      {"disable_drag", RuntimeCommandRequestContract{"disable_drag", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"disable_drag", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"disable_drag", "CONNECTED", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"disable_drag", "disable_drag", "handleExecutionCommand"}},
      {"disconnect_robot", RuntimeCommandRequestContract{"disconnect_robot", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"disconnect_robot", "command_ack", "command_ack", {
          {"command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"disconnect_robot", "BOOT|DISCONNECTED|CONNECTED|POWERED|AUTO_READY|FAULT|ESTOP", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"disconnect_robot", "disconnect_robot", "handleConnectionCommand"}},
      {"emergency_stop", RuntimeCommandRequestContract{"emergency_stop", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"emergency_stop", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"emergency_stop", "*", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"emergency_stop", "emergency_stop", "handleExecutionCommand"}},
      {"enable_drag", RuntimeCommandRequestContract{"enable_drag", {
          {"space", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"type", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"enable_drag", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"enable_drag", "CONNECTED", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"enable_drag", "enable_drag", "handleExecutionCommand"}},
      {"get_authoritative_runtime_envelope", RuntimeCommandRequestContract{"get_authoritative_runtime_envelope", {
        }}, RuntimeCommandResponseContract{"get_authoritative_runtime_envelope", "authoritative_runtime_envelope", "authoritative_runtime_envelope_present|control_authority|final_verdict", {
          {"authoritative_runtime_envelope_present", true, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"control_authority", true, RuntimeContractFieldType::Object, "summary_state|detail", RuntimeContractFieldType::Any, ""},
          {"final_verdict", true, RuntimeContractFieldType::Object, "accepted|authoritative|reason", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_authoritative_runtime_envelope", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_authoritative_runtime_envelope", "get_authoritative_runtime_envelope", "handleQueryCommand"}},
      {"get_capability_contract", RuntimeCommandRequestContract{"get_capability_contract", {
        }}, RuntimeCommandResponseContract{"get_capability_contract", "capability_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_capability_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_capability_contract", "get_capability_contract", "handleQueryCommand"}},
      {"get_clinical_mainline_contract", RuntimeCommandRequestContract{"get_clinical_mainline_contract", {
        }}, RuntimeCommandResponseContract{"get_clinical_mainline_contract", "clinical_mainline_contract", "robot_model|clinical_mainline_mode|required_sequence", {
          {"robot_model", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"clinical_mainline_mode", true, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"required_sequence", true, RuntimeContractFieldType::Array, "", RuntimeContractFieldType::String, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_clinical_mainline_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_clinical_mainline_contract", "get_clinical_mainline_contract", "handleQueryCommand"}},
      {"get_control_governance_contract", RuntimeCommandRequestContract{"get_control_governance_contract", {
        }}, RuntimeCommandResponseContract{"get_control_governance_contract", "control_governance_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_control_governance_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_control_governance_contract", "get_control_governance_contract", "handleQueryCommand"}},
      {"get_controller_evidence", RuntimeCommandRequestContract{"get_controller_evidence", {
        }}, RuntimeCommandResponseContract{"get_controller_evidence", "controller_evidence", "runtime_source|last_event|last_transition", {
          {"runtime_source", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"last_event", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"last_transition", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_controller_evidence", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_controller_evidence", "get_controller_evidence", "handleQueryCommand"}},
      {"get_deployment_contract", RuntimeCommandRequestContract{"get_deployment_contract", {
        }}, RuntimeCommandResponseContract{"get_deployment_contract", "deployment_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_deployment_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_deployment_contract", "get_deployment_contract", "handleQueryCommand"}},
      {"get_dual_state_machine_contract", RuntimeCommandRequestContract{"get_dual_state_machine_contract", {
        }}, RuntimeCommandResponseContract{"get_dual_state_machine_contract", "dual_state_machine_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_dual_state_machine_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_dual_state_machine_contract", "get_dual_state_machine_contract", "handleQueryCommand"}},
      {"get_fault_injection_contract", RuntimeCommandRequestContract{"get_fault_injection_contract", {
        }}, RuntimeCommandResponseContract{"get_fault_injection_contract", "fault_injection_contract", "summary_state|detail|active_faults", {
          {"summary_state", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"active_faults", true, RuntimeContractFieldType::Array, "", RuntimeContractFieldType::String, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_fault_injection_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_fault_injection_contract", "get_fault_injection_contract", "handleQueryCommand"}},
      {"get_hardware_lifecycle_contract", RuntimeCommandRequestContract{"get_hardware_lifecycle_contract", {
        }}, RuntimeCommandResponseContract{"get_hardware_lifecycle_contract", "hardware_lifecycle_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_hardware_lifecycle_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_hardware_lifecycle_contract", "get_hardware_lifecycle_contract", "handleQueryCommand"}},
      {"get_identity_contract", RuntimeCommandRequestContract{"get_identity_contract", {
        }}, RuntimeCommandResponseContract{"get_identity_contract", "identity_contract", "robot_model|sdk_robot_class|axis_count", {
          {"robot_model", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"sdk_robot_class", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"axis_count", true, RuntimeContractFieldType::Integer, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_identity_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_identity_contract", "get_identity_contract", "handleQueryCommand"}},
      {"get_io_snapshot", RuntimeCommandRequestContract{"get_io_snapshot", {
        }}, RuntimeCommandResponseContract{"get_io_snapshot", "io_snapshot", "di|do|ai|ao|registers|xpanel_vout_mode", {
          {"di", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"do", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"ai", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"ao", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"registers", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"xpanel_vout_mode", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_io_snapshot", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_io_snapshot", "get_io_snapshot", "handleQueryCommand"}},
      {"get_mainline_executor_contract", RuntimeCommandRequestContract{"get_mainline_executor_contract", {
        }}, RuntimeCommandResponseContract{"get_mainline_executor_contract", "mainline_executor_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_mainline_executor_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_mainline_executor_contract", "get_mainline_executor_contract", "handleQueryCommand"}},
      {"get_model_authority_contract", RuntimeCommandRequestContract{"get_model_authority_contract", {
        }}, RuntimeCommandResponseContract{"get_model_authority_contract", "model_authority_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_model_authority_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_model_authority_contract", "get_model_authority_contract", "handleQueryCommand"}},
      {"get_motion_contract", RuntimeCommandRequestContract{"get_motion_contract", {
        }}, RuntimeCommandResponseContract{"get_motion_contract", "motion_contract", "rt_mode|sdk_boundary_units|rt_contract|nrt_contract", {
          {"rt_mode", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"sdk_boundary_units", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"rt_contract", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"nrt_contract", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_motion_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_motion_contract", "get_motion_contract", "handleQueryCommand"}},
      {"get_recovery_contract", RuntimeCommandRequestContract{"get_recovery_contract", {
        }}, RuntimeCommandResponseContract{"get_recovery_contract", "recovery_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_recovery_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_recovery_contract", "get_recovery_contract", "handleQueryCommand"}},
      {"get_register_snapshot", RuntimeCommandRequestContract{"get_register_snapshot", {
        }}, RuntimeCommandResponseContract{"get_register_snapshot", "register_snapshot", "registers", {
          {"registers", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_register_snapshot", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_register_snapshot", "get_register_snapshot", "handleQueryCommand"}},
      {"get_release_contract", RuntimeCommandRequestContract{"get_release_contract", {
        }}, RuntimeCommandResponseContract{"get_release_contract", "release_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_release_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_release_contract", "get_release_contract", "handleQueryCommand"}},
      {"get_robot_family_contract", RuntimeCommandRequestContract{"get_robot_family_contract", {
        }}, RuntimeCommandResponseContract{"get_robot_family_contract", "robot_family_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_robot_family_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_robot_family_contract", "get_robot_family_contract", "handleQueryCommand"}},
      {"get_rt_kernel_contract", RuntimeCommandRequestContract{"get_rt_kernel_contract", {
        }}, RuntimeCommandResponseContract{"get_rt_kernel_contract", "rt_kernel_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_rt_kernel_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_rt_kernel_contract", "get_rt_kernel_contract", "handleQueryCommand"}},
      {"get_runtime_alignment", RuntimeCommandRequestContract{"get_runtime_alignment", {
        }}, RuntimeCommandResponseContract{"get_runtime_alignment", "runtime_alignment", "runtime_source|sdk_available|robot_family", {
          {"runtime_source", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"sdk_available", true, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"robot_family", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_runtime_alignment", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_runtime_alignment", "get_runtime_alignment", "handleQueryCommand"}},
      {"get_safety_config", RuntimeCommandRequestContract{"get_safety_config", {
        }}, RuntimeCommandResponseContract{"get_safety_config", "safety_config", "collision_detection_enabled|soft_limit_enabled", {
          {"collision_detection_enabled", true, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"soft_limit_enabled", true, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_safety_config", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_safety_config", "get_safety_config", "handleQueryCommand"}},
      {"get_safety_recovery_contract", RuntimeCommandRequestContract{"get_safety_recovery_contract", {
        }}, RuntimeCommandResponseContract{"get_safety_recovery_contract", "safety_recovery_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_safety_recovery_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_safety_recovery_contract", "get_safety_recovery_contract", "handleQueryCommand"}},
      {"get_sdk_runtime_config", RuntimeCommandRequestContract{"get_sdk_runtime_config", {
        }}, RuntimeCommandResponseContract{"get_sdk_runtime_config", "sdk_runtime_config", "remote_ip|local_ip|rt_mode|runtime_config_contract_digest|runtime_config_schema_version|rt_phase_contract", {
          {"remote_ip", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"local_ip", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"rt_mode", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"runtime_config_contract_digest", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"runtime_config_schema_version", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"rt_phase_contract", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_sdk_runtime_config", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_sdk_runtime_config", "get_sdk_runtime_config", "handleQueryCommand"}},
      {"get_session_drift_contract", RuntimeCommandRequestContract{"get_session_drift_contract", {
        }}, RuntimeCommandResponseContract{"get_session_drift_contract", "session_drift_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_session_drift_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_session_drift_contract", "get_session_drift_contract", "handleQueryCommand"}},
      {"get_session_freeze", RuntimeCommandRequestContract{"get_session_freeze", {
        }}, RuntimeCommandResponseContract{"get_session_freeze", "session_freeze", "session_locked|session_id|plan_hash|freeze_consistent|strict_runtime_freeze_gate", {
          {"session_locked", true, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"session_id", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"plan_hash", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"freeze_consistent", true, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"strict_runtime_freeze_gate", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"session_freeze_policy", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"frozen_execution_critical_fields", false, RuntimeContractFieldType::Array, "", RuntimeContractFieldType::String, ""},
          {"frozen_evidence_only_fields", false, RuntimeContractFieldType::Array, "", RuntimeContractFieldType::String, ""},
          {"recheck_on_start_procedure", false, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"live_binding_established", false, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"control_source_exclusive", false, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"network_healthy", false, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_session_freeze", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_session_freeze", "get_session_freeze", "handleQueryCommand"}},
      {"get_vendor_boundary_contract", RuntimeCommandRequestContract{"get_vendor_boundary_contract", {
        }}, RuntimeCommandResponseContract{"get_vendor_boundary_contract", "vendor_boundary_contract", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_vendor_boundary_contract", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_vendor_boundary_contract", "get_vendor_boundary_contract", "handleQueryCommand"}},
      {"get_xmate_model_summary", RuntimeCommandRequestContract{"get_xmate_model_summary", {
        }}, RuntimeCommandResponseContract{"get_xmate_model_summary", "xmate_model_summary", "model_source|kinematics_ready|dynamics_ready", {
          {"model_source", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"kinematics_ready", true, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""},
          {"dynamics_ready", true, RuntimeContractFieldType::Boolean, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"get_xmate_model_summary", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"get_xmate_model_summary", "get_xmate_model_summary", "handleQueryCommand"}},
      {"go_home", RuntimeCommandRequestContract{"go_home", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"go_home", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"go_home", "CONNECTED|POWERED|AUTO_READY|PATH_VALIDATED|SCAN_COMPLETE|SEGMENT_ABORTED|PLAN_ABORTED", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"go_home", "go_home", "handleExecutionCommand"}},
      {"inject_fault", RuntimeCommandRequestContract{"inject_fault", {
          {"fault_name", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"inject_fault", "command_ack", "command_ack", {
          {"command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"inject_fault", "*", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"inject_fault", "inject_fault", "handleFaultInjectionCommand"}},
      {"load_scan_plan", RuntimeCommandRequestContract{"load_scan_plan", {
          {"scan_plan", true, RuntimeContractFieldType::Object, "plan_id|segments", RuntimeContractFieldType::Any, ""},
          {"scan_plan_hash", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"load_scan_plan", "session_command_ack", "session_command_ack", {
          {"session_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"load_scan_plan", "SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"load_scan_plan", "load_scan_plan", "handleSessionCommand"}},
      {"lock_session", RuntimeCommandRequestContract{"lock_session", {
          {"build_id", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"config_snapshot", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"device_health_snapshot", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"device_roster", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"force_sensor_provider", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"protocol_version", false, RuntimeContractFieldType::Integer, "", RuntimeContractFieldType::Any, ""},
          {"safety_thresholds", true, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"scan_plan_hash", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"session_dir", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"session_freeze_policy", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"session_id", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"software_version", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"strict_runtime_freeze_gate", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"lock_session", "session_command_ack", "session_command_ack", {
          {"session_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"lock_session", "AUTO_READY", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"lock_session", "lock_session", "handleSessionCommand"}},
      {"pause_rl_project", RuntimeCommandRequestContract{"pause_rl_project", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"pause_rl_project", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"pause_rl_project", "AUTO_READY|SCANNING|PAUSED_HOLD|SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"pause_rl_project", "pause_rl_project", "handleExecutionCommand"}},
      {"pause_scan", RuntimeCommandRequestContract{"pause_scan", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"pause_scan", "rt_command_ack", "rt_command_ack", {
          {"rt_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"pause_scan", "SCANNING", CommandRuntimeLane::RtControl}, RuntimeCommandDispatchContract{"pause_scan", "pause_scan", "handleExecutionCommand"}},
      {"power_off", RuntimeCommandRequestContract{"power_off", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"power_off", "command_ack", "command_ack", {
          {"command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"power_off", "CONNECTED|POWERED|AUTO_READY|SESSION_LOCKED|PATH_VALIDATED", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"power_off", "power_off", "handlePowerModeCommand"}},
      {"power_on", RuntimeCommandRequestContract{"power_on", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"power_on", "command_ack", "command_ack", {
          {"command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"power_on", "CONNECTED|POWERED|AUTO_READY", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"power_on", "power_on", "handlePowerModeCommand"}},
      {"query_controller_log", RuntimeCommandRequestContract{"query_controller_log", {
        }}, RuntimeCommandResponseContract{"query_controller_log", "controller_log", "logs", {
          {"logs", true, RuntimeContractFieldType::Array, "", RuntimeContractFieldType::Object, "level|source|message"}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"query_controller_log", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"query_controller_log", "query_controller_log", "handleQueryCommand"}},
      {"query_final_verdict", RuntimeCommandRequestContract{"query_final_verdict", {
        }}, RuntimeCommandResponseContract{"query_final_verdict", "final_verdict", "final_verdict", {
          {"final_verdict", true, RuntimeContractFieldType::Object, "accepted|authoritative|reason", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"query_final_verdict", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"query_final_verdict", "query_final_verdict", "handleValidationCommand"}},
      {"query_path_lists", RuntimeCommandRequestContract{"query_path_lists", {
        }}, RuntimeCommandResponseContract{"query_path_lists", "path_lists", "paths|drag", {
          {"paths", true, RuntimeContractFieldType::Array, "", RuntimeContractFieldType::Object, "name|rate|points"},
          {"drag", true, RuntimeContractFieldType::Object, "enabled|space|type", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"query_path_lists", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"query_path_lists", "query_path_lists", "handleQueryCommand"}},
      {"query_rl_projects", RuntimeCommandRequestContract{"query_rl_projects", {
        }}, RuntimeCommandResponseContract{"query_rl_projects", "rl_projects", "projects|status", {
          {"projects", true, RuntimeContractFieldType::Array, "", RuntimeContractFieldType::Object, "name|tasks"},
          {"status", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"query_rl_projects", "*", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"query_rl_projects", "query_rl_projects", "handleQueryCommand"}},
      {"release_control_lease", RuntimeCommandRequestContract{"release_control_lease", {
          {"actor_id", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"lease_id", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"reason", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"release_control_lease", "control_authority", "summary_state|detail", {
          {"summary_state", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"control_authority", false, RuntimeContractFieldType::Object, "summary_state|detail", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"release_control_lease", "*", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"release_control_lease", "release_control_lease", "handleSessionCommand"}},
      {"renew_control_lease", RuntimeCommandRequestContract{"renew_control_lease", {
          {"actor_id", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"lease_id", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"ttl_s", false, RuntimeContractFieldType::Integer, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"renew_control_lease", "control_authority", "summary_state|detail|lease", {
          {"summary_state", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"detail", true, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"lease", true, RuntimeContractFieldType::Object, "lease_id|actor_id|workspace|role", RuntimeContractFieldType::Any, ""},
          {"control_authority", false, RuntimeContractFieldType::Object, "summary_state|detail", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"renew_control_lease", "*", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"renew_control_lease", "renew_control_lease", "handleSessionCommand"}},
      {"replay_path", RuntimeCommandRequestContract{"replay_path", {
          {"name", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"rate", false, RuntimeContractFieldType::Double, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"replay_path", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"replay_path", "AUTO_READY|PATH_VALIDATED|SCAN_COMPLETE", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"replay_path", "replay_path", "handleExecutionCommand"}},
      {"resume_scan", RuntimeCommandRequestContract{"resume_scan", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"resume_scan", "rt_command_ack", "rt_command_ack", {
          {"rt_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"resume_scan", "PAUSED_HOLD", CommandRuntimeLane::RtControl}, RuntimeCommandDispatchContract{"resume_scan", "resume_scan", "handleExecutionCommand"}},
      {"run_rl_project", RuntimeCommandRequestContract{"run_rl_project", {
          {"project", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"task", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"run_rl_project", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"run_rl_project", "AUTO_READY|SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"run_rl_project", "run_rl_project", "handleExecutionCommand"}},
      {"safe_retreat", RuntimeCommandRequestContract{"safe_retreat", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"safe_retreat", "rt_command_ack", "rt_command_ack", {
          {"rt_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"safe_retreat", "PATH_VALIDATED|APPROACHING|CONTACT_SEEKING|CONTACT_STABLE|SCANNING|PAUSED_HOLD|RECOVERY_RETRACT|FAULT", CommandRuntimeLane::RtControl}, RuntimeCommandDispatchContract{"safe_retreat", "safe_retreat", "handleExecutionCommand"}},
      {"save_record_path", RuntimeCommandRequestContract{"save_record_path", {
          {"name", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"save_as", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"save_record_path", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"save_record_path", "CONNECTED", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"save_record_path", "save_record_path", "handleExecutionCommand"}},
      {"seek_contact", RuntimeCommandRequestContract{"seek_contact", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"seek_contact", "rt_command_ack", "rt_command_ack", {
          {"rt_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"seek_contact", "PATH_VALIDATED|APPROACHING|PAUSED_HOLD|RECOVERY_RETRACT", CommandRuntimeLane::RtControl}, RuntimeCommandDispatchContract{"seek_contact", "seek_contact", "handleExecutionCommand"}},
      {"set_auto_mode", RuntimeCommandRequestContract{"set_auto_mode", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"set_auto_mode", "command_ack", "command_ack", {
          {"command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"set_auto_mode", "POWERED|AUTO_READY", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"set_auto_mode", "set_auto_mode", "handlePowerModeCommand"}},
      {"set_manual_mode", RuntimeCommandRequestContract{"set_manual_mode", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"set_manual_mode", "command_ack", "command_ack", {
          {"command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"set_manual_mode", "CONNECTED|POWERED|AUTO_READY", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"set_manual_mode", "set_manual_mode", "handlePowerModeCommand"}},
      {"start_procedure", RuntimeCommandRequestContract{"start_procedure", {
          {"procedure", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"start_procedure", "rt_command_ack", "rt_command_ack", {
          {"rt_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"start_procedure", "PATH_VALIDATED|CONTACT_STABLE|PAUSED_HOLD", CommandRuntimeLane::RtControl}, RuntimeCommandDispatchContract{"start_procedure", "start_procedure", "handleExecutionCommand"}},
      {"start_record_path", RuntimeCommandRequestContract{"start_record_path", {
          {"duration_s", false, RuntimeContractFieldType::Integer, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"start_record_path", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"start_record_path", "CONNECTED", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"start_record_path", "start_record_path", "handleExecutionCommand"}},
      {"start_scan", RuntimeCommandRequestContract{"start_scan", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"start_scan", "rt_command_ack", "rt_command_ack", {
          {"rt_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"start_scan", "PATH_VALIDATED|CONTACT_STABLE|PAUSED_HOLD", CommandRuntimeLane::RtControl}, RuntimeCommandDispatchContract{"start_scan", "start_procedure", "handleExecutionCommand"}},
      {"stop_record_path", RuntimeCommandRequestContract{"stop_record_path", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"stop_record_path", "execution_command_ack", "execution_command_ack", {
          {"execution_command_ack", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"stop_record_path", "CONNECTED", CommandRuntimeLane::Command}, RuntimeCommandDispatchContract{"stop_record_path", "stop_record_path", "handleExecutionCommand"}},
      {"validate_scan_plan", RuntimeCommandRequestContract{"validate_scan_plan", {
          {"config_snapshot", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""},
          {"scan_plan", true, RuntimeContractFieldType::Object, "plan_id|segments|plan_hash", RuntimeContractFieldType::Any, ""},
          {"scan_plan_hash", false, RuntimeContractFieldType::String, "", RuntimeContractFieldType::Any, ""},
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"validate_scan_plan", "final_verdict", "final_verdict", {
          {"final_verdict", true, RuntimeContractFieldType::Object, "accepted|authoritative|reason", RuntimeContractFieldType::Any, ""}
        }, true, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"validate_scan_plan", "AUTO_READY|SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"validate_scan_plan", "validate_scan_plan", "handleValidationCommand"}},
      {"validate_setup", RuntimeCommandRequestContract{"validate_setup", {
          {"_command_context", false, RuntimeContractFieldType::Object, "", RuntimeContractFieldType::Any, ""}
        }}, RuntimeCommandResponseContract{"validate_setup", "validation_report", "validation_report", {
          {"validation_report", true, RuntimeContractFieldType::Any, "", RuntimeContractFieldType::Any, ""}
        }, false, "ok|message|request_id|data|protocol_version"}, RuntimeCommandGuardContract{"validate_setup", "CONNECTED|POWERED|AUTO_READY|SESSION_LOCKED|PATH_VALIDATED", CommandRuntimeLane::Query}, RuntimeCommandDispatchContract{"validate_setup", "validate_setup", "handleValidationCommand"}},
