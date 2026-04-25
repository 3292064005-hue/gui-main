#include "robot_core/core_runtime.h"

#include "core_runtime_contract_json_helpers.h"
#include "robot_core/core_runtime_contract_publisher.h"
#include "robot_core/robot_family_descriptor.h"
#include "robot_core/robot_identity_contract.h"
#include "robot_core/safety_decision.h"

namespace robot_core {

using namespace contract_json;

std::string CoreRuntime::controlGovernanceContractJsonInternal() const {
  using namespace json;
  const bool session_locked = !state_store_.session_id.empty();
  const bool session_binding_valid = sessionFreezeConsistentLocked();
  const bool rt_ready = state_store_.controller_online && state_store_.powered && state_store_.automatic_mode && state_store_.config.rt_mode == "cartesianImpedance";
  const auto rt_snapshot = procedure_executor_.rt_motion_service.snapshot();
  const auto nrt_snapshot = procedure_executor_.nrt_motion_service.snapshot();
  return object({
      field("single_control_source_required", boolLiteral(state_store_.config.requires_single_control_source)),
      field("live_evidence_bundle_required", boolLiteral(true)),
      field("control_authority_expected_source", quote("cpp_robot_core")),
      field("write_surface", quote("core_runtime_only")),
      field("current_execution_state", quote(stateName(state_store_.execution_state))),
      field("controller_online", boolLiteral(state_store_.controller_online)),
      field("powered", boolLiteral(state_store_.powered)),
      field("automatic_mode", boolLiteral(state_store_.automatic_mode)),
      field("session_binding_valid", boolLiteral(session_binding_valid)),
      field("runtime_config_bound", boolLiteral(session_locked)),
      field("session_id", quote(state_store_.session_id)),
      field("active_plan_hash", quote(state_store_.plan_hash)),
      field("locked_scan_plan_hash", quote(state_store_.locked_scan_plan_hash)),
      field("tool_ready", boolLiteral(state_store_.tool_ready)),
      field("tcp_ready", boolLiteral(state_store_.tcp_ready)),
      field("load_ready", boolLiteral(state_store_.load_ready)),
      field("nrt_ready", boolLiteral(state_store_.controller_online && state_store_.powered)),
      field("rt_ready", boolLiteral(rt_ready)),
      field("lifecycle_state", quote(procedure_executor_.sdk_robot.hardwareLifecycleState())),
      field("rt_loop_active", boolLiteral(rt_snapshot.loop_active)),
      field("rt_move_active", boolLiteral(rt_snapshot.move_active)),
      field("rt_quality_gate_passed", boolLiteral(state_store_.rt_jitter_ok)),
      field("nrt_last_command", quote(nrt_snapshot.last_command)),
      field("required_capability_claims", capabilityClaimCatalogJson()),
      field("detail", quote("single control source contract requires session freeze + AUTO + powered + cartesianImpedance mainline with explicit capability claims"))
  });
}

std::string CoreRuntime::controllerEvidenceJsonInternal() const {
  using namespace json;
  const auto logs = procedure_executor_.sdk_robot.controllerLogs();
  const auto cfg_logs = procedure_executor_.sdk_robot.configurationLog();
  std::vector<std::string> log_tail;
  for (const auto& item : logs) {
    log_tail.push_back(object({field("level", quote("INFO")), field("source", quote("sdk")), field("message", quote(item))}));
  }
  std::vector<std::string> cfg_tail;
  for (const auto& item : cfg_logs) {
    cfg_tail.push_back(quote(item));
  }
  const auto rl_status = procedure_executor_.sdk_robot.rlStatus();
  const auto drag = procedure_executor_.sdk_robot.dragState();
  return object({
      field("runtime_source", quote(procedure_executor_.sdk_robot.runtimeSource())),
      field("last_event", quote(stateName(state_store_.execution_state))),
      field("last_transition", quote(state_store_.last_transition)),
      field("state_reason", quote(state_store_.state_reason)),
      field("last_controller_log", quote(logs.empty() ? std::string("") : logs.back())),
      field("controller_log_tail", objectArray(log_tail)),
      field("configuration_log_tail", stringArray(cfg_logs)),
      field("rl_status", object({field("loaded_project", quote(rl_status.loaded_project)), field("loaded_task", quote(rl_status.loaded_task)), field("running", boolLiteral(rl_status.running)), field("rate", formatDouble(rl_status.rate)), field("loop", boolLiteral(rl_status.loop))})),
      field("drag_state", object({field("enabled", boolLiteral(drag.enabled)), field("space", quote(drag.space)), field("type", quote(drag.type))})),
      field("registers", object({field("segment", std::to_string(state_store_.active_segment)), field("frame", std::to_string(state_store_.frame_id)), field("command_sequence", std::to_string(procedure_executor_.sdk_robot.commandSequence()))})),
      field("fault_code", quote(state_store_.fault_code)),
      field("pending_alarm_count", std::to_string(static_cast<int>(evidence_projector_.pending_alarms.size()))),
      field("last_nrt_profile", quote(procedure_executor_.nrt_motion_service.snapshot().active_profile)),
      field("last_rt_phase", quote(procedure_executor_.rt_motion_service.snapshot().phase)),
      field("reason_chain", stringArray({stateName(state_store_.execution_state), state_store_.state_reason, state_store_.last_transition, state_store_.fault_code}))
  });
}


}  // namespace robot_core
