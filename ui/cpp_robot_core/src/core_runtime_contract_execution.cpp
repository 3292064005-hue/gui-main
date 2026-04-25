#include "robot_core/core_runtime.h"

#include "core_runtime_contract_json_helpers.h"
#include "robot_core/core_runtime_contract_publisher.h"
#include "robot_core/robot_family_descriptor.h"
#include "robot_core/robot_identity_contract.h"
#include "robot_core/safety_decision.h"

namespace robot_core {

using namespace contract_json;

std::string CoreRuntime::dualStateMachineContractJsonLocked() const {
  using namespace json;
  const std::string runtime_state = stateName(state_store_.execution_state);
  std::string clinical_state = "boot";
  if (runtime_state == "CONNECTED" || runtime_state == "POWERED" || runtime_state == "AUTO_READY") clinical_state = "startup";
  else if (runtime_state == "SESSION_LOCKED") clinical_state = "session_locked";
  else if (runtime_state == "PATH_VALIDATED") clinical_state = "plan_validated";
  else if (runtime_state == "APPROACHING") clinical_state = "approaching";
  else if (runtime_state == "CONTACT_SEEKING") clinical_state = "seek_contact";
  else if (runtime_state == "CONTACT_STABLE") clinical_state = "contact_stable";
  else if (runtime_state == "SCANNING") clinical_state = "scan_follow";
  else if (runtime_state == "PAUSED_HOLD") clinical_state = "paused_hold";
  else if (runtime_state == "RETREATING" || runtime_state == "RECOVERY_RETRACT") clinical_state = "controlled_retract";
  else if (runtime_state == "SCAN_COMPLETE") clinical_state = "completed";
  else if (runtime_state == "FAULT") clinical_state = "fault";
  else if (runtime_state == "ESTOP") clinical_state = "estop";
  const bool aligned = !(runtime_state == "SCANNING" && clinical_state != "scan_follow");
  return object({
      field("summary_state", quote(aligned ? std::string("ready") : std::string("blocked"))),
      field("summary_label", quote(aligned ? std::string("双层状态机已对齐") : std::string("双层状态机冲突"))),
      field("detail", quote(aligned ? std::string("执行状态机与临床任务状态机已通过映射规则对齐。") : std::string("runtime 与 clinical task state 不一致。"))),
      field("runtime_state", quote(runtime_state)),
      field("clinical_task_state", quote(clinical_state)),
      field("execution_and_clinical_aligned", boolLiteral(aligned)),
      field("execution_permissions", object({
          field("allow_nrt", boolLiteral(state_store_.execution_state == RobotCoreState::AutoReady || state_store_.execution_state == RobotCoreState::SessionLocked || state_store_.execution_state == RobotCoreState::PathValidated || state_store_.execution_state == RobotCoreState::ScanComplete)),
          field("allow_rt_seek", boolLiteral(state_store_.execution_state == RobotCoreState::PathValidated || state_store_.execution_state == RobotCoreState::Approaching || state_store_.execution_state == RobotCoreState::ContactSeeking)),
          field("allow_rt_scan", boolLiteral(state_store_.execution_state == RobotCoreState::ContactStable || state_store_.execution_state == RobotCoreState::Scanning || state_store_.execution_state == RobotCoreState::PausedHold)),
          field("allow_retract", boolLiteral(state_store_.execution_state != RobotCoreState::Boot && state_store_.execution_state != RobotCoreState::Disconnected && state_store_.execution_state != RobotCoreState::Estop))
      }))
  });
}

std::string CoreRuntime::mainlineExecutorContractJsonLocked() const {
  using namespace json;
  const auto rt = procedure_executor_.rt_motion_service.snapshot();
  const auto nrt = procedure_executor_.nrt_motion_service.snapshot();
  std::vector<std::string> templates;
  for (const auto& profile : nrt.templates) {
    templates.push_back(object({field("name", quote(profile.name)), field("sdk_command", quote(profile.sdk_command)), field("blocking", boolLiteral(true)), field("requires_auto_mode", boolLiteral(profile.requires_auto_mode)), field("requires_move_reset", boolLiteral(profile.requires_move_reset)), field("delegates_to_sdk", boolLiteral(profile.delegates_to_sdk))}));
  }
  const bool task_tree_aligned = !(stateName(state_store_.execution_state) == "SCANNING" && rt.phase != "scan_follow");
  return object({
      field("summary_state", quote(task_tree_aligned ? std::string("ready") : std::string("blocked"))),
      field("summary_label", quote(task_tree_aligned ? std::string("主线执行器已对齐") : std::string("主线执行器未对齐"))),
      field("detail", quote("NRT/RT executor 只表达意图、阶段与监测器；真实执行委托给官方 SDK。")),
      field("task_tree_aligned", boolLiteral(task_tree_aligned)),
      field("nrt_executor", object({
          field("summary_state", quote(nrt.degraded_without_sdk ? std::string("warning") : std::string("ready"))),
          field("detail", quote("NRT executor delegates MoveAbsJ/MoveL templates to the official SDK planner.")),
          field("sdk_delegation_only", boolLiteral(nrt.sdk_delegation_only)),
          field("requires_move_reset", boolLiteral(nrt.requires_move_reset)),
          field("requires_single_control_source", boolLiteral(nrt.requires_single_control_source)),
          field("last_command_id", quote(nrt.last_command_id)),
          field("last_result", quote(nrt.last_result)),
          field("templates", objectArray(templates))
      })),
      field("rt_executor", object({
          field("summary_state", quote(rt.degraded_without_sdk ? std::string("warning") : std::string("ready"))),
          field("detail", quote("RT executor wraps cartesianImpedance mainline with limiter/guard semantics.")),
          field("phase", quote(rt.phase)),
          field("phase_group", quote(rt.phase_group)),
          field("reference_limiter_enabled", boolLiteral(rt.reference_limiter_enabled)),
          field("freshness_guard_enabled", boolLiteral(rt.freshness_guard_enabled)),
          field("jitter_monitor_enabled", boolLiteral(rt.jitter_monitor_enabled)),
          field("contact_band_monitor_enabled", boolLiteral(rt.contact_band_monitor_enabled)),
          field("network_guard_enabled", boolLiteral(rt.network_guard_enabled)),
          field("fixed_period_enforced", boolLiteral(rt.fixed_period_enforced)),
          field("network_healthy", boolLiteral(rt.network_healthy)),
          field("overrun_count", std::to_string(rt.overrun_count)),
          field("nominal_loop_hz", std::to_string(rt.nominal_loop_hz))
      }))
  });
}

}  // namespace robot_core
