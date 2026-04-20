#include "robot_core/core_runtime.h"

#include <algorithm>
#include <cctype>
#include <set>

#include "json_utils.h"

namespace robot_core {
namespace {

bool hasJsonKey(const std::string& json_blob, const std::string& key) {
  return !json::extractString(json_blob, key, "").empty() ||
         json::extractBool(json_blob, key, false) ||
         json::extractInt(json_blob, key, 0) != 0 ||
         json::extractDouble(json_blob, key, 0.0) != 0.0 ||
         json_blob.find("\"" + key + "\"") != std::string::npos;
}

std::string normalizeFreezeGateMode(std::string value) {
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
  if (value == "off" || value == "warn" || value == "enforce") return value;
  return "enforce";
}

void appendFreezeIssue(const std::string& mode, std::vector<std::string>* blockers, std::vector<std::string>* warnings, const std::string& message) {
  if (mode == "warn") {
    if (warnings != nullptr) warnings->push_back(message);
    return;
  }
  if (blockers != nullptr) blockers->push_back(message);
}

std::vector<std::string> uniqueStrings(const std::vector<std::string>& values) {
  std::vector<std::string> out;
  std::set<std::string> seen;
  for (auto value : values) {
    if (value.empty()) continue;
    std::transform(value.begin(), value.end(), value.begin(), [](unsigned char c) { return static_cast<char>(std::tolower(c)); });
    if (seen.insert(value).second) out.push_back(value);
  }
  return out;
}

bool containsField(const std::vector<std::string>& values, const std::string& key) {
  return std::find(values.begin(), values.end(), key) != values.end();
}

}  // namespace

void CoreRuntime::captureSessionFreezeInputsLocked(const LockSessionRequest& request) {
  frozen_device_roster_json_ = request.device_roster;
  frozen_safety_thresholds_json_ = request.safety_thresholds.empty() ? std::string("{}") : request.safety_thresholds;
  frozen_device_health_snapshot_json_ = request.device_health_snapshot.empty() ? std::string("{}") : request.device_health_snapshot;
  frozen_session_freeze_policy_json_ = request.session_freeze_policy.value_or(std::string("{}"));
  const auto policy_json = frozen_session_freeze_policy_json_.empty() ? std::string("{}") : frozen_session_freeze_policy_json_;
  strict_runtime_freeze_gate_ = normalizeFreezeGateMode(
      request.strict_runtime_freeze_gate.value_or(json::extractString(policy_json, "strict_runtime_freeze_gate", config_.strict_runtime_freeze_gate)));
  frozen_execution_critical_fields_ = uniqueStrings(json::extractStringArray(policy_json, "execution_critical_fields", {"device_roster", "safety_thresholds", "device_health_snapshot"}));
  if (frozen_execution_critical_fields_.empty()) {
    frozen_execution_critical_fields_ = {"device_roster", "safety_thresholds", "device_health_snapshot"};
  }
  frozen_evidence_only_fields_ = uniqueStrings(json::extractStringArray(policy_json, "evidence_only_fields", {}));
  frozen_recheck_on_start_procedure_ = json::extractBool(policy_json, "recheck_on_start_procedure", true);
}

void CoreRuntime::clearSessionFreezeInputsLocked() {
  strict_runtime_freeze_gate_ = normalizeFreezeGateMode(config_.strict_runtime_freeze_gate);
  frozen_device_roster_json_.clear();
  frozen_safety_thresholds_json_.clear();
  frozen_device_health_snapshot_json_.clear();
  frozen_session_freeze_policy_json_.clear();
  frozen_execution_critical_fields_.clear();
  frozen_evidence_only_fields_.clear();
  frozen_recheck_on_start_procedure_ = true;
}

void CoreRuntime::appendSessionFreezeGateIssuesLocked(std::vector<std::string>* blockers, std::vector<std::string>* warnings, bool recheck_live_state) const {
  const auto mode = normalizeFreezeGateMode(strict_runtime_freeze_gate_);
  if (mode == "off") return;
  if (session_id_.empty() || session_dir_.empty()) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze gate missing session binding");
    return;
  }
  if (containsField(frozen_execution_critical_fields_, "device_roster")) {
    if (frozen_device_roster_json_.empty() || frozen_device_roster_json_ == "{}") {
      appendFreezeIssue(mode, blockers, warnings, "session freeze missing device_roster");
    } else {
      for (const auto& device_name : {std::string("robot"), std::string("camera"), std::string("ultrasound"), std::string("pressure")}) {
        if (!hasJsonKey(frozen_device_roster_json_, device_name)) {
          appendFreezeIssue(mode, blockers, warnings, std::string("session freeze device_roster missing ") + device_name);
        }
      }
    }
  }
  if (containsField(frozen_execution_critical_fields_, "safety_thresholds")) {
    if (frozen_safety_thresholds_json_.empty() || frozen_safety_thresholds_json_ == "{}") {
      appendFreezeIssue(mode, blockers, warnings, "session freeze missing safety_thresholds");
    } else if (!hasJsonKey(frozen_safety_thresholds_json_, "desired_contact_force_n") && !hasJsonKey(frozen_safety_thresholds_json_, "max_z_force_n")) {
      appendFreezeIssue(mode, blockers, warnings, "session freeze safety_thresholds missing force guard keys");
    }
  }
  if (containsField(frozen_execution_critical_fields_, "device_health_snapshot")) {
    if (frozen_device_health_snapshot_json_.empty() || frozen_device_health_snapshot_json_ == "{}") {
      appendFreezeIssue(mode, blockers, warnings, "session freeze missing device_health_snapshot");
    } else if (!hasJsonKey(frozen_device_health_snapshot_json_, "robot")) {
      appendFreezeIssue(mode, blockers, warnings, "session freeze device_health_snapshot missing robot facts");
    }
  }
  if (!(tool_ready_ && tcp_ready_ && load_ready_)) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze lost tool/tcp/load readiness");
  }
  if (!locked_scan_plan_hash_.empty() && !plan_hash_.empty() && locked_scan_plan_hash_ != plan_hash_) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze plan_hash drift detected");
  }
  if (!recheck_live_state || !frozen_recheck_on_start_procedure_) return;
  const auto& query = sdk_robot_.queryPort();
  if (!query.liveBindingEstablished()) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze gate degraded: live binding is not established");
    return;
  }
  if (config_.requires_single_control_source && !query.controlSourceExclusive()) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze lost single-control-source exclusivity");
  }
  if (!query.networkHealthy()) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze detected unhealthy runtime network");
  }
  const auto runtime_cfg = query.runtimeConfig();
  if (!config_.remote_ip.empty() && runtime_cfg.remote_ip != config_.remote_ip) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze remote_ip drift detected");
  }
  if (!config_.local_ip.empty() && runtime_cfg.local_ip != config_.local_ip) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze local_ip drift detected");
  }
  if (runtime_cfg.robot_model != config_.robot_model || runtime_cfg.sdk_robot_class != config_.sdk_robot_class || runtime_cfg.axis_count != config_.axis_count) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze robot identity drift detected");
  }
}

bool CoreRuntime::sessionFreezeGateEnforcedLocked() const {
  return normalizeFreezeGateMode(strict_runtime_freeze_gate_) == "enforce";
}

bool CoreRuntime::sessionFreezeConsistentLocked() const {
  std::vector<std::string> blockers;
  appendSessionFreezeGateIssuesLocked(&blockers, nullptr, true);
  return blockers.empty();
}

}  // namespace robot_core
