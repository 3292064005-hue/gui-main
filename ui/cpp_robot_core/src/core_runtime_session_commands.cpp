#include "robot_core/core_runtime.h"

#include <algorithm>
#include <filesystem>
#include <functional>
#include <unordered_map>

#include "json_utils.h"
#include "core_runtime_command_helpers.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {


std::string CoreRuntime::handleSessionCommand(const RuntimeCommandInvocation& invocation) {
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  const auto& command = invocation.command;
  if (command == "lock_session") {
    const auto* request = invocation.requestAs<LockSessionRequest>();
    if (request == nullptr) {
      return replyJson(invocation.request_id, false, "typed request mismatch: lock_session");
    }
    if (state_store_.execution_state != RobotCoreState::AutoReady) {
      return replyJson(invocation.request_id, false, "core not ready for session lock");
    }
    const auto previous_session_id = state_store_.session_id;
    const auto previous_session_dir = state_store_.session_dir;
    const auto previous_locked_scan_plan_hash = state_store_.locked_scan_plan_hash;
    const auto previous_config = state_store_.config;
    const auto previous_tool_ready = state_store_.tool_ready;
    const auto previous_tcp_ready = state_store_.tcp_ready;
    const auto previous_load_ready = state_store_.load_ready;
    const auto previous_session_locked_ts_ns = state_store_.session_locked_ts_ns;
    const auto previous_authority_lease = authority_kernel_.lease;
    const auto previous_strict_runtime_freeze_gate = state_store_.strict_runtime_freeze_gate;
    const auto previous_frozen_device_roster_json = state_store_.frozen_device_roster_json;
    const auto previous_frozen_safety_thresholds_json = state_store_.frozen_safety_thresholds_json;
    const auto previous_frozen_device_health_snapshot_json = state_store_.frozen_device_health_snapshot_json;
    const auto previous_frozen_session_freeze_policy_json = state_store_.frozen_session_freeze_policy_json;
    const auto previous_frozen_execution_critical_fields = state_store_.frozen_execution_critical_fields;
    const auto previous_frozen_evidence_only_fields = state_store_.frozen_evidence_only_fields;
    const auto previous_frozen_recheck_on_start_procedure = state_store_.frozen_recheck_on_start_procedure;
    const auto previous_runtime_cfg = procedure_executor_.sdk_robot.queryPort().runtimeConfig();
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
      evidence_projector_.recording_service.closeSession();
      state_store_.config = previous_config;
      state_store_.session_id = previous_session_id;
      state_store_.session_dir = previous_session_dir;
      state_store_.locked_scan_plan_hash = previous_locked_scan_plan_hash;
      state_store_.tool_ready = previous_tool_ready;
      state_store_.tcp_ready = previous_tcp_ready;
      state_store_.load_ready = previous_load_ready;
      state_store_.session_locked_ts_ns = previous_session_locked_ts_ns;
      authority_kernel_.lease = previous_authority_lease;
      state_store_.strict_runtime_freeze_gate = previous_strict_runtime_freeze_gate;
      state_store_.frozen_device_roster_json = previous_frozen_device_roster_json;
      state_store_.frozen_safety_thresholds_json = previous_frozen_safety_thresholds_json;
      state_store_.frozen_device_health_snapshot_json = previous_frozen_device_health_snapshot_json;
      state_store_.frozen_session_freeze_policy_json = previous_frozen_session_freeze_policy_json;
      state_store_.frozen_execution_critical_fields = previous_frozen_execution_critical_fields;
      state_store_.frozen_evidence_only_fields = previous_frozen_evidence_only_fields;
      state_store_.frozen_recheck_on_start_procedure = previous_frozen_recheck_on_start_procedure;
      procedure_executor_.sdk_robot.rtControlPort().configureMainline(previous_runtime_cfg);
    };
    try {
      state_store_.session_id = request->session_id;
      state_store_.session_dir = request->session_dir;
      if (state_store_.session_id.empty() || state_store_.session_dir.empty()) {
        rollback_lock_session();
        return replyJson(invocation.request_id, false, "session_id or session_dir missing");
      }
      state_store_.locked_scan_plan_hash = request->scan_plan_hash;
      applyConfigSnapshotLocked(request->config_snapshot);
      captureSessionFreezeInputsLocked(*request);
      state_store_.tool_ready = !state_store_.config.tool_name.empty();
      state_store_.tcp_ready = !state_store_.config.tcp_name.empty();
      state_store_.load_ready = state_store_.config.load_kg > 0.0;
      std::vector<std::string> session_blockers;
      std::vector<std::string> session_warnings;
      appendMainlineContractIssuesLocked(&session_blockers, &session_warnings);
      appendSessionFreezeGateIssuesLocked(&session_blockers, &session_warnings, true);
      if (!session_blockers.empty()) {
        rollback_lock_session();
        return replyJson(invocation.request_id, false, session_blockers.front());
      }
      auto runtime_cfg = procedure_executor_.sdk_robot.queryPort().runtimeConfig();
    const auto identity = resolveRobotIdentity(state_store_.config.robot_model, state_store_.config.sdk_robot_class, state_store_.config.axis_count);
    runtime_cfg.robot_model = identity.robot_model;
    runtime_cfg.sdk_robot_class = identity.sdk_robot_class;
    runtime_cfg.preferred_link = state_store_.config.preferred_link.empty() ? identity.preferred_link : state_store_.config.preferred_link;
    runtime_cfg.requires_single_control_source = state_store_.config.requires_single_control_source;
    runtime_cfg.clinical_mainline_mode = identity.clinical_mainline_mode;
    runtime_cfg.remote_ip = state_store_.config.remote_ip;
    runtime_cfg.local_ip = state_store_.config.local_ip;
    runtime_cfg.axis_count = identity.axis_count;
    runtime_cfg.rt_network_tolerance_percent = state_store_.config.rt_network_tolerance_percent;
    runtime_cfg.joint_filter_hz = state_store_.config.joint_filter_hz;
    runtime_cfg.cart_filter_hz = state_store_.config.cart_filter_hz;
    runtime_cfg.torque_filter_hz = state_store_.config.torque_filter_hz;
    runtime_cfg.contact_seek_speed_mm_s = state_store_.config.contact_seek_speed_mm_s;
    runtime_cfg.scan_speed_mm_s = state_store_.config.scan_speed_mm_s;
    runtime_cfg.retreat_speed_mm_s = state_store_.config.retreat_speed_mm_s;
    runtime_cfg.sample_step_mm = state_store_.config.sample_step_mm;
    runtime_cfg.seek_contact_max_travel_mm = std::max(state_store_.config.seek_contact_max_travel_mm, state_store_.config.collision_fallback_mm);
    runtime_cfg.scan_follow_max_travel_mm = std::max(state_store_.config.segment_length_mm, state_store_.config.sample_step_mm);
    runtime_cfg.retract_travel_mm = std::max(state_store_.config.retract_travel_mm, state_store_.config.collision_fallback_mm);
    runtime_cfg.scan_follow_lateral_amplitude_mm = std::max(0.0, state_store_.config.scan_follow_lateral_amplitude_mm);
    runtime_cfg.scan_follow_frequency_hz = std::max(0.05, state_store_.config.scan_follow_frequency_hz);
    runtime_cfg.rt_stale_state_timeout_ms = std::max(1.0, state_store_.config.rt_stale_state_timeout_ms);
    runtime_cfg.rt_phase_transition_debounce_cycles = std::max(1, state_store_.config.rt_phase_transition_debounce_cycles);
    runtime_cfg.rt_max_cart_step_mm = std::max(0.01, state_store_.config.rt_max_cart_step_mm);
    runtime_cfg.rt_max_cart_vel_mm_s = std::max(0.1, state_store_.config.rt_max_cart_vel_mm_s);
    runtime_cfg.rt_max_cart_acc_mm_s2 = std::max(1.0, state_store_.config.rt_max_cart_acc_mm_s2);
    runtime_cfg.rt_max_pose_trim_deg = std::max(0.1, state_store_.config.rt_max_pose_trim_deg);
    runtime_cfg.rt_max_force_error_n = std::max(0.1, state_store_.config.rt_max_force_error_n);
    runtime_cfg.rt_integrator_limit_n = std::max(0.1, state_store_.config.rt_integrator_limit_n);
    runtime_cfg.contact_force_target_n = std::max(0.1, state_store_.config.contact_force_target_n);
    runtime_cfg.contact_force_tolerance_n = std::max(0.1, state_store_.config.contact_force_tolerance_n);
    runtime_cfg.contact_establish_cycles = std::max(1, state_store_.config.contact_establish_cycles);
    runtime_cfg.normal_admittance_gain = std::max(0.0, state_store_.config.normal_admittance_gain);
    runtime_cfg.normal_damping_gain = std::max(0.0, state_store_.config.normal_damping_gain);
    runtime_cfg.seek_contact_max_step_mm = std::max(0.01, state_store_.config.seek_contact_max_step_mm);
    runtime_cfg.normal_velocity_quiet_threshold_mm_s = std::max(0.0, state_store_.config.normal_velocity_quiet_threshold_mm_s);
    runtime_cfg.scan_force_target_n = std::max(0.1, state_store_.config.scan_force_target_n);
    runtime_cfg.scan_force_tolerance_n = std::max(0.1, state_store_.config.scan_force_tolerance_n);
    runtime_cfg.scan_normal_pi_kp = std::max(0.0, state_store_.config.scan_normal_pi_kp);
    runtime_cfg.scan_normal_pi_ki = std::max(0.0, state_store_.config.scan_normal_pi_ki);
    runtime_cfg.scan_tangent_speed_min_mm_s = std::max(0.1, state_store_.config.scan_tangent_speed_min_mm_s);
    runtime_cfg.scan_tangent_speed_max_mm_s = std::max(runtime_cfg.scan_tangent_speed_min_mm_s, state_store_.config.scan_tangent_speed_max_mm_s);
    runtime_cfg.scan_pose_trim_gain = std::max(0.0, state_store_.config.scan_pose_trim_gain);
    runtime_cfg.scan_follow_enable_lateral_modulation = state_store_.config.scan_follow_enable_lateral_modulation;
    runtime_cfg.pause_hold_position_guard_mm = std::max(0.01, state_store_.config.pause_hold_position_guard_mm);
    runtime_cfg.pause_hold_force_guard_n = std::max(0.1, state_store_.config.pause_hold_force_guard_n);
    runtime_cfg.pause_hold_drift_kp = std::max(0.0, state_store_.config.pause_hold_drift_kp);
    runtime_cfg.pause_hold_drift_ki = std::max(0.0, state_store_.config.pause_hold_drift_ki);
    runtime_cfg.pause_hold_integrator_leak = std::clamp(state_store_.config.pause_hold_integrator_leak, 0.0, 1.0);
    runtime_cfg.contact_control.mode = state_store_.config.contact_control.mode.empty() ? std::string("normal_axis_admittance") : state_store_.config.contact_control.mode;
    runtime_cfg.contact_control.virtual_mass = std::max(0.01, state_store_.config.contact_control.virtual_mass);
    runtime_cfg.contact_control.virtual_damping = std::max(0.0, state_store_.config.contact_control.virtual_damping);
    runtime_cfg.contact_control.virtual_stiffness = std::max(0.0, state_store_.config.contact_control.virtual_stiffness);
    runtime_cfg.contact_control.force_deadband_n = std::max(0.0, state_store_.config.contact_control.force_deadband_n);
    runtime_cfg.contact_control.max_normal_step_mm = std::max(0.01, std::min(state_store_.config.contact_control.max_normal_step_mm, runtime_cfg.rt_max_cart_step_mm));
    runtime_cfg.contact_control.max_normal_velocity_mm_s = std::max(0.1, std::min(state_store_.config.contact_control.max_normal_velocity_mm_s, runtime_cfg.rt_max_cart_vel_mm_s));
    runtime_cfg.contact_control.max_normal_acc_mm_s2 = std::max(1.0, std::min(state_store_.config.contact_control.max_normal_acc_mm_s2, runtime_cfg.rt_max_cart_acc_mm_s2));
    runtime_cfg.contact_control.max_normal_travel_mm = std::max(runtime_cfg.contact_control.max_normal_step_mm, state_store_.config.contact_control.max_normal_travel_mm);
    runtime_cfg.contact_control.anti_windup_limit_n = std::max(0.1, state_store_.config.contact_control.anti_windup_limit_n);
    runtime_cfg.contact_control.integrator_leak = std::clamp(state_store_.config.contact_control.integrator_leak, 0.0, 1.0);
    runtime_cfg.force_estimator.preferred_source = state_store_.config.force_estimator.preferred_source.empty() ? std::string("fused") : state_store_.config.force_estimator.preferred_source;
    runtime_cfg.force_estimator.pressure_weight = std::max(0.0, state_store_.config.force_estimator.pressure_weight);
    runtime_cfg.force_estimator.wrench_weight = std::max(0.0, state_store_.config.force_estimator.wrench_weight);
    runtime_cfg.force_estimator.stale_timeout_ms = std::max(1, state_store_.config.force_estimator.stale_timeout_ms);
    runtime_cfg.force_estimator.timeout_ms = std::max(runtime_cfg.force_estimator.stale_timeout_ms, state_store_.config.force_estimator.timeout_ms);
    runtime_cfg.force_estimator.auto_bias_zero = state_store_.config.force_estimator.auto_bias_zero;
    runtime_cfg.force_estimator.min_confidence = std::clamp(state_store_.config.force_estimator.min_confidence, 0.0, 1.0);
    runtime_cfg.orientation_trim.gain = std::max(0.0, state_store_.config.orientation_trim.gain);
    runtime_cfg.orientation_trim.max_trim_deg = std::max(0.1, state_store_.config.orientation_trim.max_trim_deg);
    runtime_cfg.orientation_trim.lowpass_hz = std::max(0.1, state_store_.config.orientation_trim.lowpass_hz);
    runtime_cfg.retract_release_force_n = std::max(0.1, state_store_.config.retract_release_force_n);
    runtime_cfg.retract_release_cycles = std::max(1, state_store_.config.retract_release_cycles);
    runtime_cfg.retract_safe_gap_mm = std::max(0.1, state_store_.config.retract_safe_gap_mm);
    runtime_cfg.retract_max_travel_mm = std::max(0.1, state_store_.config.retract_max_travel_mm);
    runtime_cfg.retract_jerk_limit_mm_s3 = std::max(1.0, state_store_.config.retract_jerk_limit_mm_s3);
    runtime_cfg.retract_timeout_ms = std::max(10.0, state_store_.config.retract_timeout_ms);
    runtime_cfg.load_kg = state_store_.config.load_kg;
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, state_store_.config.cartesian_impedance.size()); ++idx) runtime_cfg.cartesian_impedance[idx] = state_store_.config.cartesian_impedance[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, state_store_.config.desired_wrench_n.size()); ++idx) runtime_cfg.desired_wrench_n[idx] = state_store_.config.desired_wrench_n[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(16, state_store_.config.fc_frame_matrix.size()); ++idx) runtime_cfg.fc_frame_matrix[idx] = state_store_.config.fc_frame_matrix[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(16, state_store_.config.tcp_frame_matrix.size()); ++idx) runtime_cfg.tcp_frame_matrix[idx] = state_store_.config.tcp_frame_matrix[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(3, state_store_.config.load_com_mm.size()); ++idx) runtime_cfg.load_com_mm[idx] = state_store_.config.load_com_mm[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, state_store_.config.load_inertia.size()); ++idx) runtime_cfg.load_inertia[idx] = state_store_.config.load_inertia[idx];
      procedure_executor_.sdk_robot.rtControlPort().configureMainline(runtime_cfg);
      procedure_executor_.sdk_robot.collaborationPort().setRlStatus(state_store_.config.rl_project_name, state_store_.config.rl_task_name, false);
      procedure_executor_.sdk_robot.collaborationPort().setDragState(false, "cartesian", "admittance");
      std::filesystem::create_directories(state_store_.session_dir);
      evidence_projector_.recording_service.openSession(state_store_.session_dir, state_store_.session_id);
      bindAuthoritySessionLocked(state_store_.session_id);
      state_store_.session_locked_ts_ns = json::nowNs();
      state_store_.execution_state = RobotCoreState::SessionLocked;
      return replyJson(invocation.request_id, true, "lock_session accepted", json::object({json::field("session_id", json::quote(state_store_.session_id))}));
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
    const auto session_id = normalizeAuthorityToken(context.session_id.empty() ? request->session_id.value_or(state_store_.session_id) : context.session_id, state_store_.session_id);
    const auto profile = normalizeAuthorityToken(context.profile.empty() ? request->profile.value_or(std::string("dev")) : context.profile, "dev");
    const auto source = normalizeAuthorityToken(context.source.empty() ? request->source.value_or(std::string("runtime_command")) : context.source, "runtime_command");
    const auto intent_reason = normalizeAuthorityToken(context.intent_reason.empty() ? request->intent_reason.value_or(std::string("runtime_control_authority")) : context.intent_reason, "runtime_control_authority");
    const auto requested_lease_id = normalizeAuthorityToken(context.lease_id.empty() ? request->lease_id.value_or(std::string()) : context.lease_id, "");
    if (authority_kernel_.lease.active) {
      const bool same_owner = authority_kernel_.lease.actor_id == actor_id && authority_kernel_.lease.workspace == workspace && authority_kernel_.lease.role == role;
      if (!same_owner) {
        return replyJson(invocation.request_id, false, "控制权已被 " + authority_kernel_.lease.actor_id + "@" + authority_kernel_.lease.workspace + "/" + authority_kernel_.lease.role + " 持有，当前请求为 " + actor_id + "@" + workspace + "/" + role);
      }
      if (!requested_lease_id.empty() && requested_lease_id != authority_kernel_.lease.lease_id) {
        return replyJson(invocation.request_id, false, "lease_id 不匹配，active=" + authority_kernel_.lease.lease_id);
      }
    }
    authority_kernel_.lease.active = true;
    authority_kernel_.lease.lease_id = requested_lease_id.empty() ? (authority_kernel_.lease.lease_id.empty() ? makeRuntimeLeaseIdLocked(context) : authority_kernel_.lease.lease_id) : requested_lease_id;
    authority_kernel_.lease.actor_id = actor_id;
    authority_kernel_.lease.workspace = workspace;
    authority_kernel_.lease.role = role;
    authority_kernel_.lease.session_id = session_id;
    authority_kernel_.lease.source = source;
    authority_kernel_.lease.intent_reason = intent_reason;
    authority_kernel_.lease.deployment_profile = profile;
    authority_kernel_.lease.acquired_ts_ns = authority_kernel_.lease.acquired_ts_ns == 0 ? json::nowNs() : authority_kernel_.lease.acquired_ts_ns;
    authority_kernel_.lease.refreshed_ts_ns = json::nowNs();
    authority_kernel_.lease.granted_claims.insert("control_authority_write");
    for (const auto& claim : context.requested_claims) {
      if (roleCanClaimLocked(role, claim)) authority_kernel_.lease.granted_claims.insert(claim);
    }
    if (!session_id.empty()) bindAuthoritySessionLocked(session_id);
    return replyJson(invocation.request_id, true, "acquire_control_lease accepted", json::object({
        json::field("summary_state", json::quote("ready")),
        json::field("summary_label", json::quote("控制权租约已获取")),
        json::field("detail", json::quote("cpp_robot_core runtime 持有并发布唯一控制权租约")),
        json::field("lease", json::object({
            json::field("lease_id", json::quote(authority_kernel_.lease.lease_id)),
            json::field("actor_id", json::quote(authority_kernel_.lease.actor_id)),
            json::field("workspace", json::quote(authority_kernel_.lease.workspace)),
            json::field("role", json::quote(authority_kernel_.lease.role)),
            json::field("session_id", json::quote(authority_kernel_.lease.session_id)),
            json::field("acquired_ts_ns", std::to_string(authority_kernel_.lease.acquired_ts_ns)),
            json::field("refreshed_ts_ns", std::to_string(authority_kernel_.lease.refreshed_ts_ns)),
            json::field("source", json::quote(authority_kernel_.lease.source)),
            json::field("deployment_profile", json::quote(authority_kernel_.lease.deployment_profile)),
            json::field("granted_claims", joinClaims(authority_kernel_.lease.granted_claims))
        })),
        json::field("control_authority", controlAuthorityJsonLocked())
    }));
  }
  if (command == "renew_control_lease") {
    const auto* request = invocation.requestAs<RenewControlLeaseRequest>();
    if (request == nullptr) {
      return replyJson(invocation.request_id, false, "typed request mismatch: renew_control_lease");
    }
    if (!authority_kernel_.lease.active) {
      return replyJson(invocation.request_id, false, "当前没有可续租的控制权租约");
    }
    const auto& context = invocation.context();
    const auto lease_id = normalizeAuthorityToken(context.lease_id.empty() ? request->lease_id.value_or(std::string()) : context.lease_id, "");
    const auto actor_id = normalizeAuthorityToken(context.actor_id.empty() ? request->actor_id.value_or(authority_kernel_.lease.actor_id) : context.actor_id, authority_kernel_.lease.actor_id);
    if (lease_id.empty() || lease_id != authority_kernel_.lease.lease_id) {
      return replyJson(invocation.request_id, false, "lease_id 不匹配，active=" + authority_kernel_.lease.lease_id);
    }
    if (actor_id != authority_kernel_.lease.actor_id) {
      return replyJson(invocation.request_id, false, "actor_id 不匹配，active=" + authority_kernel_.lease.actor_id);
    }
    authority_kernel_.lease.refreshed_ts_ns = json::nowNs();
    authority_kernel_.lease.granted_claims.insert("control_authority_write");
    return replyJson(invocation.request_id, true, "renew_control_lease accepted", json::object({
        json::field("summary_state", json::quote("ready")),
        json::field("summary_label", json::quote("控制权租约已续租")),
        json::field("detail", json::quote("cpp_robot_core runtime 已刷新控制权租约")),
        json::field("lease", json::object({
            json::field("lease_id", json::quote(authority_kernel_.lease.lease_id)),
            json::field("actor_id", json::quote(authority_kernel_.lease.actor_id)),
            json::field("workspace", json::quote(authority_kernel_.lease.workspace)),
            json::field("role", json::quote(authority_kernel_.lease.role)),
            json::field("session_id", json::quote(authority_kernel_.lease.session_id)),
            json::field("acquired_ts_ns", std::to_string(authority_kernel_.lease.acquired_ts_ns)),
            json::field("refreshed_ts_ns", std::to_string(authority_kernel_.lease.refreshed_ts_ns)),
            json::field("source", json::quote(authority_kernel_.lease.source)),
            json::field("deployment_profile", json::quote(authority_kernel_.lease.deployment_profile)),
            json::field("granted_claims", joinClaims(authority_kernel_.lease.granted_claims))
        })),
        json::field("control_authority", controlAuthorityJsonLocked())
    }));
  }
  if (command == "release_control_lease") {
    const auto* request = invocation.requestAs<ReleaseControlLeaseRequest>();
    if (request == nullptr) {
      return replyJson(invocation.request_id, false, "typed request mismatch: release_control_lease");
    }
    if (!authority_kernel_.lease.active) {
      return replyJson(invocation.request_id, true, "release_control_lease accepted", json::object({
          json::field("summary_state", json::quote("released")),
          json::field("summary_label", json::quote("当前无活动控制权租约")),
          json::field("detail", json::quote("cpp_robot_core runtime 当前无活动控制权租约")),
          json::field("control_authority", controlAuthorityJsonLocked())
      }));
    }
    const auto& context = invocation.context();
    const auto lease_id = normalizeAuthorityToken(context.lease_id.empty() ? request->lease_id.value_or(std::string()) : context.lease_id, authority_kernel_.lease.lease_id);
    const auto actor_id = normalizeAuthorityToken(context.actor_id.empty() ? request->actor_id.value_or(authority_kernel_.lease.actor_id) : context.actor_id, authority_kernel_.lease.actor_id);
    if (!lease_id.empty() && lease_id != authority_kernel_.lease.lease_id) {
      return replyJson(invocation.request_id, false, "lease_id 不匹配，active=" + authority_kernel_.lease.lease_id);
    }
    if (!actor_id.empty() && actor_id != authority_kernel_.lease.actor_id) {
      return replyJson(invocation.request_id, false, "actor_id 不匹配，active=" + authority_kernel_.lease.actor_id);
    }
    clearAuthoritySessionBindingLocked();
    authority_kernel_.lease = RuntimeAuthorityLease{};
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
    if (state_store_.execution_state != RobotCoreState::SessionLocked && state_store_.execution_state != RobotCoreState::PathValidated &&
        state_store_.execution_state != RobotCoreState::ScanComplete) {
      return replyJson(invocation.request_id, false, "session not locked");
    }
    loadPlanLocked(request->scan_plan, request->scan_plan_hash.value_or(""));
    if (!state_store_.plan_loaded) {
      return replyJson(invocation.request_id, false, "scan plan missing segments");
    }
    if (!state_store_.locked_scan_plan_hash.empty() && !state_store_.plan_hash.empty() && state_store_.locked_scan_plan_hash != state_store_.plan_hash) {
      state_store_.plan_loaded = false;
      state_store_.execution_state = RobotCoreState::SessionLocked;
      state_store_.state_reason = "plan_hash_mismatch";
      return replyJson(invocation.request_id, false, "locked scan_plan_hash does not match loaded plan");
    }
    configureActiveSegmentLocked(nullptr);
    state_store_.execution_state = RobotCoreState::PathValidated;
    state_store_.state_reason = "scan_plan_validated";
    if (evidence_projector_.last_final_verdict.plan_hash.empty() || evidence_projector_.last_final_verdict.plan_hash == state_store_.plan_hash) {
      evidence_projector_.last_final_verdict.accepted = true;
      evidence_projector_.last_final_verdict.reason = "scan plan validated and loaded";
      evidence_projector_.last_final_verdict.detail = "scan plan validated and loaded";
      evidence_projector_.last_final_verdict.policy_state = "ready";
      evidence_projector_.last_final_verdict.next_state = "approach_prescan";
      evidence_projector_.last_final_verdict.plan_id = state_store_.plan_id;
      evidence_projector_.last_final_verdict.plan_hash = state_store_.plan_hash;
      evidence_projector_.last_final_verdict.summary_label = "模型前检通过";
    }
    return replyJson(invocation.request_id, true, "load_scan_plan accepted", json::object({json::field("plan_id", json::quote(state_store_.plan_id))}));
  }
  return replyJson(invocation.request_id, false, "unsupported command: " + command);
}


}  // namespace robot_core
