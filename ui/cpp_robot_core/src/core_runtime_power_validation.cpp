#include "robot_core/core_runtime.h"

#include <functional>
#include <unordered_map>

#include "json_utils.h"

namespace robot_core {

std::string CoreRuntime::handlePowerModeCommand(const RuntimeCommandInvocation& invocation) {
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  const auto& command = invocation.command;
  using PowerHandler = std::function<std::string(CoreRuntime*, const RuntimeCommandInvocation&)>;
  static const std::unordered_map<std::string, PowerHandler> handlers = {
      {"power_on", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<PowerOnRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: power_on");
         }
         (void)request;
         if (!self->state_store_.controller_online) {
           return self->replyJson(inv.request_id, false, "robot not connected");
         }
         if (!self->procedure_executor_.sdk_robot.lifecyclePort().setPower(true)) {
           return self->replyJson(inv.request_id, false, "power_on failed");
         }
         self->state_store_.powered = true;
         self->state_store_.execution_state = RobotCoreState::Powered;
         return self->replyJson(inv.request_id, true, "power_on accepted");
       }},
      {"power_off", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<PowerOffRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: power_off");
         }
         (void)request;
         if (self->state_store_.controller_online && !self->procedure_executor_.sdk_robot.lifecyclePort().setPower(false)) {
           return self->replyJson(inv.request_id, false, "power_off failed");
         }
         self->state_store_.powered = false;
         self->state_store_.automatic_mode = false;
         self->state_store_.execution_state = self->state_store_.controller_online ? RobotCoreState::Connected : RobotCoreState::Disconnected;
         return self->replyJson(inv.request_id, true, "power_off accepted");
       }},
      {"set_auto_mode", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<SetAutoModeRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: set_auto_mode");
         }
         (void)request;
         if (!self->state_store_.powered) {
           return self->replyJson(inv.request_id, false, "robot not powered");
         }
         if (!self->procedure_executor_.sdk_robot.lifecyclePort().setAutoMode()) {
           return self->replyJson(inv.request_id, false, "set_auto_mode failed");
         }
         self->state_store_.automatic_mode = true;
         self->state_store_.execution_state = RobotCoreState::AutoReady;
         return self->replyJson(inv.request_id, true, "set_auto_mode accepted");
       }},
      {"set_manual_mode", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<SetManualModeRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: set_manual_mode");
         }
         (void)request;
         if (self->state_store_.controller_online) {
           self->procedure_executor_.sdk_robot.lifecyclePort().setManualMode();
         }
         self->state_store_.automatic_mode = false;
         self->state_store_.execution_state = self->state_store_.powered ? RobotCoreState::Powered : RobotCoreState::Connected;
         return self->replyJson(inv.request_id, true, "set_manual_mode accepted");
       }},
  };
  const auto it = handlers.find(command);
  if (it == handlers.end()) {
    return replyJson(invocation.request_id, false, "unsupported command: " + command);
  }
  return it->second(this, invocation);
}

std::string CoreRuntime::handleValidationCommand(const RuntimeCommandInvocation& invocation) {
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  const auto& command = invocation.command;
  using ValidationHandler = std::function<std::string(CoreRuntime*, const RuntimeCommandInvocation&)>;
  static const std::unordered_map<std::string, ValidationHandler> handlers = {
      {"validate_setup", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ValidateSetupRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: validate_setup");
         }
         (void)request;
         const auto safety = self->evaluateSafetyLocked();
         const auto data_json = json::object({
             json::field("safe_to_arm", json::boolLiteral(safety.safe_to_arm)),
             json::field("safe_to_scan", json::boolLiteral(safety.safe_to_scan)),
             json::field("active_interlocks", json::stringArray(safety.active_interlocks)),
         });
         return self->replyJson(inv.request_id, safety.safe_to_arm, safety.safe_to_arm ? "setup validated" : "setup invalid", data_json);
       }},
      {"validate_scan_plan", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ValidateScanPlanRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: validate_scan_plan");
         }
         const auto verdict = self->compileScanPlanVerdictLocked(
             request->config_snapshot.value_or("{}"),
             request->scan_plan,
             request->scan_plan_hash.value_or(""));
         self->evidence_projector_.last_final_verdict = verdict;
         const auto verdict_json = self->finalVerdictJson(verdict);
         return self->replyJson(inv.request_id, verdict.accepted, verdict.accepted ? "validate_scan_plan accepted" : "validate_scan_plan rejected", json::object({json::field("final_verdict", verdict_json), json::field("canonical_command", json::quote("validate_scan_plan"))}));
       }},
      {"query_final_verdict", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<QueryFinalVerdictRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: query_final_verdict");
         }
         (void)request;
         const auto verdict_json = self->finalVerdictJson(self->evidence_projector_.last_final_verdict);
         return self->replyJson(inv.request_id, true, "final verdict snapshot", json::object({json::field("final_verdict", verdict_json)}));
       }},
  };
  const auto it = handlers.find(command);
  if (it == handlers.end()) {
    return replyJson(invocation.request_id, false, "unsupported command: " + command);
  }
  return it->second(this, invocation);
}

}  // namespace robot_core
