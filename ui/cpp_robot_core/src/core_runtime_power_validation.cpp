#include "robot_core/core_runtime.h"

#include "json_utils.h"

namespace robot_core {

std::string CoreRuntime::handlePowerModeCommand(const std::string& request_id, const std::string& line) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto command = json::extractString(line, "command");
  if (command == "power_on") {
    if (!controller_online_) {
      return replyJson(request_id, false, "robot not connected");
    }
    if (!sdk_robot_.lifecyclePort().setPower(true)) {
      return replyJson(request_id, false, "power_on failed");
    }
    powered_ = true;
    execution_state_ = RobotCoreState::Powered;
    return replyJson(request_id, true, "power_on accepted");
  }
  if (command == "power_off") {
    if (controller_online_ && !sdk_robot_.lifecyclePort().setPower(false)) {
      return replyJson(request_id, false, "power_off failed");
    }
    powered_ = false;
    automatic_mode_ = false;
    execution_state_ = controller_online_ ? RobotCoreState::Connected : RobotCoreState::Disconnected;
    return replyJson(request_id, true, "power_off accepted");
  }
  if (command == "set_auto_mode") {
    if (!powered_) {
      return replyJson(request_id, false, "robot not powered");
    }
    if (!sdk_robot_.lifecyclePort().setAutoMode()) {
      return replyJson(request_id, false, "set_auto_mode failed");
    }
    automatic_mode_ = true;
    execution_state_ = RobotCoreState::AutoReady;
    return replyJson(request_id, true, "set_auto_mode accepted");
  }
  if (command == "set_manual_mode") {
    if (controller_online_) {
      sdk_robot_.lifecyclePort().setManualMode();
    }
    automatic_mode_ = false;
    execution_state_ = powered_ ? RobotCoreState::Powered : RobotCoreState::Connected;
    return replyJson(request_id, true, "set_manual_mode accepted");
  }
  return replyJson(request_id, false, "unsupported command: " + command);
}

std::string CoreRuntime::handleValidationCommand(const std::string& request_id, const std::string& line) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto command = json::extractString(line, "command");
  if (command == "validate_setup") {
    const auto safety = evaluateSafetyLocked();
    const auto data_json = json::object({
        json::field("safe_to_arm", json::boolLiteral(safety.safe_to_arm)),
        json::field("safe_to_scan", json::boolLiteral(safety.safe_to_scan)),
        json::field("active_interlocks", json::stringArray(safety.active_interlocks)),
    });
    return replyJson(request_id, safety.safe_to_arm, safety.safe_to_arm ? "setup validated" : "setup invalid", data_json);
  }
  if (command == "compile_scan_plan") {
    const auto verdict = compileScanPlanVerdictLocked(line);
    last_final_verdict_ = verdict;
    const auto verdict_json = finalVerdictJson(verdict);
    return replyJson(request_id, verdict.accepted, verdict.accepted ? "compile_scan_plan accepted" : "compile_scan_plan rejected", json::object({json::field("final_verdict", verdict_json)}));
  }
  if (command == "query_final_verdict") {
    const auto verdict_json = finalVerdictJson(last_final_verdict_);
    return replyJson(request_id, true, "final verdict snapshot", json::object({json::field("final_verdict", verdict_json)}));
  }
  return replyJson(request_id, false, "unsupported command: " + command);
}

}  // namespace robot_core
