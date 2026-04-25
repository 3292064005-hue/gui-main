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
  state_store_.frozen_device_roster_json = request.device_roster;
  state_store_.frozen_safety_thresholds_json = request.safety_thresholds.empty() ? std::string("{}") : request.safety_thresholds;
  state_store_.frozen_device_health_snapshot_json = request.device_health_snapshot.empty() ? std::string("{}") : request.device_health_snapshot;
  state_store_.frozen_session_freeze_policy_json = request.session_freeze_policy.value_or(std::string("{}"));
  const auto policy_json = state_store_.frozen_session_freeze_policy_json.empty() ? std::string("{}") : state_store_.frozen_session_freeze_policy_json;
  state_store_.strict_runtime_freeze_gate = normalizeFreezeGateMode(
      request.strict_runtime_freeze_gate.value_or(json::extractString(policy_json, "strict_runtime_freeze_gate", state_store_.config.strict_runtime_freeze_gate)));
  state_store_.frozen_execution_critical_fields = uniqueStrings(json::extractStringArray(policy_json, "execution_critical_fields", {"device_roster", "safety_thresholds", "device_health_snapshot"}));
  if (state_store_.frozen_execution_critical_fields.empty()) {
    state_store_.frozen_execution_critical_fields = {"device_roster", "safety_thresholds", "device_health_snapshot"};
  }
  state_store_.frozen_evidence_only_fields = uniqueStrings(json::extractStringArray(policy_json, "evidence_only_fields", {}));
  state_store_.frozen_recheck_on_start_procedure = json::extractBool(policy_json, "recheck_on_start_procedure", true);
}

void CoreRuntime::clearSessionFreezeInputsLocked() {
  state_store_.strict_runtime_freeze_gate = normalizeFreezeGateMode(state_store_.config.strict_runtime_freeze_gate);
  state_store_.frozen_device_roster_json.clear();
  state_store_.frozen_safety_thresholds_json.clear();
  state_store_.frozen_device_health_snapshot_json.clear();
  state_store_.frozen_session_freeze_policy_json.clear();
  state_store_.frozen_execution_critical_fields.clear();
  state_store_.frozen_evidence_only_fields.clear();
  state_store_.frozen_recheck_on_start_procedure = true;
}

void CoreRuntime::appendSessionFreezeGateIssuesLocked(std::vector<std::string>* blockers, std::vector<std::string>* warnings, bool recheck_live_state) const {
  const auto mode = normalizeFreezeGateMode(state_store_.strict_runtime_freeze_gate);
  if (mode == "off") return;
  if (state_store_.session_id.empty() || state_store_.session_dir.empty()) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze gate missing session binding");
    return;
  }
  if (containsField(state_store_.frozen_execution_critical_fields, "device_roster")) {
    if (state_store_.frozen_device_roster_json.empty() || state_store_.frozen_device_roster_json == "{}") {
      appendFreezeIssue(mode, blockers, warnings, "session freeze missing device_roster");
    } else {
      for (const auto& device_name : {std::string("robot"), std::string("camera"), std::string("ultrasound"), std::string("pressure")}) {
        if (!hasJsonKey(state_store_.frozen_device_roster_json, device_name)) {
          appendFreezeIssue(mode, blockers, warnings, std::string("session freeze device_roster missing ") + device_name);
        }
      }
    }
  }
  if (containsField(state_store_.frozen_execution_critical_fields, "safety_thresholds")) {
    if (state_store_.frozen_safety_thresholds_json.empty() || state_store_.frozen_safety_thresholds_json == "{}") {
      appendFreezeIssue(mode, blockers, warnings, "session freeze missing safety_thresholds");
    } else if (!hasJsonKey(state_store_.frozen_safety_thresholds_json, "desired_contact_force_n") && !hasJsonKey(state_store_.frozen_safety_thresholds_json, "max_z_force_n")) {
      appendFreezeIssue(mode, blockers, warnings, "session freeze safety_thresholds missing force guard keys");
    }
  }
  if (containsField(state_store_.frozen_execution_critical_fields, "device_health_snapshot")) {
    if (state_store_.frozen_device_health_snapshot_json.empty() || state_store_.frozen_device_health_snapshot_json == "{}") {
      appendFreezeIssue(mode, blockers, warnings, "session freeze missing device_health_snapshot");
    } else if (!hasJsonKey(state_store_.frozen_device_health_snapshot_json, "robot")) {
      appendFreezeIssue(mode, blockers, warnings, "session freeze device_health_snapshot missing robot facts");
    }
  }
  if (!(state_store_.tool_ready && state_store_.tcp_ready && state_store_.load_ready)) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze lost tool/tcp/load readiness");
  }
  if (!state_store_.locked_scan_plan_hash.empty() && !state_store_.plan_hash.empty() && state_store_.locked_scan_plan_hash != state_store_.plan_hash) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze plan_hash drift detected");
  }
  if (!recheck_live_state || !state_store_.frozen_recheck_on_start_procedure) return;
  const auto& query = procedure_executor_.sdk_robot.queryPort();
  if (!query.liveBindingEstablished()) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze gate degraded: live binding is not established");
    return;
  }
  if (state_store_.config.requires_single_control_source && !query.controlSourceExclusive()) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze lost single-control-source exclusivity");
  }
  if (!query.networkHealthy()) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze detected unhealthy runtime network");
  }
  const auto runtime_cfg = query.runtimeConfig();
  if (!state_store_.config.remote_ip.empty() && runtime_cfg.remote_ip != state_store_.config.remote_ip) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze remote_ip drift detected");
  }
  if (!state_store_.config.local_ip.empty() && runtime_cfg.local_ip != state_store_.config.local_ip) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze local_ip drift detected");
  }
  if (runtime_cfg.robot_model != state_store_.config.robot_model || runtime_cfg.sdk_robot_class != state_store_.config.sdk_robot_class || runtime_cfg.axis_count != state_store_.config.axis_count) {
    appendFreezeIssue(mode, blockers, warnings, "session freeze robot identity drift detected");
  }
}

bool CoreRuntime::sessionFreezeGateEnforcedLocked() const {
  return normalizeFreezeGateMode(state_store_.strict_runtime_freeze_gate) == "enforce";
}

bool CoreRuntime::sessionFreezeConsistentLocked() const {
  std::vector<std::string> blockers;
  appendSessionFreezeGateIssuesLocked(&blockers, nullptr, true);
  return blockers.empty();
}

}  // namespace robot_core
