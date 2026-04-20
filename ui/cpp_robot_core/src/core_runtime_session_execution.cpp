#include "robot_core/core_runtime.h"

#include <algorithm>
#include <filesystem>
#include <functional>
#include <unordered_map>

#include "json_utils.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {

namespace {

std::string normalizeAuthorityToken(const std::string& raw, const std::string& fallback) {
  const auto begin = raw.find_first_not_of(" \t\r\n");
  if (begin == std::string::npos) return fallback;
  const auto end = raw.find_last_not_of(" \t\r\n");
  return raw.substr(begin, end - begin + 1);
}

std::string joinClaims(const std::set<std::string>& claims) {
  std::vector<std::string> items(claims.begin(), claims.end());
  return json::stringArray(items);
}

}  // namespace

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
  if (!authority_lease_.active) return;
  authority_lease_.session_id = session_id;
  authority_lease_.refreshed_ts_ns = json::nowNs();
}

void CoreRuntime::clearAuthoritySessionBindingLocked() {
  if (!authority_lease_.active) return;
  authority_lease_.session_id.clear();
  authority_lease_.refreshed_ts_ns = json::nowNs();
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

  if (!authority_lease_.active) {
    if (context.lease_required && !context.auto_issue_implicit_lease) {
      if (error != nullptr) *error = "当前命令要求显式控制权租约。";
      return false;
    }
    authority_lease_.active = true;
    authority_lease_.lease_id = makeRuntimeLeaseIdLocked(context);
    authority_lease_.actor_id = actor_id;
    authority_lease_.workspace = workspace;
    authority_lease_.role = role;
    authority_lease_.session_id = session_id;
    authority_lease_.source = normalizeAuthorityToken(context.source, "runtime_command");
    authority_lease_.intent_reason = normalizeAuthorityToken(context.intent_reason, command);
    authority_lease_.deployment_profile = normalizeAuthorityToken(context.profile, "dev");
    authority_lease_.acquired_ts_ns = json::nowNs();
    authority_lease_.refreshed_ts_ns = authority_lease_.acquired_ts_ns;
    authority_lease_.granted_claims.insert(command_claim);
  }

  if (!lease_id.empty() && lease_id != authority_lease_.lease_id) {
    if (error != nullptr) *error = "lease_id 不匹配，active=" + authority_lease_.lease_id;
    return false;
  }
  if (authority_lease_.actor_id != actor_id || authority_lease_.workspace != workspace || authority_lease_.role != role) {
    if (error != nullptr) *error = "控制权已被 " + authority_lease_.actor_id + "@" + authority_lease_.workspace + "/" + authority_lease_.role + " 持有，当前请求为 " + actor_id + "@" + workspace + "/" + role;
    return false;
  }
  if (!authority_lease_.session_id.empty() && !session_id.empty() && authority_lease_.session_id != session_id) {
    if (error != nullptr) *error = "session 绑定冲突，active=" + authority_lease_.session_id + ", requested=" + session_id;
    return false;
  }

  authority_lease_.refreshed_ts_ns = json::nowNs();
  authority_lease_.source = normalizeAuthorityToken(context.source, authority_lease_.source.empty() ? std::string("runtime_command") : authority_lease_.source);
  authority_lease_.intent_reason = normalizeAuthorityToken(context.intent_reason, authority_lease_.intent_reason.empty() ? command : authority_lease_.intent_reason);
  authority_lease_.deployment_profile = normalizeAuthorityToken(context.profile, authority_lease_.deployment_profile.empty() ? std::string("dev") : authority_lease_.deployment_profile);
  if (!session_id.empty()) authority_lease_.session_id = session_id;
  authority_lease_.granted_claims.insert(command_claim);
  for (const auto& claim : context.requested_claims) {
    if (roleCanClaimLocked(role, claim)) authority_lease_.granted_claims.insert(claim);
  }
  return true;
}

std::string CoreRuntime::handleFaultInjectionCommand(const RuntimeCommandInvocation& invocation) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto& command = invocation.command;
  using FaultHandler = std::function<std::string(CoreRuntime*, const RuntimeCommandInvocation&)>;
  static const std::unordered_map<std::string, FaultHandler> handlers = {
      {"inject_fault", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<InjectFaultRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: inject_fault");
         }
         const auto fault_name = request->fault_name;
         std::string error_message;
         if (!self->applyFaultInjectionLocked(fault_name, &error_message)) {
           return self->replyJson(inv.request_id, false, error_message.empty() ? "fault injection failed" : error_message);
         }
         return self->replyJson(inv.request_id, true, "inject_fault accepted", self->faultInjectionContractJsonLocked());
       }},
      {"clear_injected_faults", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ClearInjectedFaultsRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: clear_injected_faults");
         }
         (void)request;
         self->clearInjectedFaultsLocked();
         return self->replyJson(inv.request_id, true, "clear_injected_faults accepted", self->faultInjectionContractJsonLocked());
       }},
  };
  const auto it = handlers.find(command);
  if (it == handlers.end()) {
    return replyJson(invocation.request_id, false, "unsupported command: " + command);
  }
  return it->second(this, invocation);
}

std::string CoreRuntime::handleSessionCommand(const RuntimeCommandInvocation& invocation) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto& command = invocation.command;
  if (command == "lock_session") {
    const auto* request = invocation.requestAs<LockSessionRequest>();
    if (request == nullptr) {
      return replyJson(invocation.request_id, false, "typed request mismatch: lock_session");
    }
    if (execution_state_ != RobotCoreState::AutoReady) {
      return replyJson(invocation.request_id, false, "core not ready for session lock");
    }
    const auto previous_session_id = session_id_;
    const auto previous_session_dir = session_dir_;
    const auto previous_locked_scan_plan_hash = locked_scan_plan_hash_;
    const auto previous_config = config_;
    const auto previous_tool_ready = tool_ready_;
    const auto previous_tcp_ready = tcp_ready_;
    const auto previous_load_ready = load_ready_;
    const auto previous_session_locked_ts_ns = session_locked_ts_ns_;
    const auto previous_authority_lease = authority_lease_;
    const auto previous_strict_runtime_freeze_gate = strict_runtime_freeze_gate_;
    const auto previous_frozen_device_roster_json = frozen_device_roster_json_;
    const auto previous_frozen_safety_thresholds_json = frozen_safety_thresholds_json_;
    const auto previous_frozen_device_health_snapshot_json = frozen_device_health_snapshot_json_;
    const auto previous_frozen_session_freeze_policy_json = frozen_session_freeze_policy_json_;
    const auto previous_frozen_execution_critical_fields = frozen_execution_critical_fields_;
    const auto previous_frozen_evidence_only_fields = frozen_evidence_only_fields_;
    const auto previous_frozen_recheck_on_start_procedure = frozen_recheck_on_start_procedure_;
    const auto previous_runtime_cfg = sdk_robot_.queryPort().runtimeConfig();
    auto rollback_lock_session = [this,
                                  &previous_session_id,
                                  &previous_session_dir,
                                  &previous_locked_scan_plan_hash,
                                  &previous_config,
                                  &previous_tool_ready,
                                  &previous_tcp_ready,
                                  &previous_load_ready,
                                  &previous_session_locked_ts_ns,
                                  &previous_authority_lease,
                                  &previous_strict_runtime_freeze_gate,
                                  &previous_frozen_device_roster_json,
                                  &previous_frozen_safety_thresholds_json,
                                  &previous_frozen_device_health_snapshot_json,
                                  &previous_frozen_session_freeze_policy_json,
                                  &previous_frozen_execution_critical_fields,
                                  &previous_frozen_evidence_only_fields,
                                  &previous_frozen_recheck_on_start_procedure,
                                  &previous_runtime_cfg]() {
      recording_service_.closeSession();
      config_ = previous_config;
      session_id_ = previous_session_id;
      session_dir_ = previous_session_dir;
      locked_scan_plan_hash_ = previous_locked_scan_plan_hash;
      tool_ready_ = previous_tool_ready;
      tcp_ready_ = previous_tcp_ready;
      load_ready_ = previous_load_ready;
      session_locked_ts_ns_ = previous_session_locked_ts_ns;
      authority_lease_ = previous_authority_lease;
      strict_runtime_freeze_gate_ = previous_strict_runtime_freeze_gate;
      frozen_device_roster_json_ = previous_frozen_device_roster_json;
      frozen_safety_thresholds_json_ = previous_frozen_safety_thresholds_json;
      frozen_device_health_snapshot_json_ = previous_frozen_device_health_snapshot_json;
      frozen_session_freeze_policy_json_ = previous_frozen_session_freeze_policy_json;
      frozen_execution_critical_fields_ = previous_frozen_execution_critical_fields;
      frozen_evidence_only_fields_ = previous_frozen_evidence_only_fields;
      frozen_recheck_on_start_procedure_ = previous_frozen_recheck_on_start_procedure;
      sdk_robot_.rtControlPort().configureMainline(previous_runtime_cfg);
    };
    try {
      session_id_ = request->session_id;
      session_dir_ = request->session_dir;
      if (session_id_.empty() || session_dir_.empty()) {
        rollback_lock_session();
        return replyJson(invocation.request_id, false, "session_id or session_dir missing");
      }
      locked_scan_plan_hash_ = request->scan_plan_hash;
      applyConfigSnapshotLocked(request->config_snapshot);
      captureSessionFreezeInputsLocked(*request);
      tool_ready_ = !config_.tool_name.empty();
      tcp_ready_ = !config_.tcp_name.empty();
      load_ready_ = config_.load_kg > 0.0;
      std::vector<std::string> session_blockers;
      std::vector<std::string> session_warnings;
      appendMainlineContractIssuesLocked(&session_blockers, &session_warnings);
      appendSessionFreezeGateIssuesLocked(&session_blockers, &session_warnings, true);
      if (!session_blockers.empty()) {
        rollback_lock_session();
        return replyJson(invocation.request_id, false, session_blockers.front());
      }
      auto runtime_cfg = sdk_robot_.queryPort().runtimeConfig();
    const auto identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
    runtime_cfg.robot_model = identity.robot_model;
    runtime_cfg.sdk_robot_class = identity.sdk_robot_class;
    runtime_cfg.preferred_link = config_.preferred_link.empty() ? identity.preferred_link : config_.preferred_link;
    runtime_cfg.requires_single_control_source = config_.requires_single_control_source;
    runtime_cfg.allow_contract_shell_writes = config_.allow_contract_shell_writes;
    runtime_cfg.clinical_mainline_mode = identity.clinical_mainline_mode;
    runtime_cfg.remote_ip = config_.remote_ip;
    runtime_cfg.local_ip = config_.local_ip;
    runtime_cfg.axis_count = identity.axis_count;
    runtime_cfg.rt_network_tolerance_percent = config_.rt_network_tolerance_percent;
    runtime_cfg.joint_filter_hz = config_.joint_filter_hz;
    runtime_cfg.cart_filter_hz = config_.cart_filter_hz;
    runtime_cfg.torque_filter_hz = config_.torque_filter_hz;
    runtime_cfg.contact_seek_speed_mm_s = config_.contact_seek_speed_mm_s;
    runtime_cfg.scan_speed_mm_s = config_.scan_speed_mm_s;
    runtime_cfg.retreat_speed_mm_s = config_.retreat_speed_mm_s;
    runtime_cfg.sample_step_mm = config_.sample_step_mm;
    runtime_cfg.seek_contact_max_travel_mm = std::max(config_.seek_contact_max_travel_mm, config_.collision_fallback_mm);
    runtime_cfg.scan_follow_max_travel_mm = std::max(config_.segment_length_mm, config_.sample_step_mm);
    runtime_cfg.retract_travel_mm = std::max(config_.retract_travel_mm, config_.collision_fallback_mm);
    runtime_cfg.scan_follow_lateral_amplitude_mm = std::max(0.0, config_.scan_follow_lateral_amplitude_mm);
    runtime_cfg.scan_follow_frequency_hz = std::max(0.05, config_.scan_follow_frequency_hz);
    runtime_cfg.rt_stale_state_timeout_ms = std::max(1.0, config_.rt_stale_state_timeout_ms);
    runtime_cfg.rt_phase_transition_debounce_cycles = std::max(1, config_.rt_phase_transition_debounce_cycles);
    runtime_cfg.rt_max_cart_step_mm = std::max(0.01, config_.rt_max_cart_step_mm);
    runtime_cfg.rt_max_cart_vel_mm_s = std::max(0.1, config_.rt_max_cart_vel_mm_s);
    runtime_cfg.rt_max_cart_acc_mm_s2 = std::max(1.0, config_.rt_max_cart_acc_mm_s2);
    runtime_cfg.rt_max_pose_trim_deg = std::max(0.1, config_.rt_max_pose_trim_deg);
    runtime_cfg.rt_max_force_error_n = std::max(0.1, config_.rt_max_force_error_n);
    runtime_cfg.rt_integrator_limit_n = std::max(0.1, config_.rt_integrator_limit_n);
    runtime_cfg.contact_force_target_n = std::max(0.1, config_.contact_force_target_n);
    runtime_cfg.contact_force_tolerance_n = std::max(0.1, config_.contact_force_tolerance_n);
    runtime_cfg.contact_establish_cycles = std::max(1, config_.contact_establish_cycles);
    runtime_cfg.normal_admittance_gain = std::max(0.0, config_.normal_admittance_gain);
    runtime_cfg.normal_damping_gain = std::max(0.0, config_.normal_damping_gain);
    runtime_cfg.seek_contact_max_step_mm = std::max(0.01, config_.seek_contact_max_step_mm);
    runtime_cfg.normal_velocity_quiet_threshold_mm_s = std::max(0.0, config_.normal_velocity_quiet_threshold_mm_s);
    runtime_cfg.scan_force_target_n = std::max(0.1, config_.scan_force_target_n);
    runtime_cfg.scan_force_tolerance_n = std::max(0.1, config_.scan_force_tolerance_n);
    runtime_cfg.scan_normal_pi_kp = std::max(0.0, config_.scan_normal_pi_kp);
    runtime_cfg.scan_normal_pi_ki = std::max(0.0, config_.scan_normal_pi_ki);
    runtime_cfg.scan_tangent_speed_min_mm_s = std::max(0.1, config_.scan_tangent_speed_min_mm_s);
    runtime_cfg.scan_tangent_speed_max_mm_s = std::max(runtime_cfg.scan_tangent_speed_min_mm_s, config_.scan_tangent_speed_max_mm_s);
    runtime_cfg.scan_pose_trim_gain = std::max(0.0, config_.scan_pose_trim_gain);
    runtime_cfg.scan_follow_enable_lateral_modulation = config_.scan_follow_enable_lateral_modulation;
    runtime_cfg.pause_hold_position_guard_mm = std::max(0.01, config_.pause_hold_position_guard_mm);
    runtime_cfg.pause_hold_force_guard_n = std::max(0.1, config_.pause_hold_force_guard_n);
    runtime_cfg.pause_hold_drift_kp = std::max(0.0, config_.pause_hold_drift_kp);
    runtime_cfg.pause_hold_drift_ki = std::max(0.0, config_.pause_hold_drift_ki);
    runtime_cfg.pause_hold_integrator_leak = std::clamp(config_.pause_hold_integrator_leak, 0.0, 1.0);
    runtime_cfg.contact_control.mode = config_.contact_control.mode.empty() ? std::string("normal_axis_admittance") : config_.contact_control.mode;
    runtime_cfg.contact_control.virtual_mass = std::max(0.01, config_.contact_control.virtual_mass);
    runtime_cfg.contact_control.virtual_damping = std::max(0.0, config_.contact_control.virtual_damping);
    runtime_cfg.contact_control.virtual_stiffness = std::max(0.0, config_.contact_control.virtual_stiffness);
    runtime_cfg.contact_control.force_deadband_n = std::max(0.0, config_.contact_control.force_deadband_n);
    runtime_cfg.contact_control.max_normal_step_mm = std::max(0.01, std::min(config_.contact_control.max_normal_step_mm, runtime_cfg.rt_max_cart_step_mm));
    runtime_cfg.contact_control.max_normal_velocity_mm_s = std::max(0.1, std::min(config_.contact_control.max_normal_velocity_mm_s, runtime_cfg.rt_max_cart_vel_mm_s));
    runtime_cfg.contact_control.max_normal_acc_mm_s2 = std::max(1.0, std::min(config_.contact_control.max_normal_acc_mm_s2, runtime_cfg.rt_max_cart_acc_mm_s2));
    runtime_cfg.contact_control.max_normal_travel_mm = std::max(runtime_cfg.contact_control.max_normal_step_mm, config_.contact_control.max_normal_travel_mm);
    runtime_cfg.contact_control.anti_windup_limit_n = std::max(0.1, config_.contact_control.anti_windup_limit_n);
    runtime_cfg.contact_control.integrator_leak = std::clamp(config_.contact_control.integrator_leak, 0.0, 1.0);
    runtime_cfg.force_estimator.preferred_source = config_.force_estimator.preferred_source.empty() ? std::string("fused") : config_.force_estimator.preferred_source;
    runtime_cfg.force_estimator.pressure_weight = std::max(0.0, config_.force_estimator.pressure_weight);
    runtime_cfg.force_estimator.wrench_weight = std::max(0.0, config_.force_estimator.wrench_weight);
    runtime_cfg.force_estimator.stale_timeout_ms = std::max(1, config_.force_estimator.stale_timeout_ms);
    runtime_cfg.force_estimator.timeout_ms = std::max(runtime_cfg.force_estimator.stale_timeout_ms, config_.force_estimator.timeout_ms);
    runtime_cfg.force_estimator.auto_bias_zero = config_.force_estimator.auto_bias_zero;
    runtime_cfg.force_estimator.min_confidence = std::clamp(config_.force_estimator.min_confidence, 0.0, 1.0);
    runtime_cfg.orientation_trim.gain = std::max(0.0, config_.orientation_trim.gain);
    runtime_cfg.orientation_trim.max_trim_deg = std::max(0.1, config_.orientation_trim.max_trim_deg);
    runtime_cfg.orientation_trim.lowpass_hz = std::max(0.1, config_.orientation_trim.lowpass_hz);
    runtime_cfg.retract_release_force_n = std::max(0.1, config_.retract_release_force_n);
    runtime_cfg.retract_release_cycles = std::max(1, config_.retract_release_cycles);
    runtime_cfg.retract_safe_gap_mm = std::max(0.1, config_.retract_safe_gap_mm);
    runtime_cfg.retract_max_travel_mm = std::max(0.1, config_.retract_max_travel_mm);
    runtime_cfg.retract_jerk_limit_mm_s3 = std::max(1.0, config_.retract_jerk_limit_mm_s3);
    runtime_cfg.retract_timeout_ms = std::max(10.0, config_.retract_timeout_ms);
    runtime_cfg.load_kg = config_.load_kg;
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, config_.cartesian_impedance.size()); ++idx) runtime_cfg.cartesian_impedance[idx] = config_.cartesian_impedance[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, config_.desired_wrench_n.size()); ++idx) runtime_cfg.desired_wrench_n[idx] = config_.desired_wrench_n[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(16, config_.fc_frame_matrix.size()); ++idx) runtime_cfg.fc_frame_matrix[idx] = config_.fc_frame_matrix[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(16, config_.tcp_frame_matrix.size()); ++idx) runtime_cfg.tcp_frame_matrix[idx] = config_.tcp_frame_matrix[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(3, config_.load_com_mm.size()); ++idx) runtime_cfg.load_com_mm[idx] = config_.load_com_mm[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, config_.load_inertia.size()); ++idx) runtime_cfg.load_inertia[idx] = config_.load_inertia[idx];
      sdk_robot_.rtControlPort().configureMainline(runtime_cfg);
      sdk_robot_.collaborationPort().setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
      sdk_robot_.collaborationPort().setDragState(false, "cartesian", "admittance");
      std::filesystem::create_directories(session_dir_);
      recording_service_.openSession(session_dir_, session_id_);
      bindAuthoritySessionLocked(session_id_);
      session_locked_ts_ns_ = json::nowNs();
      execution_state_ = RobotCoreState::SessionLocked;
      return replyJson(invocation.request_id, true, "lock_session accepted", json::object({json::field("session_id", json::quote(session_id_))}));
    } catch (const std::exception& exc) {
      rollback_lock_session();
      return replyJson(invocation.request_id, false, std::string("lock_session failed: ") + exc.what());
    } catch (...) {
      rollback_lock_session();
      return replyJson(invocation.request_id, false, "lock_session failed: unknown exception");
    }
  }
  if (command == "acquire_control_lease") {
    const auto* request = invocation.requestAs<AcquireControlLeaseRequest>();
    if (request == nullptr) {
      return replyJson(invocation.request_id, false, "typed request mismatch: acquire_control_lease");
    }
    const auto& context = invocation.context();
    const auto actor_id = normalizeAuthorityToken(context.actor_id.empty() ? request->actor_id.value_or(std::string()) : context.actor_id, "implicit-operator");
    const auto workspace = normalizeAuthorityToken(context.workspace.empty() ? request->workspace.value_or(std::string()) : context.workspace, "desktop");
    const auto role = normalizeAuthorityToken(context.role.empty() ? request->role.value_or(std::string()) : context.role, "operator");
    const auto session_id = normalizeAuthorityToken(context.session_id.empty() ? request->session_id.value_or(session_id_) : context.session_id, session_id_);
    const auto profile = normalizeAuthorityToken(context.profile.empty() ? request->profile.value_or(std::string("dev")) : context.profile, "dev");
    const auto source = normalizeAuthorityToken(context.source.empty() ? request->source.value_or(std::string("runtime_command")) : context.source, "runtime_command");
    const auto intent_reason = normalizeAuthorityToken(context.intent_reason.empty() ? request->intent_reason.value_or(std::string("runtime_control_authority")) : context.intent_reason, "runtime_control_authority");
    const auto requested_lease_id = normalizeAuthorityToken(context.lease_id.empty() ? request->lease_id.value_or(std::string()) : context.lease_id, "");
    if (authority_lease_.active) {
      const bool same_owner = authority_lease_.actor_id == actor_id && authority_lease_.workspace == workspace && authority_lease_.role == role;
      if (!same_owner) {
        return replyJson(invocation.request_id, false, "控制权已被 " + authority_lease_.actor_id + "@" + authority_lease_.workspace + "/" + authority_lease_.role + " 持有，当前请求为 " + actor_id + "@" + workspace + "/" + role);
      }
      if (!requested_lease_id.empty() && requested_lease_id != authority_lease_.lease_id) {
        return replyJson(invocation.request_id, false, "lease_id 不匹配，active=" + authority_lease_.lease_id);
      }
    }
    authority_lease_.active = true;
    authority_lease_.lease_id = requested_lease_id.empty() ? (authority_lease_.lease_id.empty() ? makeRuntimeLeaseIdLocked(context) : authority_lease_.lease_id) : requested_lease_id;
    authority_lease_.actor_id = actor_id;
    authority_lease_.workspace = workspace;
    authority_lease_.role = role;
    authority_lease_.session_id = session_id;
    authority_lease_.source = source;
    authority_lease_.intent_reason = intent_reason;
    authority_lease_.deployment_profile = profile;
    authority_lease_.acquired_ts_ns = authority_lease_.acquired_ts_ns == 0 ? json::nowNs() : authority_lease_.acquired_ts_ns;
    authority_lease_.refreshed_ts_ns = json::nowNs();
    authority_lease_.granted_claims.insert("control_authority_write");
    for (const auto& claim : context.requested_claims) {
      if (roleCanClaimLocked(role, claim)) authority_lease_.granted_claims.insert(claim);
    }
    if (!session_id.empty()) bindAuthoritySessionLocked(session_id);
    return replyJson(invocation.request_id, true, "acquire_control_lease accepted", json::object({
        json::field("summary_state", json::quote("ready")),
        json::field("summary_label", json::quote("控制权租约已获取")),
        json::field("detail", json::quote("cpp_robot_core runtime 持有并发布唯一控制权租约")),
        json::field("lease", json::object({
            json::field("lease_id", json::quote(authority_lease_.lease_id)),
            json::field("actor_id", json::quote(authority_lease_.actor_id)),
            json::field("workspace", json::quote(authority_lease_.workspace)),
            json::field("role", json::quote(authority_lease_.role)),
            json::field("session_id", json::quote(authority_lease_.session_id)),
            json::field("acquired_ts_ns", std::to_string(authority_lease_.acquired_ts_ns)),
            json::field("refreshed_ts_ns", std::to_string(authority_lease_.refreshed_ts_ns)),
            json::field("source", json::quote(authority_lease_.source)),
            json::field("deployment_profile", json::quote(authority_lease_.deployment_profile)),
            json::field("granted_claims", joinClaims(authority_lease_.granted_claims))
        })),
        json::field("control_authority", controlAuthorityJsonLocked())
    }));
  }
  if (command == "renew_control_lease") {
    const auto* request = invocation.requestAs<RenewControlLeaseRequest>();
    if (request == nullptr) {
      return replyJson(invocation.request_id, false, "typed request mismatch: renew_control_lease");
    }
    if (!authority_lease_.active) {
      return replyJson(invocation.request_id, false, "当前没有可续租的控制权租约");
    }
    const auto& context = invocation.context();
    const auto lease_id = normalizeAuthorityToken(context.lease_id.empty() ? request->lease_id.value_or(std::string()) : context.lease_id, "");
    const auto actor_id = normalizeAuthorityToken(context.actor_id.empty() ? request->actor_id.value_or(authority_lease_.actor_id) : context.actor_id, authority_lease_.actor_id);
    if (lease_id.empty() || lease_id != authority_lease_.lease_id) {
      return replyJson(invocation.request_id, false, "lease_id 不匹配，active=" + authority_lease_.lease_id);
    }
    if (actor_id != authority_lease_.actor_id) {
      return replyJson(invocation.request_id, false, "actor_id 不匹配，active=" + authority_lease_.actor_id);
    }
    authority_lease_.refreshed_ts_ns = json::nowNs();
    authority_lease_.granted_claims.insert("control_authority_write");
    return replyJson(invocation.request_id, true, "renew_control_lease accepted", json::object({
        json::field("summary_state", json::quote("ready")),
        json::field("summary_label", json::quote("控制权租约已续租")),
        json::field("detail", json::quote("cpp_robot_core runtime 已刷新控制权租约")),
        json::field("lease", json::object({
            json::field("lease_id", json::quote(authority_lease_.lease_id)),
            json::field("actor_id", json::quote(authority_lease_.actor_id)),
            json::field("workspace", json::quote(authority_lease_.workspace)),
            json::field("role", json::quote(authority_lease_.role)),
            json::field("session_id", json::quote(authority_lease_.session_id)),
            json::field("acquired_ts_ns", std::to_string(authority_lease_.acquired_ts_ns)),
            json::field("refreshed_ts_ns", std::to_string(authority_lease_.refreshed_ts_ns)),
            json::field("source", json::quote(authority_lease_.source)),
            json::field("deployment_profile", json::quote(authority_lease_.deployment_profile)),
            json::field("granted_claims", joinClaims(authority_lease_.granted_claims))
        })),
        json::field("control_authority", controlAuthorityJsonLocked())
    }));
  }
  if (command == "release_control_lease") {
    const auto* request = invocation.requestAs<ReleaseControlLeaseRequest>();
    if (request == nullptr) {
      return replyJson(invocation.request_id, false, "typed request mismatch: release_control_lease");
    }
    if (!authority_lease_.active) {
      return replyJson(invocation.request_id, true, "release_control_lease accepted", json::object({
          json::field("summary_state", json::quote("released")),
          json::field("summary_label", json::quote("当前无活动控制权租约")),
          json::field("detail", json::quote("cpp_robot_core runtime 当前无活动控制权租约")),
          json::field("control_authority", controlAuthorityJsonLocked())
      }));
    }
    const auto& context = invocation.context();
    const auto lease_id = normalizeAuthorityToken(context.lease_id.empty() ? request->lease_id.value_or(std::string()) : context.lease_id, authority_lease_.lease_id);
    const auto actor_id = normalizeAuthorityToken(context.actor_id.empty() ? request->actor_id.value_or(authority_lease_.actor_id) : context.actor_id, authority_lease_.actor_id);
    if (!lease_id.empty() && lease_id != authority_lease_.lease_id) {
      return replyJson(invocation.request_id, false, "lease_id 不匹配，active=" + authority_lease_.lease_id);
    }
    if (!actor_id.empty() && actor_id != authority_lease_.actor_id) {
      return replyJson(invocation.request_id, false, "actor_id 不匹配，active=" + authority_lease_.actor_id);
    }
    clearAuthoritySessionBindingLocked();
    authority_lease_ = RuntimeAuthorityLease{};
    return replyJson(invocation.request_id, true, "release_control_lease accepted", json::object({
        json::field("summary_state", json::quote("released")),
        json::field("summary_label", json::quote("控制权租约已释放")),
        json::field("detail", json::quote("cpp_robot_core runtime 已释放控制权租约")),
        json::field("control_authority", controlAuthorityJsonLocked())
    }));
  }
  if (command == "load_scan_plan") {
    const auto* request = invocation.requestAs<LoadScanPlanRequest>();
    if (request == nullptr) {
      return replyJson(invocation.request_id, false, "typed request mismatch: load_scan_plan");
    }
    if (execution_state_ != RobotCoreState::SessionLocked && execution_state_ != RobotCoreState::PathValidated &&
        execution_state_ != RobotCoreState::ScanComplete) {
      return replyJson(invocation.request_id, false, "session not locked");
    }
    loadPlanLocked(request->scan_plan, request->scan_plan_hash.value_or(""));
    if (!plan_loaded_) {
      return replyJson(invocation.request_id, false, "scan plan missing segments");
    }
    if (!locked_scan_plan_hash_.empty() && !plan_hash_.empty() && locked_scan_plan_hash_ != plan_hash_) {
      plan_loaded_ = false;
      execution_state_ = RobotCoreState::SessionLocked;
      state_reason_ = "plan_hash_mismatch";
      return replyJson(invocation.request_id, false, "locked scan_plan_hash does not match loaded plan");
    }
    configureActiveSegmentLocked(nullptr);
    execution_state_ = RobotCoreState::PathValidated;
    state_reason_ = "scan_plan_validated";
    if (last_final_verdict_.plan_hash.empty() || last_final_verdict_.plan_hash == plan_hash_) {
      last_final_verdict_.accepted = true;
      last_final_verdict_.reason = "scan plan validated and loaded";
      last_final_verdict_.detail = "scan plan validated and loaded";
      last_final_verdict_.policy_state = "ready";
      last_final_verdict_.next_state = "approach_prescan";
      last_final_verdict_.plan_id = plan_id_;
      last_final_verdict_.plan_hash = plan_hash_;
      last_final_verdict_.summary_label = "模型前检通过";
    }
    return replyJson(invocation.request_id, true, "load_scan_plan accepted", json::object({json::field("plan_id", json::quote(plan_id_))}));
  }
  return replyJson(invocation.request_id, false, "unsupported command: " + command);
}

std::string CoreRuntime::handleExecutionCommand(const RuntimeCommandInvocation& invocation) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto& command = invocation.command;
  const auto allow_command = [this](const std::string& action, std::string* reason) -> bool {
    return state_machine_guard_.allow(action, execution_state_, reason);
  };
  const auto validate_rt_phase = [this](const std::string& fallback_message, std::string* out_reason) -> bool {
    std::string phase_reason;
    const bool ok = model_authority_.validateRtPhaseTargetDelta(config_, sdk_robot_, &phase_reason) &&
                    model_authority_.validateRtPhaseWorkspace(config_, sdk_robot_, &phase_reason) &&
                    model_authority_.validateRtPhaseSingularityMargin(config_, sdk_robot_, &phase_reason);
    if (!ok && out_reason != nullptr) {
      *out_reason = phase_reason.empty() ? fallback_message : phase_reason;
    }
    return ok;
  };
  using ExecutionHandler = std::function<std::string(CoreRuntime*, const RuntimeCommandInvocation&)>;
const auto start_scan_procedure = [allow_command, validate_rt_phase](CoreRuntime* self, const std::string& command_name, const std::string& procedure_name, const RuntimeCommandInvocation& inv) {
  std::string reason;
  if (!allow_command(command_name, &reason)) {
    return self->replyJson(inv.request_id, false, reason);
  }
  if (!self->sessionFreezeConsistentLocked()) {
    return self->replyJson(inv.request_id, false, "start_procedure blocked by runtime freeze gate");
  }
  if (!validate_rt_phase(command_name + std::string(" precheck failed"), &reason)) {
    return self->replyJson(inv.request_id, false, reason);
  }
  if (procedure_name != "scan") {
    return self->replyJson(inv.request_id, false, "unsupported procedure: " + procedure_name);
  }
  if (!self->configureActiveSegmentLocked(&reason)) {
    return self->replyJson(inv.request_id, false, reason.empty() ? "active segment configuration failed" : reason);
  }
  self->scan_procedure_active_ = true;
  if (self->execution_state_ == RobotCoreState::PausedHold || self->execution_state_ == RobotCoreState::ContactStable) {
    if (!self->startPlanDrivenScanLocked(&reason)) {
      return self->replyJson(inv.request_id, false, reason.empty() ? "resume start_procedure failed" : reason);
    }
    return self->replyJson(inv.request_id, true, "start_procedure accepted");
  }
  if (self->execution_state_ != RobotCoreState::PathValidated) {
    return self->replyJson(inv.request_id, false, "start_procedure requires PATH_VALIDATED, CONTACT_STABLE, or PAUSED_HOLD");
  }
  if (!self->nrt_motion_service_.approachPrescan()) {
    self->execution_state_ = RobotCoreState::Fault;
    return self->replyJson(inv.request_id, false, "approach_prescan failed");
  }
  self->execution_state_ = RobotCoreState::Approaching;
  self->state_reason_ = "approach_prescan";
  self->contact_state_.recommended_action = "SEEK_CONTACT";
  if (!self->rt_motion_service_.seekContact()) {
    self->execution_state_ = RobotCoreState::Fault;
    return self->replyJson(inv.request_id, false, "seek_contact failed");
  }
  self->execution_state_ = RobotCoreState::ContactSeeking;
  self->state_reason_ = "waiting_for_contact_stability";
  self->contact_state_.mode = "SEEKING_CONTACT";
  self->contact_state_.recommended_action = "WAIT_CONTACT_STABLE";
  return self->replyJson(inv.request_id, true, "start_procedure accepted");
};
  const std::unordered_map<std::string, ExecutionHandler> handlers = {
      {"approach_prescan", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ApproachPrescanRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: approach_prescan");
         }
         (void)request;
         if (self->execution_state_ != RobotCoreState::PathValidated) {
           return self->replyJson(inv.request_id, false, "scan plan not ready");
         }
         if (!self->sessionFreezeConsistentLocked()) {
           return self->replyJson(inv.request_id, false, "approach_prescan blocked by runtime freeze gate");
         }
         if (!self->nrt_motion_service_.approachPrescan()) {
           self->execution_state_ = RobotCoreState::Fault;
           return self->replyJson(inv.request_id, false, "approach_prescan failed");
         }
         self->execution_state_ = RobotCoreState::Approaching;
         self->state_reason_ = "approach_prescan";
         self->contact_state_.recommended_action = "SEEK_CONTACT";
         return self->replyJson(inv.request_id, true, "approach_prescan accepted");
       }},
      {"seek_contact", [allow_command, validate_rt_phase](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<SeekContactRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: seek_contact");
         }
         (void)request;
         std::string reason;
         if (!allow_command("seek_contact", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->sessionFreezeConsistentLocked()) {
           return self->replyJson(inv.request_id, false, "seek_contact blocked by runtime freeze gate");
         }
         if (!validate_rt_phase("seek_contact precheck failed", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->rt_motion_service_.seekContact()) {
           return self->replyJson(inv.request_id, false, "seek_contact failed");
         }
         self->execution_state_ = RobotCoreState::ContactSeeking;
         self->state_reason_ = "waiting_for_contact_stability";
         self->contact_state_.mode = "SEEKING_CONTACT";
         self->contact_state_.recommended_action = "WAIT_CONTACT_STABLE";
         return self->replyJson(inv.request_id, true, "seek_contact accepted");
       }},
      {"start_procedure", [start_scan_procedure](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<StartProcedureRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: start_procedure");
         }
         return start_scan_procedure(self, "start_procedure", request->procedure, inv);
       }},
      {"start_scan", [start_scan_procedure](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<StartScanRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: start_scan");
         }
         (void)request;
         return start_scan_procedure(self, "start_scan", "scan", inv);
       }},
      {"pause_scan", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<PauseScanRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: pause_scan");
         }
         (void)request;
         if (self->execution_state_ != RobotCoreState::Scanning) {
           return self->replyJson(inv.request_id, false, "scan not active");
         }
         self->rt_motion_service_.pauseAndHold();
         self->recovery_manager_.pauseAndHold();
         self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, false);
         self->execution_state_ = RobotCoreState::PausedHold;
         self->state_reason_ = "pause_hold";
         self->contact_state_.mode = "HOLDING_CONTACT";
         self->contact_state_.recommended_action = "RESUME_OR_RETREAT";
         return self->replyJson(inv.request_id, true, "pause_scan accepted");
       }},
      {"resume_scan", [validate_rt_phase](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ResumeScanRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: resume_scan");
         }
         (void)request;
         if (!self->sessionFreezeConsistentLocked()) {
           return self->replyJson(inv.request_id, false, "resume_scan blocked by runtime freeze gate");
         }
         if (self->execution_state_ != RobotCoreState::PausedHold) {
           return self->replyJson(inv.request_id, false, "scan not paused");
         }
         std::string reason;
         if (!validate_rt_phase("resume_scan precheck failed", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->startPlanDrivenScanLocked(&reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "resume_scan failed" : reason);
         }
         self->recovery_manager_.cancelRetry();
         return self->replyJson(inv.request_id, true, "resume_scan accepted");
       }},
      {"safe_retreat", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<SafeRetreatRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: safe_retreat");
         }
         (void)request;
         std::string reason;
         if (!allow_command("safe_retreat", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto rt_retract = self->rt_motion_service_.controlledRetract();
         if (!rt_retract.canProceedToNrtRetreat()) {
           self->execution_state_ = RobotCoreState::Fault;
           self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, false);
           self->fault_code_ = "SAFE_RETREAT_RT_RETRACT_FAILED";
           self->queueAlarmLocked("RECOVERABLE_FAULT", "recovery", "安全退让失败：RT受控回撤未闭环", "safe_retreat", rt_retract.reason, "controlled_retract_incomplete");
           return self->replyJson(inv.request_id, false, std::string("safe_retreat blocked before NRT retreat: ") + rt_retract.reason);
         }
         if (!self->nrt_motion_service_.safeRetreat(&reason)) {
           self->execution_state_ = RobotCoreState::Fault;
           self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, false);
           self->fault_code_ = "SAFE_RETREAT_FAILED";
           self->queueAlarmLocked("RECOVERABLE_FAULT", "recovery", "安全退让失败", "safe_retreat", reason, "controlled_retract_failed");
           return self->replyJson(inv.request_id, false, reason.empty() ? "safe_retreat failed" : reason);
         }
         self->recovery_manager_.controlledRetract();
         self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, false);
         self->execution_state_ = RobotCoreState::Retreating;
         self->state_reason_ = "safe_retreat";
         self->retreat_ticks_remaining_ = 30;
         self->contact_state_.mode = "NO_CONTACT";
         self->contact_state_.recommended_action = "WAIT_RETREAT_COMPLETE";
         return self->replyJson(inv.request_id, true, "safe_retreat accepted");
       }},
      {"go_home", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<GoHomeRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: go_home");
         }
         (void)request;
         std::string reason;
         if (!allow_command("go_home", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const bool ok = self->nrt_motion_service_.goHome();
         return self->replyJson(inv.request_id, ok, ok ? "go_home accepted" : "go_home failed");
       }},
      {"run_rl_project", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<RunRlProjectRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: run_rl_project");
         }
         std::string reason;
         if (!allow_command("run_rl_project", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto project = request->project.value_or(self->config_.rl_project_name);
         const auto task = request->task.value_or(self->config_.rl_task_name);
         if (!self->sdk_robot_.collaborationPort().runRlProject(project, task, &reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "run_rl_project failed" : reason);
         }
         self->sdk_robot_.collaborationPort().setRlStatus(project, task, true);
         return self->replyJson(inv.request_id, true, "run_rl_project accepted");
       }},
      {"pause_rl_project", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<PauseRlProjectRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: pause_rl_project");
         }
         (void)request;
         std::string reason;
         if (!allow_command("pause_rl_project", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->sdk_robot_.collaborationPort().pauseRlProject(&reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "pause_rl_project failed" : reason);
         }
         self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, false);
         return self->replyJson(inv.request_id, true, "pause_rl_project accepted");
       }},
      {"enable_drag", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<EnableDragRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: enable_drag");
         }
         std::string reason;
         if (!allow_command("enable_drag", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto space = request->space.value_or("cartesian");
         const auto type = request->type.value_or("admittance");
         if (!self->sdk_robot_.collaborationPort().enableDrag(space, type, &reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "enable_drag failed" : reason);
         }
         self->sdk_robot_.collaborationPort().setDragState(true, space, type);
         return self->replyJson(inv.request_id, true, "enable_drag accepted");
       }},
      {"disable_drag", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<DisableDragRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: disable_drag");
         }
         (void)request;
         std::string reason;
         if (!allow_command("disable_drag", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->sdk_robot_.collaborationPort().disableDrag(&reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "disable_drag failed" : reason);
         }
         self->sdk_robot_.collaborationPort().setDragState(false, "cartesian", "admittance");
         return self->replyJson(inv.request_id, true, "disable_drag accepted");
       }},
      {"replay_path", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ReplayPathRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: replay_path");
         }
         std::string reason;
         if (!allow_command("replay_path", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto name = request->name.value_or("spine_demo_path");
         const auto rate = request->rate.value_or(0.5);
         if (!self->sdk_robot_.collaborationPort().replayPath(name, rate, &reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "replay_path failed" : reason);
         }
         return self->replyJson(inv.request_id, true, "replay_path accepted");
       }},
      {"start_record_path", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<StartRecordPathRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: start_record_path");
         }
         std::string reason;
         if (!allow_command("start_record_path", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto duration_s = request->duration_s.value_or(60);
         if (!self->sdk_robot_.collaborationPort().startRecordPath(duration_s, &reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "start_record_path failed" : reason);
         }
         return self->replyJson(inv.request_id, true, "start_record_path accepted");
       }},
      {"stop_record_path", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<StopRecordPathRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: stop_record_path");
         }
         (void)request;
         std::string reason;
         if (!allow_command("stop_record_path", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->sdk_robot_.collaborationPort().stopRecordPath(&reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "stop_record_path failed" : reason);
         }
         return self->replyJson(inv.request_id, true, "stop_record_path accepted");
       }},
      {"cancel_record_path", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<CancelRecordPathRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: cancel_record_path");
         }
         (void)request;
         std::string reason;
         if (!allow_command("cancel_record_path", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->sdk_robot_.collaborationPort().cancelRecordPath(&reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "cancel_record_path failed" : reason);
         }
         return self->replyJson(inv.request_id, true, "cancel_record_path accepted");
       }},
      {"save_record_path", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<SaveRecordPathRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: save_record_path");
         }
         std::string reason;
         if (!allow_command("save_record_path", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto name = request->name.value_or("spine_demo_path");
         const auto save_as = request->save_as.value_or(name);
         if (!self->sdk_robot_.collaborationPort().saveRecordPath(name, save_as, &reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "save_record_path failed" : reason);
         }
         return self->replyJson(inv.request_id, true, "save_record_path accepted");
       }},
      {"clear_fault", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ClearFaultRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: clear_fault");
         }
         (void)request;
         if (self->execution_state_ != RobotCoreState::Fault) {
           return self->replyJson(inv.request_id, false, "no fault to clear");
         }
         self->fault_code_.clear();
         self->execution_state_ = self->plan_loaded_ ? RobotCoreState::PathValidated : RobotCoreState::AutoReady;
         return self->replyJson(inv.request_id, true, "clear_fault accepted");
       }},
      {"emergency_stop", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<EmergencyStopRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: emergency_stop");
         }
         (void)request;
         self->rt_motion_service_.stop();
         self->recovery_manager_.cancelRetry();
         self->recovery_manager_.latchEstop();
         self->execution_state_ = RobotCoreState::Estop;
         self->fault_code_ = "ESTOP";
         self->queueAlarmLocked("FATAL_FAULT", "safety", "急停触发");
         return self->replyJson(inv.request_id, true, "emergency_stop accepted");
       }},
  };
  const auto it = handlers.find(command);
  if (it == handlers.end()) {
    return replyJson(invocation.request_id, false, "unsupported command: " + command);
  }
  return it->second(this, invocation);
}

}  // namespace robot_core
