#include "robot_core/core_runtime.h"

#include <unordered_map>

namespace robot_core {

std::string CoreRuntime::handleContractQueryCommandLocked(const RuntimeCommandInvocation& invocation) {
  using ContractBuilder = std::string (CoreRuntime::*)() const;
  static const std::unordered_map<std::string, ContractBuilder> contract_builders = {
      {"get_robot_family_contract", &CoreRuntime::robotFamilyContractJsonLocked},
      {"get_vendor_boundary_contract", &CoreRuntime::vendorBoundaryContractJsonLocked},
      {"get_session_drift_contract", &CoreRuntime::sessionDriftContractJsonLocked},
      {"get_hardware_lifecycle_contract", &CoreRuntime::hardwareLifecycleContractJsonLocked},
      {"get_rt_kernel_contract", &CoreRuntime::rtKernelContractJsonLocked},
      {"get_authoritative_runtime_envelope", &CoreRuntime::authoritativeRuntimeEnvelopeJsonLocked},
      {"get_control_governance_contract", &CoreRuntime::controlGovernanceContractJsonLocked},
      {"get_controller_evidence", &CoreRuntime::controllerEvidenceJsonLocked},
      {"get_dual_state_machine_contract", &CoreRuntime::dualStateMachineContractJsonLocked},
      {"get_mainline_executor_contract", &CoreRuntime::mainlineExecutorContractJsonLocked},
      {"get_recovery_contract", &CoreRuntime::safetyRecoveryContractJsonLocked},
      {"get_safety_recovery_contract", &CoreRuntime::safetyRecoveryContractJsonLocked},
      {"get_capability_contract", &CoreRuntime::capabilityContractJsonLocked},
      {"get_model_authority_contract", &CoreRuntime::modelAuthorityContractJsonLocked},
      {"get_release_contract", &CoreRuntime::releaseContractJsonLocked},
      {"get_deployment_contract", &CoreRuntime::deploymentContractJsonLocked},
      {"get_fault_injection_contract", &CoreRuntime::faultInjectionContractJsonLocked},
  };
  const auto contract_it = contract_builders.find(invocation.command);
  if (contract_it == contract_builders.end()) {
    return {};
  }
  return replyJson(invocation.request_id, true, invocation.command + " accepted", (this->*(contract_it->second))());
}

}  // namespace robot_core
