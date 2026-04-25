#include "robot_core/core_runtime.h"

#include <algorithm>
#include <filesystem>
#include <functional>
#include <unordered_map>

#include "json_utils.h"
#include "core_runtime_command_helpers.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {


std::vector<std::string> CoreRuntime::allowedClaimsForRoleLocked(const std::string& role) const {
  const auto normalized_role = normalizeAuthorityToken(role, "read_only");
  if (normalized_role == "operator" || normalized_role == "admin" || normalized_role == "service") {
    return {"control_authority_write", "hardware_lifecycle_write", "runtime_validation", "plan_compile", "session_freeze_write", "nrt_motion_write", "rt_motion_write", "recovery_write", "fault_injection_write"};
  }
  if (normalized_role == "researcher" || normalized_role == "qa" || normalized_role == "review") {
    return {"plan_compile", "runtime_read"};
  }
  if (normalized_role == "reviewer" || normalized_role == "read_only") {
    return {"runtime_read"};
  }
  return {"runtime_read"};
}

bool CoreRuntime::roleCanClaimLocked(const std::string& role, const std::string& claim) const {
  const auto normalized_claim = normalizeAuthorityToken(claim, "");
  if (normalized_claim.empty()) return true;
  const auto allowed = allowedClaimsForRoleLocked(role);
  return std::find(allowed.begin(), allowed.end(), normalized_claim) != allowed.end();
}

std::string CoreRuntime::makeRuntimeLeaseIdLocked(const RuntimeCommandContext& context) const {
  const auto seed = context.actor_id + "|" + context.workspace + "|" + context.role + "|" + context.session_id + "|" + std::to_string(json::nowNs());
  const auto digest = std::to_string(std::hash<std::string>{}(seed));
  return digest.size() > 16 ? digest.substr(0, 16) : digest;
}

void CoreRuntime::bindAuthoritySessionLocked(const std::string& session_id) {
  if (!authority_kernel_.lease.active) return;
  authority_kernel_.lease.session_id = session_id;
  authority_kernel_.lease.refreshed_ts_ns = json::nowNs();
}

void CoreRuntime::clearAuthoritySessionBindingLocked() {
  if (!authority_kernel_.lease.active) return;
  authority_kernel_.lease.session_id.clear();
  authority_kernel_.lease.refreshed_ts_ns = json::nowNs();
}

bool CoreRuntime::authorizeInvocationLocked(const RuntimeCommandInvocation& invocation, std::string* error) {
  const auto command = invocation.command;
  const auto command_claim = command == "acquire_control_lease" || command == "renew_control_lease" || command == "release_control_lease"
                                 ? std::string("control_authority_write")
                                 : commandCapabilityClaim(command);
  const bool requires_authority = isWriteCommand(command) || command_claim == "plan_compile";
  if (!requires_authority) {
    return true;
  }

  const auto& context = invocation.context();
  const auto actor_id = normalizeAuthorityToken(context.actor_id, "implicit-operator");
  const auto workspace = normalizeAuthorityToken(context.workspace, "desktop");
  const auto role = normalizeAuthorityToken(context.role, "operator");
  const auto session_id = context.session_id;
  const auto lease_id = context.lease_id;

  if (!roleCanClaimLocked(role, command_claim)) {
    if (error != nullptr) *error = "角色 " + role + " 无权获取 capability claim: " + command_claim;
    return false;
  }

  if (command == "acquire_control_lease" || command == "renew_control_lease" || command == "release_control_lease") {
    return true;
  }

  if (!authority_kernel_.lease.active) {
    if (context.lease_required && !context.auto_issue_implicit_lease) {
      if (error != nullptr) *error = "当前命令要求显式控制权租约。";
      return false;
    }
    authority_kernel_.lease.active = true;
    authority_kernel_.lease.lease_id = makeRuntimeLeaseIdLocked(context);
    authority_kernel_.lease.actor_id = actor_id;
    authority_kernel_.lease.workspace = workspace;
    authority_kernel_.lease.role = role;
    authority_kernel_.lease.session_id = session_id;
    authority_kernel_.lease.source = normalizeAuthorityToken(context.source, "runtime_command");
    authority_kernel_.lease.intent_reason = normalizeAuthorityToken(context.intent_reason, command);
    authority_kernel_.lease.deployment_profile = normalizeAuthorityToken(context.profile, "dev");
    authority_kernel_.lease.acquired_ts_ns = json::nowNs();
    authority_kernel_.lease.refreshed_ts_ns = authority_kernel_.lease.acquired_ts_ns;
    authority_kernel_.lease.granted_claims.insert(command_claim);
  }

  if (!lease_id.empty() && lease_id != authority_kernel_.lease.lease_id) {
    if (error != nullptr) *error = "lease_id 不匹配，active=" + authority_kernel_.lease.lease_id;
    return false;
  }
  if (authority_kernel_.lease.actor_id != actor_id || authority_kernel_.lease.workspace != workspace || authority_kernel_.lease.role != role) {
    if (error != nullptr) *error = "控制权已被 " + authority_kernel_.lease.actor_id + "@" + authority_kernel_.lease.workspace + "/" + authority_kernel_.lease.role + " 持有，当前请求为 " + actor_id + "@" + workspace + "/" + role;
    return false;
  }
  if (!authority_kernel_.lease.session_id.empty() && !session_id.empty() && authority_kernel_.lease.session_id != session_id) {
    if (error != nullptr) *error = "session 绑定冲突，active=" + authority_kernel_.lease.session_id + ", requested=" + session_id;
    return false;
  }

  authority_kernel_.lease.refreshed_ts_ns = json::nowNs();
  authority_kernel_.lease.source = normalizeAuthorityToken(context.source, authority_kernel_.lease.source.empty() ? std::string("runtime_command") : authority_kernel_.lease.source);
  authority_kernel_.lease.intent_reason = normalizeAuthorityToken(context.intent_reason, authority_kernel_.lease.intent_reason.empty() ? command : authority_kernel_.lease.intent_reason);
  authority_kernel_.lease.deployment_profile = normalizeAuthorityToken(context.profile, authority_kernel_.lease.deployment_profile.empty() ? std::string("dev") : authority_kernel_.lease.deployment_profile);
  if (!session_id.empty()) authority_kernel_.lease.session_id = session_id;
  authority_kernel_.lease.granted_claims.insert(command_claim);
  for (const auto& claim : context.requested_claims) {
    if (roleCanClaimLocked(role, claim)) authority_kernel_.lease.granted_claims.insert(claim);
  }
  return true;
}


}  // namespace robot_core
