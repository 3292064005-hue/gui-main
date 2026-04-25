// Generated from schemas/runtime_command_manifest.json via runtime_command_contracts.py. Do not edit manually.

inline std::string CoreRuntime::handleAcquireControlLeaseTyped(const RuntimeCommandContext& context, const AcquireControlLeaseRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = AcquireControlLeaseRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(AcquireControlLeaseRequest::kCommand);
  return handleSessionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<AcquireControlLeaseRequest>(const RuntimeCommandContext& context, const AcquireControlLeaseRequest& request) {
  return handleAcquireControlLeaseTyped(context, request);
}

inline std::string CoreRuntime::handleApproachPrescanTyped(const RuntimeCommandContext& context, const ApproachPrescanRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = ApproachPrescanRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(ApproachPrescanRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<ApproachPrescanRequest>(const RuntimeCommandContext& context, const ApproachPrescanRequest& request) {
  return handleApproachPrescanTyped(context, request);
}

inline std::string CoreRuntime::handleCancelRecordPathTyped(const RuntimeCommandContext& context, const CancelRecordPathRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = CancelRecordPathRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(CancelRecordPathRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<CancelRecordPathRequest>(const RuntimeCommandContext& context, const CancelRecordPathRequest& request) {
  return handleCancelRecordPathTyped(context, request);
}

inline std::string CoreRuntime::handleClearFaultTyped(const RuntimeCommandContext& context, const ClearFaultRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = ClearFaultRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(ClearFaultRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<ClearFaultRequest>(const RuntimeCommandContext& context, const ClearFaultRequest& request) {
  return handleClearFaultTyped(context, request);
}

inline std::string CoreRuntime::handleClearInjectedFaultsTyped(const RuntimeCommandContext& context, const ClearInjectedFaultsRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = ClearInjectedFaultsRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(ClearInjectedFaultsRequest::kCommand);
  return handleFaultInjectionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<ClearInjectedFaultsRequest>(const RuntimeCommandContext& context, const ClearInjectedFaultsRequest& request) {
  return handleClearInjectedFaultsTyped(context, request);
}

inline std::string CoreRuntime::handleConnectRobotTyped(const RuntimeCommandContext& context, const ConnectRobotRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = ConnectRobotRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(ConnectRobotRequest::kCommand);
  return handleConnectionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<ConnectRobotRequest>(const RuntimeCommandContext& context, const ConnectRobotRequest& request) {
  return handleConnectRobotTyped(context, request);
}

inline std::string CoreRuntime::handleDisableDragTyped(const RuntimeCommandContext& context, const DisableDragRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = DisableDragRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(DisableDragRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<DisableDragRequest>(const RuntimeCommandContext& context, const DisableDragRequest& request) {
  return handleDisableDragTyped(context, request);
}

inline std::string CoreRuntime::handleDisconnectRobotTyped(const RuntimeCommandContext& context, const DisconnectRobotRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = DisconnectRobotRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(DisconnectRobotRequest::kCommand);
  return handleConnectionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<DisconnectRobotRequest>(const RuntimeCommandContext& context, const DisconnectRobotRequest& request) {
  return handleDisconnectRobotTyped(context, request);
}

inline std::string CoreRuntime::handleEmergencyStopTyped(const RuntimeCommandContext& context, const EmergencyStopRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = EmergencyStopRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(EmergencyStopRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<EmergencyStopRequest>(const RuntimeCommandContext& context, const EmergencyStopRequest& request) {
  return handleEmergencyStopTyped(context, request);
}

inline std::string CoreRuntime::handleEnableDragTyped(const RuntimeCommandContext& context, const EnableDragRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = EnableDragRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(EnableDragRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<EnableDragRequest>(const RuntimeCommandContext& context, const EnableDragRequest& request) {
  return handleEnableDragTyped(context, request);
}

inline std::string CoreRuntime::handleGetAuthoritativeRuntimeEnvelopeTyped(const RuntimeCommandContext& context, const GetAuthoritativeRuntimeEnvelopeRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetAuthoritativeRuntimeEnvelopeRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetAuthoritativeRuntimeEnvelopeRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetAuthoritativeRuntimeEnvelopeRequest>(const RuntimeCommandContext& context, const GetAuthoritativeRuntimeEnvelopeRequest& request) {
  return handleGetAuthoritativeRuntimeEnvelopeTyped(context, request);
}

inline std::string CoreRuntime::handleGetCapabilityContractTyped(const RuntimeCommandContext& context, const GetCapabilityContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetCapabilityContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetCapabilityContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetCapabilityContractRequest>(const RuntimeCommandContext& context, const GetCapabilityContractRequest& request) {
  return handleGetCapabilityContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetClinicalMainlineContractTyped(const RuntimeCommandContext& context, const GetClinicalMainlineContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetClinicalMainlineContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetClinicalMainlineContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetClinicalMainlineContractRequest>(const RuntimeCommandContext& context, const GetClinicalMainlineContractRequest& request) {
  return handleGetClinicalMainlineContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetControlGovernanceContractTyped(const RuntimeCommandContext& context, const GetControlGovernanceContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetControlGovernanceContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetControlGovernanceContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetControlGovernanceContractRequest>(const RuntimeCommandContext& context, const GetControlGovernanceContractRequest& request) {
  return handleGetControlGovernanceContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetControllerEvidenceTyped(const RuntimeCommandContext& context, const GetControllerEvidenceRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetControllerEvidenceRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetControllerEvidenceRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetControllerEvidenceRequest>(const RuntimeCommandContext& context, const GetControllerEvidenceRequest& request) {
  return handleGetControllerEvidenceTyped(context, request);
}

inline std::string CoreRuntime::handleGetDeploymentContractTyped(const RuntimeCommandContext& context, const GetDeploymentContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetDeploymentContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetDeploymentContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetDeploymentContractRequest>(const RuntimeCommandContext& context, const GetDeploymentContractRequest& request) {
  return handleGetDeploymentContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetDualStateMachineContractTyped(const RuntimeCommandContext& context, const GetDualStateMachineContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetDualStateMachineContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetDualStateMachineContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetDualStateMachineContractRequest>(const RuntimeCommandContext& context, const GetDualStateMachineContractRequest& request) {
  return handleGetDualStateMachineContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetFaultInjectionContractTyped(const RuntimeCommandContext& context, const GetFaultInjectionContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetFaultInjectionContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetFaultInjectionContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetFaultInjectionContractRequest>(const RuntimeCommandContext& context, const GetFaultInjectionContractRequest& request) {
  return handleGetFaultInjectionContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetHardwareLifecycleContractTyped(const RuntimeCommandContext& context, const GetHardwareLifecycleContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetHardwareLifecycleContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetHardwareLifecycleContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetHardwareLifecycleContractRequest>(const RuntimeCommandContext& context, const GetHardwareLifecycleContractRequest& request) {
  return handleGetHardwareLifecycleContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetIdentityContractTyped(const RuntimeCommandContext& context, const GetIdentityContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetIdentityContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetIdentityContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetIdentityContractRequest>(const RuntimeCommandContext& context, const GetIdentityContractRequest& request) {
  return handleGetIdentityContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetIoSnapshotTyped(const RuntimeCommandContext& context, const GetIoSnapshotRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetIoSnapshotRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetIoSnapshotRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetIoSnapshotRequest>(const RuntimeCommandContext& context, const GetIoSnapshotRequest& request) {
  return handleGetIoSnapshotTyped(context, request);
}

inline std::string CoreRuntime::handleGetMainlineExecutorContractTyped(const RuntimeCommandContext& context, const GetMainlineExecutorContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetMainlineExecutorContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetMainlineExecutorContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetMainlineExecutorContractRequest>(const RuntimeCommandContext& context, const GetMainlineExecutorContractRequest& request) {
  return handleGetMainlineExecutorContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetModelAuthorityContractTyped(const RuntimeCommandContext& context, const GetModelAuthorityContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetModelAuthorityContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetModelAuthorityContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetModelAuthorityContractRequest>(const RuntimeCommandContext& context, const GetModelAuthorityContractRequest& request) {
  return handleGetModelAuthorityContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetMotionContractTyped(const RuntimeCommandContext& context, const GetMotionContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetMotionContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetMotionContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetMotionContractRequest>(const RuntimeCommandContext& context, const GetMotionContractRequest& request) {
  return handleGetMotionContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetRecoveryContractTyped(const RuntimeCommandContext& context, const GetRecoveryContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetRecoveryContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetRecoveryContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetRecoveryContractRequest>(const RuntimeCommandContext& context, const GetRecoveryContractRequest& request) {
  return handleGetRecoveryContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetRegisterSnapshotTyped(const RuntimeCommandContext& context, const GetRegisterSnapshotRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetRegisterSnapshotRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetRegisterSnapshotRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetRegisterSnapshotRequest>(const RuntimeCommandContext& context, const GetRegisterSnapshotRequest& request) {
  return handleGetRegisterSnapshotTyped(context, request);
}

inline std::string CoreRuntime::handleGetReleaseContractTyped(const RuntimeCommandContext& context, const GetReleaseContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetReleaseContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetReleaseContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetReleaseContractRequest>(const RuntimeCommandContext& context, const GetReleaseContractRequest& request) {
  return handleGetReleaseContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetRobotFamilyContractTyped(const RuntimeCommandContext& context, const GetRobotFamilyContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetRobotFamilyContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetRobotFamilyContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetRobotFamilyContractRequest>(const RuntimeCommandContext& context, const GetRobotFamilyContractRequest& request) {
  return handleGetRobotFamilyContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetRtKernelContractTyped(const RuntimeCommandContext& context, const GetRtKernelContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetRtKernelContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetRtKernelContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetRtKernelContractRequest>(const RuntimeCommandContext& context, const GetRtKernelContractRequest& request) {
  return handleGetRtKernelContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetRuntimeAlignmentTyped(const RuntimeCommandContext& context, const GetRuntimeAlignmentRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetRuntimeAlignmentRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetRuntimeAlignmentRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetRuntimeAlignmentRequest>(const RuntimeCommandContext& context, const GetRuntimeAlignmentRequest& request) {
  return handleGetRuntimeAlignmentTyped(context, request);
}

inline std::string CoreRuntime::handleGetSafetyConfigTyped(const RuntimeCommandContext& context, const GetSafetyConfigRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetSafetyConfigRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetSafetyConfigRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetSafetyConfigRequest>(const RuntimeCommandContext& context, const GetSafetyConfigRequest& request) {
  return handleGetSafetyConfigTyped(context, request);
}

inline std::string CoreRuntime::handleGetSafetyRecoveryContractTyped(const RuntimeCommandContext& context, const GetSafetyRecoveryContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetSafetyRecoveryContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetSafetyRecoveryContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetSafetyRecoveryContractRequest>(const RuntimeCommandContext& context, const GetSafetyRecoveryContractRequest& request) {
  return handleGetSafetyRecoveryContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetSdkRuntimeConfigTyped(const RuntimeCommandContext& context, const GetSdkRuntimeConfigRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetSdkRuntimeConfigRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetSdkRuntimeConfigRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetSdkRuntimeConfigRequest>(const RuntimeCommandContext& context, const GetSdkRuntimeConfigRequest& request) {
  return handleGetSdkRuntimeConfigTyped(context, request);
}

inline std::string CoreRuntime::handleGetSessionDriftContractTyped(const RuntimeCommandContext& context, const GetSessionDriftContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetSessionDriftContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetSessionDriftContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetSessionDriftContractRequest>(const RuntimeCommandContext& context, const GetSessionDriftContractRequest& request) {
  return handleGetSessionDriftContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetSessionFreezeTyped(const RuntimeCommandContext& context, const GetSessionFreezeRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetSessionFreezeRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetSessionFreezeRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetSessionFreezeRequest>(const RuntimeCommandContext& context, const GetSessionFreezeRequest& request) {
  return handleGetSessionFreezeTyped(context, request);
}

inline std::string CoreRuntime::handleGetVendorBoundaryContractTyped(const RuntimeCommandContext& context, const GetVendorBoundaryContractRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetVendorBoundaryContractRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetVendorBoundaryContractRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetVendorBoundaryContractRequest>(const RuntimeCommandContext& context, const GetVendorBoundaryContractRequest& request) {
  return handleGetVendorBoundaryContractTyped(context, request);
}

inline std::string CoreRuntime::handleGetXmateModelSummaryTyped(const RuntimeCommandContext& context, const GetXmateModelSummaryRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GetXmateModelSummaryRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GetXmateModelSummaryRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GetXmateModelSummaryRequest>(const RuntimeCommandContext& context, const GetXmateModelSummaryRequest& request) {
  return handleGetXmateModelSummaryTyped(context, request);
}

inline std::string CoreRuntime::handleGoHomeTyped(const RuntimeCommandContext& context, const GoHomeRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = GoHomeRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(GoHomeRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<GoHomeRequest>(const RuntimeCommandContext& context, const GoHomeRequest& request) {
  return handleGoHomeTyped(context, request);
}

inline std::string CoreRuntime::handleInjectFaultTyped(const RuntimeCommandContext& context, const InjectFaultRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = InjectFaultRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(InjectFaultRequest::kCommand);
  return handleFaultInjectionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<InjectFaultRequest>(const RuntimeCommandContext& context, const InjectFaultRequest& request) {
  return handleInjectFaultTyped(context, request);
}

inline std::string CoreRuntime::handleLoadScanPlanTyped(const RuntimeCommandContext& context, const LoadScanPlanRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = LoadScanPlanRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(LoadScanPlanRequest::kCommand);
  return handleSessionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<LoadScanPlanRequest>(const RuntimeCommandContext& context, const LoadScanPlanRequest& request) {
  return handleLoadScanPlanTyped(context, request);
}

inline std::string CoreRuntime::handleLockSessionTyped(const RuntimeCommandContext& context, const LockSessionRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = LockSessionRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(LockSessionRequest::kCommand);
  return handleSessionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<LockSessionRequest>(const RuntimeCommandContext& context, const LockSessionRequest& request) {
  return handleLockSessionTyped(context, request);
}

inline std::string CoreRuntime::handlePauseRlProjectTyped(const RuntimeCommandContext& context, const PauseRlProjectRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = PauseRlProjectRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(PauseRlProjectRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<PauseRlProjectRequest>(const RuntimeCommandContext& context, const PauseRlProjectRequest& request) {
  return handlePauseRlProjectTyped(context, request);
}

inline std::string CoreRuntime::handlePauseScanTyped(const RuntimeCommandContext& context, const PauseScanRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = PauseScanRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(PauseScanRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<PauseScanRequest>(const RuntimeCommandContext& context, const PauseScanRequest& request) {
  return handlePauseScanTyped(context, request);
}

inline std::string CoreRuntime::handlePowerOffTyped(const RuntimeCommandContext& context, const PowerOffRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = PowerOffRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(PowerOffRequest::kCommand);
  return handlePowerModeCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<PowerOffRequest>(const RuntimeCommandContext& context, const PowerOffRequest& request) {
  return handlePowerOffTyped(context, request);
}

inline std::string CoreRuntime::handlePowerOnTyped(const RuntimeCommandContext& context, const PowerOnRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = PowerOnRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(PowerOnRequest::kCommand);
  return handlePowerModeCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<PowerOnRequest>(const RuntimeCommandContext& context, const PowerOnRequest& request) {
  return handlePowerOnTyped(context, request);
}

inline std::string CoreRuntime::handleQueryControllerLogTyped(const RuntimeCommandContext& context, const QueryControllerLogRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = QueryControllerLogRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(QueryControllerLogRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<QueryControllerLogRequest>(const RuntimeCommandContext& context, const QueryControllerLogRequest& request) {
  return handleQueryControllerLogTyped(context, request);
}

inline std::string CoreRuntime::handleQueryFinalVerdictTyped(const RuntimeCommandContext& context, const QueryFinalVerdictRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = QueryFinalVerdictRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(QueryFinalVerdictRequest::kCommand);
  return handleValidationCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<QueryFinalVerdictRequest>(const RuntimeCommandContext& context, const QueryFinalVerdictRequest& request) {
  return handleQueryFinalVerdictTyped(context, request);
}

inline std::string CoreRuntime::handleQueryPathListsTyped(const RuntimeCommandContext& context, const QueryPathListsRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = QueryPathListsRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(QueryPathListsRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<QueryPathListsRequest>(const RuntimeCommandContext& context, const QueryPathListsRequest& request) {
  return handleQueryPathListsTyped(context, request);
}

inline std::string CoreRuntime::handleQueryRlProjectsTyped(const RuntimeCommandContext& context, const QueryRlProjectsRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = QueryRlProjectsRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(QueryRlProjectsRequest::kCommand);
  return handleQueryCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<QueryRlProjectsRequest>(const RuntimeCommandContext& context, const QueryRlProjectsRequest& request) {
  return handleQueryRlProjectsTyped(context, request);
}

inline std::string CoreRuntime::handleReleaseControlLeaseTyped(const RuntimeCommandContext& context, const ReleaseControlLeaseRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = ReleaseControlLeaseRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(ReleaseControlLeaseRequest::kCommand);
  return handleSessionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<ReleaseControlLeaseRequest>(const RuntimeCommandContext& context, const ReleaseControlLeaseRequest& request) {
  return handleReleaseControlLeaseTyped(context, request);
}

inline std::string CoreRuntime::handleRenewControlLeaseTyped(const RuntimeCommandContext& context, const RenewControlLeaseRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = RenewControlLeaseRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(RenewControlLeaseRequest::kCommand);
  return handleSessionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<RenewControlLeaseRequest>(const RuntimeCommandContext& context, const RenewControlLeaseRequest& request) {
  return handleRenewControlLeaseTyped(context, request);
}

inline std::string CoreRuntime::handleReplayPathTyped(const RuntimeCommandContext& context, const ReplayPathRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = ReplayPathRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(ReplayPathRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<ReplayPathRequest>(const RuntimeCommandContext& context, const ReplayPathRequest& request) {
  return handleReplayPathTyped(context, request);
}

inline std::string CoreRuntime::handleResumeScanTyped(const RuntimeCommandContext& context, const ResumeScanRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = ResumeScanRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(ResumeScanRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<ResumeScanRequest>(const RuntimeCommandContext& context, const ResumeScanRequest& request) {
  return handleResumeScanTyped(context, request);
}

inline std::string CoreRuntime::handleRunRlProjectTyped(const RuntimeCommandContext& context, const RunRlProjectRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = RunRlProjectRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(RunRlProjectRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<RunRlProjectRequest>(const RuntimeCommandContext& context, const RunRlProjectRequest& request) {
  return handleRunRlProjectTyped(context, request);
}

inline std::string CoreRuntime::handleSafeRetreatTyped(const RuntimeCommandContext& context, const SafeRetreatRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = SafeRetreatRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(SafeRetreatRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<SafeRetreatRequest>(const RuntimeCommandContext& context, const SafeRetreatRequest& request) {
  return handleSafeRetreatTyped(context, request);
}

inline std::string CoreRuntime::handleSaveRecordPathTyped(const RuntimeCommandContext& context, const SaveRecordPathRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = SaveRecordPathRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(SaveRecordPathRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<SaveRecordPathRequest>(const RuntimeCommandContext& context, const SaveRecordPathRequest& request) {
  return handleSaveRecordPathTyped(context, request);
}

inline std::string CoreRuntime::handleSeekContactTyped(const RuntimeCommandContext& context, const SeekContactRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = SeekContactRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(SeekContactRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<SeekContactRequest>(const RuntimeCommandContext& context, const SeekContactRequest& request) {
  return handleSeekContactTyped(context, request);
}

inline std::string CoreRuntime::handleSetAutoModeTyped(const RuntimeCommandContext& context, const SetAutoModeRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = SetAutoModeRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(SetAutoModeRequest::kCommand);
  return handlePowerModeCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<SetAutoModeRequest>(const RuntimeCommandContext& context, const SetAutoModeRequest& request) {
  return handleSetAutoModeTyped(context, request);
}

inline std::string CoreRuntime::handleSetManualModeTyped(const RuntimeCommandContext& context, const SetManualModeRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = SetManualModeRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(SetManualModeRequest::kCommand);
  return handlePowerModeCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<SetManualModeRequest>(const RuntimeCommandContext& context, const SetManualModeRequest& request) {
  return handleSetManualModeTyped(context, request);
}

inline std::string CoreRuntime::handleStartProcedureTyped(const RuntimeCommandContext& context, const StartProcedureRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = StartProcedureRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(StartProcedureRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<StartProcedureRequest>(const RuntimeCommandContext& context, const StartProcedureRequest& request) {
  return handleStartProcedureTyped(context, request);
}

inline std::string CoreRuntime::handleStartRecordPathTyped(const RuntimeCommandContext& context, const StartRecordPathRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = StartRecordPathRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(StartRecordPathRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<StartRecordPathRequest>(const RuntimeCommandContext& context, const StartRecordPathRequest& request) {
  return handleStartRecordPathTyped(context, request);
}

inline std::string CoreRuntime::handleStopRecordPathTyped(const RuntimeCommandContext& context, const StopRecordPathRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = StopRecordPathRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(StopRecordPathRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<StopRecordPathRequest>(const RuntimeCommandContext& context, const StopRecordPathRequest& request) {
  return handleStopRecordPathTyped(context, request);
}

inline std::string CoreRuntime::handleStopScanTyped(const RuntimeCommandContext& context, const StopScanRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = StopScanRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(StopScanRequest::kCommand);
  return handleExecutionCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<StopScanRequest>(const RuntimeCommandContext& context, const StopScanRequest& request) {
  return handleStopScanTyped(context, request);
}

inline std::string CoreRuntime::handleValidateScanPlanTyped(const RuntimeCommandContext& context, const ValidateScanPlanRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = ValidateScanPlanRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(ValidateScanPlanRequest::kCommand);
  return handleValidationCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<ValidateScanPlanRequest>(const RuntimeCommandContext& context, const ValidateScanPlanRequest& request) {
  return handleValidateScanPlanTyped(context, request);
}

inline std::string CoreRuntime::handleValidateSetupTyped(const RuntimeCommandContext& context, const ValidateSetupRequest& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = ValidateSetupRequest::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(ValidateSetupRequest::kCommand);
  return handleValidationCommand(invocation);
}

template <> inline std::string CoreRuntime::handleTypedCommand<ValidateSetupRequest>(const RuntimeCommandContext& context, const ValidateSetupRequest& request) {
  return handleValidateSetupTyped(context, request);
}

