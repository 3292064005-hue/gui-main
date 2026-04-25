#include "robot_core/core_runtime.h"

#include "core_runtime_query_json_helpers.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {

using namespace query_json;

std::string CoreRuntime::handleIdentityQueryCommandLocked(const RuntimeCommandInvocation& invocation) {
  const auto& command = invocation.command;
  if (command == "get_identity_contract") {
           const auto* request = invocation.requestAs<GetIdentityContractRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: get_identity_contract");
           }
           (void)request;
           const auto runtime_cfg = this->procedure_executor_.sdk_robot.queryPort().runtimeConfig();
           const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
           const auto data = json::object(std::vector<std::string>{
               json::field("robot_model", json::quote(identity.robot_model)),
               json::field("label", json::quote(identity.label)),
               json::field("sdk_robot_class", json::quote(identity.sdk_robot_class)),
               json::field("axis_count", std::to_string(identity.axis_count)),
               json::field("controller_series", json::quote(identity.controller_series)),
               json::field("controller_version", json::quote(identity.controller_version)),
               json::field("preferred_link", json::quote(identity.preferred_link)),
               json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
               json::field("supported_rt_modes", json::stringArray(identity.supported_rt_modes)),
               json::field("clinical_allowed_modes", json::stringArray(identity.clinical_allowed_modes)),
               json::field("contact_force_target_n", json::formatDouble(runtime_cfg.contact_force_target_n)),
               json::field("scan_force_target_n", json::formatDouble(runtime_cfg.scan_force_target_n)),
               json::field("retract_timeout_ms", json::formatDouble(runtime_cfg.retract_timeout_ms)),
               json::field("cartesian_impedance_limits", vectorJson(identity.cartesian_impedance_limits)),
               json::field("desired_wrench_limits", vectorJson(identity.desired_wrench_limits)),
               json::field("official_dh_parameters", dhArrayJson(identity.official_dh_parameters))
           });
           return this->replyJson(invocation.request_id, true, "get_identity_contract accepted", data);
  }
  if (command == "get_clinical_mainline_contract") {
           const auto* request = invocation.requestAs<GetClinicalMainlineContractRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: get_clinical_mainline_contract");
           }
           (void)request;
           const auto runtime_cfg = this->procedure_executor_.sdk_robot.queryPort().runtimeConfig();
           const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
           const auto data = json::object(std::vector<std::string>{
               json::field("robot_model", json::quote(identity.robot_model)),
               json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
               json::field("required_sequence", json::stringArray({"connect_robot", "power_on", "set_auto_mode", "lock_session", "load_scan_plan", "start_procedure", "safe_retreat"})),
               json::field("runtime_owned_phase_sequence", json::stringArray({"approach_prescan", "seek_contact", "contact_hold", "scan_follow", "controlled_retract"})),
               json::field("single_control_source_required", json::boolLiteral(identity.requires_single_control_source)),
               json::field("preferred_link", json::quote(identity.preferred_link)),
               json::field("rt_loop_hz", std::to_string(1000)),
               json::field("cartesian_impedance_limits", vectorJson(identity.cartesian_impedance_limits)),
               json::field("desired_wrench_limits", vectorJson(identity.desired_wrench_limits))
           });
           return this->replyJson(invocation.request_id, true, "get_clinical_mainline_contract accepted", data);
  }
  if (command == "get_session_freeze") {
           const auto* request = invocation.requestAs<GetSessionFreezeRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: get_session_freeze");
           }
           (void)request;
           const auto data = json::object(std::vector<std::string>{
               json::field("session_locked", json::boolLiteral(!this->state_store_.session_id.empty())),
               json::field("session_id", json::quote(this->state_store_.session_id)),
               json::field("session_dir", json::quote(this->state_store_.session_dir)),
               json::field("locked_at_ns", std::to_string(this->state_store_.session_locked_ts_ns)),
               json::field("plan_hash", json::quote(this->state_store_.plan_hash)),
               json::field("active_segment", std::to_string(this->state_store_.active_segment)),
               json::field("tool_name", json::quote(this->state_store_.config.tool_name)),
               json::field("tcp_name", json::quote(this->state_store_.config.tcp_name)),
               json::field("load_kg", json::formatDouble(this->state_store_.config.load_kg)),
               json::field("rt_mode", json::quote(this->state_store_.config.rt_mode)),
               json::field("cartesian_impedance", vectorJson(this->state_store_.config.cartesian_impedance)),
               json::field("desired_wrench_n", vectorJson(this->state_store_.config.desired_wrench_n)),
               json::field("freeze_consistent", json::boolLiteral(this->sessionFreezeConsistentLocked())),
               json::field("strict_runtime_freeze_gate", json::quote(this->state_store_.strict_runtime_freeze_gate)),
               json::field("session_freeze_policy", json::quote(this->state_store_.frozen_session_freeze_policy_json)),
               json::field("frozen_execution_critical_fields", json::stringArray(this->state_store_.frozen_execution_critical_fields)),
               json::field("frozen_evidence_only_fields", json::stringArray(this->state_store_.frozen_evidence_only_fields)),
               json::field("recheck_on_start_procedure", json::boolLiteral(this->state_store_.frozen_recheck_on_start_procedure)),
               json::field("live_binding_established", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().liveBindingEstablished())),
               json::field("control_source_exclusive", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().controlSourceExclusive())),
               json::field("network_healthy", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().networkHealthy()))
           });
           return this->replyJson(invocation.request_id, true, "get_session_freeze accepted", data);
  }
  return {};
}

}  // namespace robot_core
