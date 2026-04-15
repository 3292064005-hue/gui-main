// Generated from schemas/runtime_command_manifest.json via runtime_command_contracts.py. Do not edit manually.
#pragma once

#include <optional>
#include <string>
#include <variant>

namespace robot_core {

struct ApproachPrescanRequest {
  static constexpr const char* kCommand = "approach_prescan";
};

struct CancelRecordPathRequest {
  static constexpr const char* kCommand = "cancel_record_path";
};

struct ClearFaultRequest {
  static constexpr const char* kCommand = "clear_fault";
};

struct ClearInjectedFaultsRequest {
  static constexpr const char* kCommand = "clear_injected_faults";
};

struct CompileScanPlanRequest {
  static constexpr const char* kCommand = "compile_scan_plan";
  std::optional<std::string> config_snapshot;
  std::string scan_plan{};
  std::optional<std::string> scan_plan_hash;
};

struct ConnectRobotRequest {
  static constexpr const char* kCommand = "connect_robot";
  std::optional<std::string> local_ip;
  std::optional<std::string> remote_ip;
};

struct DisableDragRequest {
  static constexpr const char* kCommand = "disable_drag";
};

struct DisconnectRobotRequest {
  static constexpr const char* kCommand = "disconnect_robot";
};

struct EmergencyStopRequest {
  static constexpr const char* kCommand = "emergency_stop";
};

struct EnableDragRequest {
  static constexpr const char* kCommand = "enable_drag";
  std::optional<std::string> space;
  std::optional<std::string> type;
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
};

struct InjectFaultRequest {
  static constexpr const char* kCommand = "inject_fault";
  std::string fault_name{};
};

struct LoadScanPlanRequest {
  static constexpr const char* kCommand = "load_scan_plan";
  std::string scan_plan{};
  std::optional<std::string> scan_plan_hash;
};

struct LockSessionRequest {
  static constexpr const char* kCommand = "lock_session";
  std::string config_snapshot{};
  std::string device_roster{};
  std::string scan_plan_hash{};
  std::string session_dir{};
  std::string session_id{};
};

struct PauseRlProjectRequest {
  static constexpr const char* kCommand = "pause_rl_project";
};

struct PauseScanRequest {
  static constexpr const char* kCommand = "pause_scan";
};

struct PowerOffRequest {
  static constexpr const char* kCommand = "power_off";
};

struct PowerOnRequest {
  static constexpr const char* kCommand = "power_on";
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

struct ReplayPathRequest {
  static constexpr const char* kCommand = "replay_path";
  std::optional<std::string> name;
  std::optional<double> rate;
};

struct ResumeScanRequest {
  static constexpr const char* kCommand = "resume_scan";
};

struct RunRlProjectRequest {
  static constexpr const char* kCommand = "run_rl_project";
  std::optional<std::string> project;
  std::optional<std::string> task;
};

struct SafeRetreatRequest {
  static constexpr const char* kCommand = "safe_retreat";
};

struct SaveRecordPathRequest {
  static constexpr const char* kCommand = "save_record_path";
  std::optional<std::string> name;
  std::optional<std::string> save_as;
};

struct SeekContactRequest {
  static constexpr const char* kCommand = "seek_contact";
};

struct SetAutoModeRequest {
  static constexpr const char* kCommand = "set_auto_mode";
};

struct SetManualModeRequest {
  static constexpr const char* kCommand = "set_manual_mode";
};

struct StartRecordPathRequest {
  static constexpr const char* kCommand = "start_record_path";
  std::optional<int> duration_s;
};

struct StartScanRequest {
  static constexpr const char* kCommand = "start_scan";
};

struct StopRecordPathRequest {
  static constexpr const char* kCommand = "stop_record_path";
};

struct ValidateScanPlanRequest {
  static constexpr const char* kCommand = "validate_scan_plan";
  std::optional<std::string> config_snapshot;
  std::string scan_plan{};
  std::optional<std::string> scan_plan_hash;
};

struct ValidateSetupRequest {
  static constexpr const char* kCommand = "validate_setup";
};

using RuntimeTypedRequestVariant = std::variant<
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
    ReplayPathRequest,
    ResumeScanRequest,
    RunRlProjectRequest,
    SafeRetreatRequest,
    SaveRecordPathRequest,
    SeekContactRequest,
    SetAutoModeRequest,
    SetManualModeRequest,
    StartRecordPathRequest,
    StartScanRequest,
    StopRecordPathRequest,
    ValidateScanPlanRequest,
    ValidateSetupRequest
>;

}  // namespace robot_core
