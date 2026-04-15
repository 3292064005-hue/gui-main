// Generated from schemas/runtime_command_manifest.json via runtime_command_contracts.py. Do not edit manually.

  if (command == "approach_prescan") {
    ApproachPrescanRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "cancel_record_path") {
    CancelRecordPathRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "clear_fault") {
    ClearFaultRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "clear_injected_faults") {
    ClearInjectedFaultsRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "compile_scan_plan") {
    CompileScanPlanRequest typed{};
    if (request.hasObjectField("config_snapshot")) typed.config_snapshot = request.objectFieldJson("config_snapshot");
    typed.scan_plan = request.objectFieldJson("scan_plan");
    if (request.hasStringField("scan_plan_hash")) typed.scan_plan_hash = request.stringField("scan_plan_hash");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "connect_robot") {
    ConnectRobotRequest typed{};
    if (request.hasStringField("local_ip")) typed.local_ip = request.stringField("local_ip");
    if (request.hasStringField("remote_ip")) typed.remote_ip = request.stringField("remote_ip");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "disable_drag") {
    DisableDragRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "disconnect_robot") {
    DisconnectRobotRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "emergency_stop") {
    EmergencyStopRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "enable_drag") {
    EnableDragRequest typed{};
    if (request.hasStringField("space")) typed.space = request.stringField("space");
    if (request.hasStringField("type")) typed.type = request.stringField("type");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_authoritative_runtime_envelope") {
    GetAuthoritativeRuntimeEnvelopeRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_capability_contract") {
    GetCapabilityContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_clinical_mainline_contract") {
    GetClinicalMainlineContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_control_governance_contract") {
    GetControlGovernanceContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_controller_evidence") {
    GetControllerEvidenceRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_deployment_contract") {
    GetDeploymentContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_dual_state_machine_contract") {
    GetDualStateMachineContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_fault_injection_contract") {
    GetFaultInjectionContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_hardware_lifecycle_contract") {
    GetHardwareLifecycleContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_identity_contract") {
    GetIdentityContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_io_snapshot") {
    GetIoSnapshotRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_mainline_executor_contract") {
    GetMainlineExecutorContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_model_authority_contract") {
    GetModelAuthorityContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_motion_contract") {
    GetMotionContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_recovery_contract") {
    GetRecoveryContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_register_snapshot") {
    GetRegisterSnapshotRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_release_contract") {
    GetReleaseContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_robot_family_contract") {
    GetRobotFamilyContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_rt_kernel_contract") {
    GetRtKernelContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_runtime_alignment") {
    GetRuntimeAlignmentRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_safety_config") {
    GetSafetyConfigRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_safety_recovery_contract") {
    GetSafetyRecoveryContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_sdk_runtime_config") {
    GetSdkRuntimeConfigRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_session_drift_contract") {
    GetSessionDriftContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_session_freeze") {
    GetSessionFreezeRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_vendor_boundary_contract") {
    GetVendorBoundaryContractRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "get_xmate_model_summary") {
    GetXmateModelSummaryRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "go_home") {
    GoHomeRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "inject_fault") {
    InjectFaultRequest typed{};
    typed.fault_name = request.stringField("fault_name");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "load_scan_plan") {
    LoadScanPlanRequest typed{};
    typed.scan_plan = request.objectFieldJson("scan_plan");
    if (request.hasStringField("scan_plan_hash")) typed.scan_plan_hash = request.stringField("scan_plan_hash");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "lock_session") {
    LockSessionRequest typed{};
    typed.config_snapshot = request.objectFieldJson("config_snapshot");
    typed.device_roster = request.objectFieldJson("device_roster");
    typed.scan_plan_hash = request.stringField("scan_plan_hash");
    typed.session_dir = request.stringField("session_dir");
    typed.session_id = request.stringField("session_id");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "pause_rl_project") {
    PauseRlProjectRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "pause_scan") {
    PauseScanRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "power_off") {
    PowerOffRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "power_on") {
    PowerOnRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "query_controller_log") {
    QueryControllerLogRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "query_final_verdict") {
    QueryFinalVerdictRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "query_path_lists") {
    QueryPathListsRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "query_rl_projects") {
    QueryRlProjectsRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "replay_path") {
    ReplayPathRequest typed{};
    if (request.hasStringField("name")) typed.name = request.stringField("name");
    if (request.hasDoubleField("rate")) typed.rate = request.doubleField("rate");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "resume_scan") {
    ResumeScanRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "run_rl_project") {
    RunRlProjectRequest typed{};
    if (request.hasStringField("project")) typed.project = request.stringField("project");
    if (request.hasStringField("task")) typed.task = request.stringField("task");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "safe_retreat") {
    SafeRetreatRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "save_record_path") {
    SaveRecordPathRequest typed{};
    if (request.hasStringField("name")) typed.name = request.stringField("name");
    if (request.hasStringField("save_as")) typed.save_as = request.stringField("save_as");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "seek_contact") {
    SeekContactRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "set_auto_mode") {
    SetAutoModeRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "set_manual_mode") {
    SetManualModeRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "start_record_path") {
    StartRecordPathRequest typed{};
    if (request.hasIntegerField("duration_s")) typed.duration_s = request.intField("duration_s");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "start_scan") {
    StartScanRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "stop_record_path") {
    StopRecordPathRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "validate_scan_plan") {
    ValidateScanPlanRequest typed{};
    if (request.hasObjectField("config_snapshot")) typed.config_snapshot = request.objectFieldJson("config_snapshot");
    typed.scan_plan = request.objectFieldJson("scan_plan");
    if (request.hasStringField("scan_plan_hash")) typed.scan_plan_hash = request.stringField("scan_plan_hash");
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

  if (command == "validate_setup") {
    ValidateSetupRequest typed{};
    if (typed_request != nullptr) *typed_request = std::move(typed);
    return true;
  }

