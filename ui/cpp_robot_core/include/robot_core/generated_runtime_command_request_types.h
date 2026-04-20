// Generated from schemas/runtime_command_manifest.json via runtime_command_contracts.py. Do not edit manually.
#pragma once

#include <optional>
#include <string>
#include <variant>

namespace robot_core {

struct AcquireControlLeaseRequest {
  static constexpr const char* kCommand = "acquire_control_lease";
  std::optional<std::string> actor_id;
  std::optional<std::string> intent_reason;
  std::optional<std::string> lease_id;
  std::optional<bool> preempt;
  std::optional<std::string> preempt_reason;
  std::optional<std::string> profile;
  std::optional<std::string> requested_claims;
  std::optional<std::string> role;
  std::optional<std::string> session_id;
  std::optional<std::string> source;
  std::optional<int> ttl_s;
  std::optional<std::string> workspace;
  std::optional<std::string> _command_context;
};

struct ApproachPrescanRequest {
  static constexpr const char* kCommand = "approach_prescan";
  std::optional<std::string> _command_context;
};

struct CancelRecordPathRequest {
  static constexpr const char* kCommand = "cancel_record_path";
  std::optional<std::string> _command_context;
};

struct ClearFaultRequest {
  static constexpr const char* kCommand = "clear_fault";
  std::optional<std::string> _command_context;
};

struct ClearInjectedFaultsRequest {
  static constexpr const char* kCommand = "clear_injected_faults";
  std::optional<std::string> _command_context;
};

struct CompileScanPlanRequest {
  static constexpr const char* kCommand = "compile_scan_plan";
  std::optional<std::string> config_snapshot;
  std::string scan_plan{};
  std::optional<std::string> scan_plan_hash;
  std::optional<std::string> _command_context;
};

struct ConnectRobotRequest {
  static constexpr const char* kCommand = "connect_robot";
  std::optional<std::string> local_ip;
  std::optional<std::string> remote_ip;
  std::optional<std::string> _command_context;
};

struct DisableDragRequest {
  static constexpr const char* kCommand = "disable_drag";
  std::optional<std::string> _command_context;
};

struct DisconnectRobotRequest {
  static constexpr const char* kCommand = "disconnect_robot";
  std::optional<std::string> _command_context;
};

struct EmergencyStopRequest {
  static constexpr const char* kCommand = "emergency_stop";
  std::optional<std::string> _command_context;
};

struct EnableDragRequest {
  static constexpr const char* kCommand = "enable_drag";
  std::optional<std::string> space;
  std::optional<std::string> type;
  std::optional<std::string> _command_context;
};

struct GetAuthoritativeRuntimeEnvelopeRequest {
  static constexpr const char* kCommand = "get_authoritative_runtime_envelope";
};

struct GetCapabilityContractRequest {
  static constexpr const char* kCommand = "get_capability_contract";
};

struct GetClinicalMainlineContractRequest {
  static constexpr const char* kCommand = "get_clinical_mainline_contract";
};

struct GetControlGovernanceContractRequest {
  static constexpr const char* kCommand = "get_control_governance_contract";
};

struct GetControllerEvidenceRequest {
  static constexpr const char* kCommand = "get_controller_evidence";
};

struct GetDeploymentContractRequest {
  static constexpr const char* kCommand = "get_deployment_contract";
};

struct GetDualStateMachineContractRequest {
  static constexpr const char* kCommand = "get_dual_state_machine_contract";
};

struct GetFaultInjectionContractRequest {
  static constexpr const char* kCommand = "get_fault_injection_contract";
};

struct GetHardwareLifecycleContractRequest {
  static constexpr const char* kCommand = "get_hardware_lifecycle_contract";
};

struct GetIdentityContractRequest {
  static constexpr const char* kCommand = "get_identity_contract";
};

struct GetIoSnapshotRequest {
  static constexpr const char* kCommand = "get_io_snapshot";
};

struct GetMainlineExecutorContractRequest {
  static constexpr const char* kCommand = "get_mainline_executor_contract";
};

struct GetModelAuthorityContractRequest {
  static constexpr const char* kCommand = "get_model_authority_contract";
};

struct GetMotionContractRequest {
  static constexpr const char* kCommand = "get_motion_contract";
};

struct GetRecoveryContractRequest {
  static constexpr const char* kCommand = "get_recovery_contract";
};

struct GetRegisterSnapshotRequest {
  static constexpr const char* kCommand = "get_register_snapshot";
};

struct GetReleaseContractRequest {
  static constexpr const char* kCommand = "get_release_contract";
};

struct GetRobotFamilyContractRequest {
  static constexpr const char* kCommand = "get_robot_family_contract";
};

struct GetRtKernelContractRequest {
  static constexpr const char* kCommand = "get_rt_kernel_contract";
};

struct GetRuntimeAlignmentRequest {
  static constexpr const char* kCommand = "get_runtime_alignment";
};

struct GetSafetyConfigRequest {
  static constexpr const char* kCommand = "get_safety_config";
};

struct GetSafetyRecoveryContractRequest {
  static constexpr const char* kCommand = "get_safety_recovery_contract";
};

struct GetSdkRuntimeConfigRequest {
  static constexpr const char* kCommand = "get_sdk_runtime_config";
};

struct GetSessionDriftContractRequest {
  static constexpr const char* kCommand = "get_session_drift_contract";
};

struct GetSessionFreezeRequest {
  static constexpr const char* kCommand = "get_session_freeze";
};

struct GetVendorBoundaryContractRequest {
  static constexpr const char* kCommand = "get_vendor_boundary_contract";
};

struct GetXmateModelSummaryRequest {
  static constexpr const char* kCommand = "get_xmate_model_summary";
};

struct GoHomeRequest {
  static constexpr const char* kCommand = "go_home";
  std::optional<std::string> _command_context;
};

struct InjectFaultRequest {
  static constexpr const char* kCommand = "inject_fault";
  std::string fault_name{};
  std::optional<std::string> _command_context;
};

struct LoadScanPlanRequest {
  static constexpr const char* kCommand = "load_scan_plan";
  std::string scan_plan{};
  std::optional<std::string> scan_plan_hash;
  std::optional<std::string> _command_context;
};

struct LockSessionRequest {
  static constexpr const char* kCommand = "lock_session";
  std::optional<std::string> build_id;
  std::string config_snapshot{};
  std::string device_health_snapshot{};
  std::string device_roster{};
  std::optional<std::string> force_sensor_provider;
  std::optional<int> protocol_version;
  std::string safety_thresholds{};
  std::string scan_plan_hash{};
  std::string session_dir{};
  std::optional<std::string> session_freeze_policy;
  std::string session_id{};
  std::optional<std::string> software_version;
  std::optional<std::string> strict_runtime_freeze_gate;
  std::optional<std::string> _command_context;
};

struct PauseRlProjectRequest {
  static constexpr const char* kCommand = "pause_rl_project";
  std::optional<std::string> _command_context;
};

struct PauseScanRequest {
  static constexpr const char* kCommand = "pause_scan";
  std::optional<std::string> _command_context;
};

struct PowerOffRequest {
  static constexpr const char* kCommand = "power_off";
  std::optional<std::string> _command_context;
};

struct PowerOnRequest {
  static constexpr const char* kCommand = "power_on";
  std::optional<std::string> _command_context;
};

struct QueryControllerLogRequest {
  static constexpr const char* kCommand = "query_controller_log";
};

struct QueryFinalVerdictRequest {
  static constexpr const char* kCommand = "query_final_verdict";
};

struct QueryPathListsRequest {
  static constexpr const char* kCommand = "query_path_lists";
};

struct QueryRlProjectsRequest {
  static constexpr const char* kCommand = "query_rl_projects";
};

struct ReleaseControlLeaseRequest {
  static constexpr const char* kCommand = "release_control_lease";
  std::optional<std::string> actor_id;
  std::optional<std::string> lease_id;
  std::optional<std::string> reason;
  std::optional<std::string> _command_context;
};

struct RenewControlLeaseRequest {
  static constexpr const char* kCommand = "renew_control_lease";
  std::optional<std::string> actor_id;
  std::optional<std::string> lease_id;
  std::optional<int> ttl_s;
  std::optional<std::string> _command_context;
};

struct ReplayPathRequest {
  static constexpr const char* kCommand = "replay_path";
  std::optional<std::string> name;
  std::optional<double> rate;
  std::optional<std::string> _command_context;
};

struct ResumeScanRequest {
  static constexpr const char* kCommand = "resume_scan";
  std::optional<std::string> _command_context;
};

struct RunRlProjectRequest {
  static constexpr const char* kCommand = "run_rl_project";
  std::optional<std::string> project;
  std::optional<std::string> task;
  std::optional<std::string> _command_context;
};

struct SafeRetreatRequest {
  static constexpr const char* kCommand = "safe_retreat";
  std::optional<std::string> _command_context;
};

struct SaveRecordPathRequest {
  static constexpr const char* kCommand = "save_record_path";
  std::optional<std::string> name;
  std::optional<std::string> save_as;
  std::optional<std::string> _command_context;
};

struct SeekContactRequest {
  static constexpr const char* kCommand = "seek_contact";
  std::optional<std::string> _command_context;
};

struct SetAutoModeRequest {
  static constexpr const char* kCommand = "set_auto_mode";
  std::optional<std::string> _command_context;
};

struct SetManualModeRequest {
  static constexpr const char* kCommand = "set_manual_mode";
  std::optional<std::string> _command_context;
};

struct StartProcedureRequest {
  static constexpr const char* kCommand = "start_procedure";
  std::string procedure{};
  std::optional<std::string> _command_context;
};

struct StartRecordPathRequest {
  static constexpr const char* kCommand = "start_record_path";
  std::optional<int> duration_s;
  std::optional<std::string> _command_context;
};

struct StartScanRequest {
  static constexpr const char* kCommand = "start_scan";
  std::optional<std::string> _command_context;
};

struct StopRecordPathRequest {
  static constexpr const char* kCommand = "stop_record_path";
  std::optional<std::string> _command_context;
};

struct ValidateScanPlanRequest {
  static constexpr const char* kCommand = "validate_scan_plan";
  std::optional<std::string> config_snapshot;
  std::string scan_plan{};
  std::optional<std::string> scan_plan_hash;
  std::optional<std::string> _command_context;
};

struct ValidateSetupRequest {
  static constexpr const char* kCommand = "validate_setup";
  std::optional<std::string> _command_context;
};

using RuntimeTypedRequestVariant = std::variant<
    AcquireControlLeaseRequest,
    ApproachPrescanRequest,
    CancelRecordPathRequest,
    ClearFaultRequest,
    ClearInjectedFaultsRequest,
    CompileScanPlanRequest,
    ConnectRobotRequest,
    DisableDragRequest,
    DisconnectRobotRequest,
    EmergencyStopRequest,
    EnableDragRequest,
    GetAuthoritativeRuntimeEnvelopeRequest,
    GetCapabilityContractRequest,
    GetClinicalMainlineContractRequest,
    GetControlGovernanceContractRequest,
    GetControllerEvidenceRequest,
    GetDeploymentContractRequest,
    GetDualStateMachineContractRequest,
    GetFaultInjectionContractRequest,
    GetHardwareLifecycleContractRequest,
    GetIdentityContractRequest,
    GetIoSnapshotRequest,
    GetMainlineExecutorContractRequest,
    GetModelAuthorityContractRequest,
    GetMotionContractRequest,
    GetRecoveryContractRequest,
    GetRegisterSnapshotRequest,
    GetReleaseContractRequest,
    GetRobotFamilyContractRequest,
    GetRtKernelContractRequest,
    GetRuntimeAlignmentRequest,
    GetSafetyConfigRequest,
    GetSafetyRecoveryContractRequest,
    GetSdkRuntimeConfigRequest,
    GetSessionDriftContractRequest,
    GetSessionFreezeRequest,
    GetVendorBoundaryContractRequest,
    GetXmateModelSummaryRequest,
    GoHomeRequest,
    InjectFaultRequest,
    LoadScanPlanRequest,
    LockSessionRequest,
    PauseRlProjectRequest,
    PauseScanRequest,
    PowerOffRequest,
    PowerOnRequest,
    QueryControllerLogRequest,
    QueryFinalVerdictRequest,
    QueryPathListsRequest,
    QueryRlProjectsRequest,
    ReleaseControlLeaseRequest,
    RenewControlLeaseRequest,
    ReplayPathRequest,
    ResumeScanRequest,
    RunRlProjectRequest,
    SafeRetreatRequest,
    SaveRecordPathRequest,
    SeekContactRequest,
    SetAutoModeRequest,
    SetManualModeRequest,
    StartProcedureRequest,
    StartRecordPathRequest,
    StartScanRequest,
    StopRecordPathRequest,
    ValidateScanPlanRequest,
    ValidateSetupRequest
>;

}  // namespace robot_core
