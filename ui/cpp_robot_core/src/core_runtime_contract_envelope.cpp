#include "robot_core/core_runtime.h"
#include "robot_core/core_runtime_contract_publisher.h"

#include <algorithm>

#include "json_utils.h"

namespace robot_core {
namespace {

constexpr int kProtocolVersion = 1;

std::string objectArray(const std::vector<std::string>& entries) {
  std::string out = "[";
  for (size_t idx = 0; idx < entries.size(); ++idx) {
    if (idx > 0) out += ",";
    out += entries[idx];
  }
  out += "]";
  return out;
}

std::string summaryEntry(const std::string& name, const std::string& detail) {
  return json::object({json::field("name", json::quote(name)), json::field("detail", json::quote(detail))});
}

}  // namespace

std::string CoreRuntime::faultInjectionContractJsonLocked() const {
  using namespace json;
  const std::vector<std::string> catalog{
      object({field("name", quote("pressure_stale")), field("effect", quote("forces stale telemetry watchdog and estop path")), field("phase_scope", stringArray({"CONTACT_SEEKING", "SCANNING", "PAUSED_HOLD"})), field("recoverable", boolLiteral(false))}),
      object({field("name", quote("rt_jitter_high")), field("effect", quote("marks RT jitter interlock active")), field("phase_scope", stringArray({"CONTACT_SEEKING", "SCANNING", "PAUSED_HOLD"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("overpressure")), field("effect", quote("forces pressure above upper bound and pause/retreat logic")), field("phase_scope", stringArray({"CONTACT_STABLE", "SCANNING"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("collision_event")), field("effect", quote("injects recoverable collision alarm and retreat")), field("phase_scope", stringArray({"APPROACHING", "CONTACT_SEEKING", "SCANNING"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("plan_hash_mismatch")), field("effect", quote("breaks locked plan hash consistency")), field("phase_scope", stringArray({"SESSION_LOCKED", "PATH_VALIDATED"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("estop_latch")), field("effect", quote("forces ESTOP latched state")), field("phase_scope", stringArray({"*"})), field("recoverable", boolLiteral(false))}),
  };
  return object({
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("enabled", boolLiteral(true)),
      field("simulation_only", boolLiteral(true)),
      field("active_injections", stringArray([&](){ std::vector<std::string> items(injected_faults_.begin(), injected_faults_.end()); return items; }())),
      field("catalog", objectArray(catalog))
  });
}

bool CoreRuntime::applyFaultInjectionLocked(const std::string& fault_name, std::string* error_message) {
  if (fault_name.empty()) {
    if (error_message != nullptr) {
      *error_message = "fault_name missing";
    }
    return false;
  }

  injected_faults_.insert(fault_name);
  if (fault_name == "pressure_stale") {
    pressure_fresh_ = false;
    devices_[2].fresh = false;
    queueAlarmLocked("FAULT", "fault_injection", "压力遥测已被注入为 stale", "fault_injection");
    return true;
  }
  if (fault_name == "rt_jitter_high") {
    rt_jitter_ok_ = false;
    queueAlarmLocked("WARNING", "fault_injection", "RT jitter interlock injected", "fault_injection");
    return true;
  }
  if (fault_name == "overpressure") {
    pressure_current_ = std::max(config_.pressure_upper + 0.5, force_limits_.max_z_force_n + 0.5);
    queueAlarmLocked("WARNING", "fault_injection", "Overpressure injected", "fault_injection", "", "safe_retreat");
    return true;
  }
  if (fault_name == "collision_event") {
    execution_state_ = RobotCoreState::Retreating;
    retreat_ticks_remaining_ = std::max(retreat_ticks_remaining_, 10);
    queueAlarmLocked("RECOVERABLE_FAULT", "collision", "模拟碰撞事件", "fault_injection", "", "safe_retreat");
    return true;
  }
  if (fault_name == "plan_hash_mismatch") {
    plan_hash_ = std::string("mismatch:") + (plan_hash_.empty() ? "empty" : plan_hash_);
    return true;
  }
  if (fault_name == "estop_latch") {
    execution_state_ = RobotCoreState::Estop;
    fault_code_ = "ESTOP_INJECTED";
    queueAlarmLocked("FAULT", "fault_injection", "ESTOP latched by fault injection", "fault_injection");
    return true;
  }

  injected_faults_.erase(fault_name);
  if (error_message != nullptr) {
    *error_message = std::string("unsupported fault injection: ") + fault_name;
  }
  return false;
}

void CoreRuntime::clearInjectedFaultsLocked() {
  injected_faults_.clear();
  rt_jitter_ok_ = true;
  pressure_fresh_ = true;
  devices_[2].fresh = devices_[2].online;
  if (execution_state_ == RobotCoreState::Estop && fault_code_ == "ESTOP_INJECTED") {
    if (automatic_mode_ && powered_) {
      execution_state_ = RobotCoreState::AutoReady;
    } else if (powered_) {
      execution_state_ = RobotCoreState::Powered;
    } else if (controller_online_) {
      execution_state_ = RobotCoreState::Connected;
    } else {
      execution_state_ = RobotCoreState::Disconnected;
    }
    fault_code_.clear();
  }
  queueAlarmLocked("INFO", "fault_injection", "fault injections cleared", "fault_injection");
}


std::string CoreRuntime::controlAuthorityJsonLocked() const {
  using namespace json;
  std::vector<std::string> blockers;
  std::vector<std::string> warnings;
  appendMainlineContractIssuesLocked(&blockers, &warnings);
  const std::string authority_state = controller_online_ ? (blockers.empty() ? std::string("ready") : std::string("blocked")) : std::string("degraded");
  std::vector<std::string> blocker_entries;
  blocker_entries.reserve(blockers.size());
  for (const auto& item : blockers) blocker_entries.push_back(summaryEntry("runtime_authority", item));
  std::vector<std::string> warning_entries;
  warning_entries.reserve(warnings.size());
  for (const auto& item : warnings) warning_entries.push_back(summaryEntry("runtime_authority", item));
  const bool has_owner = authority_lease_.active && !authority_lease_.actor_id.empty();
  const auto owner = has_owner
                         ? object({
                               field("actor_id", quote(authority_lease_.actor_id)),
                               field("workspace", quote(authority_lease_.workspace)),
                               field("role", quote(authority_lease_.role)),
                               field("session_id", quote(authority_lease_.session_id)),
                           })
                         : object({});
  const auto active_lease = authority_lease_.active
                                ? object({
                                      field("lease_id", quote(authority_lease_.lease_id)),
                                      field("actor_id", quote(authority_lease_.actor_id)),
                                      field("workspace", quote(authority_lease_.workspace)),
                                      field("role", quote(authority_lease_.role)),
                                      field("session_id", quote(authority_lease_.session_id)),
                                      field("acquired_ts_ns", std::to_string(authority_lease_.acquired_ts_ns)),
                                      field("refreshed_ts_ns", std::to_string(authority_lease_.refreshed_ts_ns)),
                                      field("source", quote(authority_lease_.source.empty() ? std::string("cpp_robot_core") : authority_lease_.source)),
                                      field("deployment_profile", quote(authority_lease_.deployment_profile)),
                                  })
                                : object({});
  const auto summary_label = authority_lease_.active
                                 ? std::string("runtime authority lease active")
                                 : (authority_state == "ready" ? std::string("runtime authority ready")
                                                                : (authority_state == "blocked" ? std::string("runtime authority blocked")
                                                                                                 : std::string("runtime authority degraded")));
  const auto detail = authority_lease_.active
                          ? std::string("cpp_robot_core publishes the active authoritative control lease")
                          : std::string("cpp_robot_core runtime is the single authority source; no active external lease is currently bound");
  const std::vector<std::string> granted_claims = authority_lease_.active
                                                      ? std::vector<std::string>(authority_lease_.granted_claims.begin(), authority_lease_.granted_claims.end())
                                                      : std::vector<std::string>{};
  return object({
      field("summary_state", quote(authority_state)),
      field("summary_label", quote(summary_label)),
      field("detail", quote(detail)),
      field("owner", owner),
      field("active_lease", active_lease),
      field("owner_provenance", object({field("source", quote("cpp_robot_core"))})),
      field("granted_claims", stringArray(granted_claims)),
      field("workspace_binding", quote(authority_lease_.active ? authority_lease_.workspace : std::string("runtime"))),
      field("session_binding", quote(authority_lease_.active ? authority_lease_.session_id : session_id_)),
      field("blockers", objectArray(blocker_entries)),
      field("warnings", objectArray(warning_entries))
  });
}

std::string CoreRuntime::finalVerdictJson(const FinalVerdict& verdict) const {
  using namespace json;
  std::vector<std::string> blocker_entries;
  blocker_entries.reserve(verdict.blockers.size());
  for (const auto& item : verdict.blockers) {
    blocker_entries.push_back(summaryEntry("model_precheck", item));
  }
  std::vector<std::string> warning_entries;
  warning_entries.reserve(verdict.warnings.size());
  for (const auto& item : verdict.warnings) {
    warning_entries.push_back(summaryEntry("model_precheck", item));
  }
  return object({
      field("summary_state", quote(verdict.policy_state.empty() ? std::string("idle") : verdict.policy_state)),
      field("summary_label", quote(verdict.summary_label.empty() ? std::string("运行时前检") : verdict.summary_label)),
      field("detail", quote(verdict.detail.empty() ? verdict.reason : verdict.detail)),
      field("warnings", objectArray(warning_entries)),
      field("blockers", objectArray(blocker_entries)),
      field("authority_source", quote(verdict.source.empty() ? std::string("cpp_robot_core") : verdict.source)),
      field("verdict_kind", quote("final")),
      field("approximate", boolLiteral(false)),
      field("final_verdict", object({
          field("accepted", boolLiteral(verdict.accepted)),
          field("reason", quote(verdict.reason)),
          field("evidence_id", quote(verdict.evidence_id)),
          field("expected_state_delta", object({field("next_state", quote(verdict.next_state.empty() ? std::string("replan_required") : verdict.next_state))})),
          field("policy_state", quote(verdict.policy_state.empty() ? std::string("idle") : verdict.policy_state)),
          field("source", quote(verdict.source.empty() ? std::string("cpp_robot_core") : verdict.source)),
          field("advisory_only", boolLiteral(verdict.advisory_only)),
      })),
      field("plan_metrics", object({
          field("plan_id", quote(verdict.plan_id)),
          field("plan_hash", quote(verdict.plan_hash)),
      })),
  });
}

std::string CoreRuntime::replyJson(const std::string& request_id, bool ok, const std::string& message, const std::string& data_json) const {
  using namespace json;
  return object({
      field("ok", boolLiteral(ok)),
      field("message", quote(message)),
      field("request_id", quote(request_id)),
      field("data", data_json),
      field("protocol_version", std::to_string(kProtocolVersion)),
  });
}


std::string CoreRuntime::controlGovernanceContractJsonLocked() const { return runtime_contract_publisher_->controlGovernanceContractJsonLocked(); }
std::string CoreRuntime::controllerEvidenceJsonLocked() const { return runtime_contract_publisher_->controllerEvidenceJsonLocked(); }
std::string CoreRuntime::releaseContractJsonLocked() const { return runtime_contract_publisher_->releaseContractJsonLocked(); }
std::string CoreRuntime::deploymentContractJsonLocked() const { return runtime_contract_publisher_->deploymentContractJsonLocked(); }
std::string CoreRuntime::authoritativeRuntimeEnvelopeJsonLocked() const { return runtime_contract_publisher_->authoritativeRuntimeEnvelopeJsonLocked(); }

}  // namespace robot_core
