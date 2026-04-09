#include "robot_core/core_runtime.h"

#include <algorithm>
#include <filesystem>
#include <functional>
#include <unordered_map>

#include "json_utils.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {

std::string CoreRuntime::handleFaultInjectionCommand(const std::string& request_id, const std::string& line) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto command = json::extractString(line, "command");
  using FaultHandler = std::function<std::string(CoreRuntime*, const std::string&, const std::string&)>;
  static const std::unordered_map<std::string, FaultHandler> handlers = {
      {"inject_fault", [](CoreRuntime* self, const std::string& req, const std::string& json_line) {
         const auto fault_name = json::extractString(json_line, "fault_name");
         std::string error_message;
         if (!self->applyFaultInjectionLocked(fault_name, &error_message)) {
           return self->replyJson(req, false, error_message.empty() ? "fault injection failed" : error_message);
         }
         return self->replyJson(req, true, "inject_fault accepted", self->faultInjectionContractJsonLocked());
       }},
      {"clear_injected_faults", [](CoreRuntime* self, const std::string& req, const std::string&) {
         self->clearInjectedFaultsLocked();
         return self->replyJson(req, true, "clear_injected_faults accepted", self->faultInjectionContractJsonLocked());
       }},
  };
  const auto it = handlers.find(command);
  if (it == handlers.end()) {
    return replyJson(request_id, false, "unsupported command: " + command);
  }
  return it->second(this, request_id, line);
}

std::string CoreRuntime::handleSessionCommand(const std::string& request_id, const std::string& line) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto command = json::extractString(line, "command");
  if (command == "lock_session") {
    if (execution_state_ != RobotCoreState::AutoReady) {
      return replyJson(request_id, false, "core not ready for session lock");
    }
    session_id_ = json::extractString(line, "session_id");
    session_dir_ = json::extractString(line, "session_dir");
    if (session_id_.empty() || session_dir_.empty()) {
      return replyJson(request_id, false, "session_id or session_dir missing");
    }
    locked_scan_plan_hash_ = json::extractString(line, "scan_plan_hash");
    applyConfigFromJsonLocked(line);
    tool_ready_ = !config_.tool_name.empty();
    tcp_ready_ = !config_.tcp_name.empty();
    load_ready_ = config_.load_kg > 0.0;
    std::vector<std::string> session_blockers;
    std::vector<std::string> session_warnings;
    appendMainlineContractIssuesLocked(&session_blockers, &session_warnings);
    if (!session_blockers.empty()) {
      session_id_.clear();
      session_dir_.clear();
      locked_scan_plan_hash_.clear();
      return replyJson(request_id, false, session_blockers.front());
    }
    auto runtime_cfg = sdk_robot_.queryPort().runtimeConfig();
    const auto identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
    runtime_cfg.robot_model = identity.robot_model;
    runtime_cfg.sdk_robot_class = identity.sdk_robot_class;
    runtime_cfg.preferred_link = config_.preferred_link.empty() ? identity.preferred_link : config_.preferred_link;
    runtime_cfg.requires_single_control_source = config_.requires_single_control_source;
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
    session_locked_ts_ns_ = json::nowNs();
    execution_state_ = RobotCoreState::SessionLocked;
    return replyJson(request_id, true, "lock_session accepted", json::object({json::field("session_id", json::quote(session_id_))}));
  }
  if (command == "load_scan_plan") {
    if (execution_state_ != RobotCoreState::SessionLocked && execution_state_ != RobotCoreState::PathValidated &&
        execution_state_ != RobotCoreState::ScanComplete) {
      return replyJson(request_id, false, "session not locked");
    }
    loadPlanFromJsonLocked(line);
    if (!plan_loaded_) {
      return replyJson(request_id, false, "scan plan missing segments");
    }
    if (!locked_scan_plan_hash_.empty() && !plan_hash_.empty() && locked_scan_plan_hash_ != plan_hash_) {
      plan_loaded_ = false;
      execution_state_ = RobotCoreState::SessionLocked;
      state_reason_ = "plan_hash_mismatch";
      return replyJson(request_id, false, "locked scan_plan_hash does not match loaded plan");
    }
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
    return replyJson(request_id, true, "load_scan_plan accepted", json::object({json::field("plan_id", json::quote(plan_id_))}));
  }
  return replyJson(request_id, false, "unsupported command: " + command);
}

std::string CoreRuntime::handleExecutionCommand(const std::string& request_id, const std::string& line) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto command = json::extractString(line, "command");
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
  using ExecutionHandler = std::function<std::string(CoreRuntime*, const std::string&, const std::string&)>;
  const std::unordered_map<std::string, ExecutionHandler> handlers = {
      {"approach_prescan", [](CoreRuntime* self, const std::string& req, const std::string&) {
         if (self->execution_state_ != RobotCoreState::PathValidated) {
           return self->replyJson(req, false, "scan plan not ready");
         }
         if (!self->nrt_motion_service_.approachPrescan()) {
           self->execution_state_ = RobotCoreState::Fault;
           return self->replyJson(req, false, "approach_prescan failed");
         }
         self->execution_state_ = RobotCoreState::Approaching;
         self->state_reason_ = "approach_prescan";
         self->contact_state_.recommended_action = "SEEK_CONTACT";
         return self->replyJson(req, true, "approach_prescan accepted");
       }},
      {"seek_contact", [allow_command, validate_rt_phase](CoreRuntime* self, const std::string& req, const std::string&) {
         std::string reason;
         if (!allow_command("seek_contact", &reason)) {
           return self->replyJson(req, false, reason);
         }
         if (!validate_rt_phase("seek_contact precheck failed", &reason)) {
           return self->replyJson(req, false, reason);
         }
         if (!self->rt_motion_service_.seekContact()) {
           return self->replyJson(req, false, "seek_contact failed");
         }
         self->execution_state_ = RobotCoreState::ContactSeeking;
         self->state_reason_ = "waiting_for_contact_stability";
         self->contact_state_.mode = "SEEKING_CONTACT";
         self->contact_state_.recommended_action = "WAIT_CONTACT_STABLE";
         return self->replyJson(req, true, "seek_contact accepted");
       }},
      {"start_scan", [allow_command, validate_rt_phase](CoreRuntime* self, const std::string& req, const std::string&) {
         std::string reason;
         if (!allow_command("start_scan", &reason)) {
           return self->replyJson(req, false, reason);
         }
         if (!validate_rt_phase("start_scan precheck failed", &reason)) {
           return self->replyJson(req, false, reason);
         }
         if (!self->rt_motion_service_.startCartesianImpedance()) {
           return self->replyJson(req, false, "start_scan failed");
         }
         self->execution_state_ = RobotCoreState::Scanning;
         self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, true);
         self->state_reason_ = "scan_active";
         self->contact_state_.mode = "STABLE_CONTACT";
         self->contact_state_.recommended_action = "SCAN";
         return self->replyJson(req, true, "start_scan accepted");
       }},
      {"pause_scan", [](CoreRuntime* self, const std::string& req, const std::string&) {
         if (self->execution_state_ != RobotCoreState::Scanning) {
           return self->replyJson(req, false, "scan not active");
         }
         self->rt_motion_service_.pauseAndHold();
         self->recovery_manager_.pauseAndHold();
         self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, false);
         self->execution_state_ = RobotCoreState::PausedHold;
         self->state_reason_ = "pause_hold";
         self->contact_state_.mode = "HOLDING_CONTACT";
         self->contact_state_.recommended_action = "RESUME_OR_RETREAT";
         return self->replyJson(req, true, "pause_scan accepted");
       }},
      {"resume_scan", [validate_rt_phase](CoreRuntime* self, const std::string& req, const std::string&) {
         if (self->execution_state_ != RobotCoreState::PausedHold) {
           return self->replyJson(req, false, "scan not paused");
         }
         std::string reason;
         if (!validate_rt_phase("resume_scan precheck failed", &reason)) {
           return self->replyJson(req, false, reason);
         }
         if (!self->rt_motion_service_.startCartesianImpedance()) {
           return self->replyJson(req, false, "resume_scan failed");
         }
         self->recovery_manager_.cancelRetry();
         self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, true);
         self->execution_state_ = RobotCoreState::Scanning;
         self->state_reason_ = "scan_active";
         self->contact_state_.mode = "STABLE_CONTACT";
         self->contact_state_.recommended_action = "SCAN";
         return self->replyJson(req, true, "resume_scan accepted");
       }},
      {"safe_retreat", [allow_command](CoreRuntime* self, const std::string& req, const std::string&) {
         std::string reason;
         if (!allow_command("safe_retreat", &reason)) {
           return self->replyJson(req, false, reason);
         }
         self->rt_motion_service_.controlledRetract();
         if (!self->nrt_motion_service_.safeRetreat()) {
           self->execution_state_ = RobotCoreState::Fault;
           self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, false);
           self->fault_code_ = "SAFE_RETREAT_FAILED";
           self->queueAlarmLocked("RECOVERABLE_FAULT", "recovery", "安全退让失败", "safe_retreat", "", "controlled_retract_failed");
           return self->replyJson(req, false, "safe_retreat failed");
         }
         self->recovery_manager_.controlledRetract();
         self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, false);
         self->execution_state_ = RobotCoreState::Retreating;
         self->state_reason_ = "safe_retreat";
         self->retreat_ticks_remaining_ = 30;
         self->contact_state_.mode = "NO_CONTACT";
         self->contact_state_.recommended_action = "WAIT_RETREAT_COMPLETE";
         return self->replyJson(req, true, "safe_retreat accepted");
       }},
      {"go_home", [allow_command](CoreRuntime* self, const std::string& req, const std::string&) {
         std::string reason;
         if (!allow_command("go_home", &reason)) {
           return self->replyJson(req, false, reason);
         }
         const bool ok = self->nrt_motion_service_.goHome();
         return self->replyJson(req, ok, ok ? "go_home accepted" : "go_home failed");
       }},
      {"run_rl_project", [allow_command](CoreRuntime* self, const std::string& req, const std::string& json_line) {
         std::string reason;
         if (!allow_command("run_rl_project", &reason)) {
           return self->replyJson(req, false, reason);
         }
         const auto project = json::extractString(json_line, "project", self->config_.rl_project_name);
         const auto task = json::extractString(json_line, "task", self->config_.rl_task_name);
         if (!self->sdk_robot_.collaborationPort().runRlProject(project, task, &reason)) {
           return self->replyJson(req, false, reason.empty() ? "run_rl_project failed" : reason);
         }
         self->sdk_robot_.collaborationPort().setRlStatus(project, task, true);
         return self->replyJson(req, true, "run_rl_project accepted");
       }},
      {"pause_rl_project", [allow_command](CoreRuntime* self, const std::string& req, const std::string&) {
         std::string reason;
         if (!allow_command("pause_rl_project", &reason)) {
           return self->replyJson(req, false, reason);
         }
         if (!self->sdk_robot_.collaborationPort().pauseRlProject(&reason)) {
           return self->replyJson(req, false, reason.empty() ? "pause_rl_project failed" : reason);
         }
         self->sdk_robot_.collaborationPort().setRlStatus(self->config_.rl_project_name, self->config_.rl_task_name, false);
         return self->replyJson(req, true, "pause_rl_project accepted");
       }},
      {"enable_drag", [allow_command](CoreRuntime* self, const std::string& req, const std::string& json_line) {
         std::string reason;
         if (!allow_command("enable_drag", &reason)) {
           return self->replyJson(req, false, reason);
         }
         const auto space = json::extractString(json_line, "space", "cartesian");
         const auto type = json::extractString(json_line, "type", "admittance");
         if (!self->sdk_robot_.collaborationPort().enableDrag(space, type, &reason)) {
           return self->replyJson(req, false, reason.empty() ? "enable_drag failed" : reason);
         }
         self->sdk_robot_.collaborationPort().setDragState(true, space, type);
         return self->replyJson(req, true, "enable_drag accepted");
       }},
      {"disable_drag", [allow_command](CoreRuntime* self, const std::string& req, const std::string&) {
         std::string reason;
         if (!allow_command("disable_drag", &reason)) {
           return self->replyJson(req, false, reason);
         }
         if (!self->sdk_robot_.collaborationPort().disableDrag(&reason)) {
           return self->replyJson(req, false, reason.empty() ? "disable_drag failed" : reason);
         }
         self->sdk_robot_.collaborationPort().setDragState(false, "cartesian", "admittance");
         return self->replyJson(req, true, "disable_drag accepted");
       }},
      {"replay_path", [allow_command](CoreRuntime* self, const std::string& req, const std::string& json_line) {
         std::string reason;
         if (!allow_command("replay_path", &reason)) {
           return self->replyJson(req, false, reason);
         }
         const auto name = json::extractString(json_line, "name", "spine_demo_path");
         const auto rate = json::extractDouble(json_line, "rate", 0.5);
         if (!self->sdk_robot_.collaborationPort().replayPath(name, rate, &reason)) {
           return self->replyJson(req, false, reason.empty() ? "replay_path failed" : reason);
         }
         return self->replyJson(req, true, "replay_path accepted");
       }},
      {"start_record_path", [allow_command](CoreRuntime* self, const std::string& req, const std::string& json_line) {
         std::string reason;
         if (!allow_command("start_record_path", &reason)) {
           return self->replyJson(req, false, reason);
         }
         const auto duration_s = json::extractInt(json_line, "duration_s", 60);
         if (!self->sdk_robot_.collaborationPort().startRecordPath(duration_s, &reason)) {
           return self->replyJson(req, false, reason.empty() ? "start_record_path failed" : reason);
         }
         return self->replyJson(req, true, "start_record_path accepted");
       }},
      {"stop_record_path", [allow_command](CoreRuntime* self, const std::string& req, const std::string&) {
         std::string reason;
         if (!allow_command("stop_record_path", &reason)) {
           return self->replyJson(req, false, reason);
         }
         if (!self->sdk_robot_.collaborationPort().stopRecordPath(&reason)) {
           return self->replyJson(req, false, reason.empty() ? "stop_record_path failed" : reason);
         }
         return self->replyJson(req, true, "stop_record_path accepted");
       }},
      {"cancel_record_path", [allow_command](CoreRuntime* self, const std::string& req, const std::string&) {
         std::string reason;
         if (!allow_command("cancel_record_path", &reason)) {
           return self->replyJson(req, false, reason);
         }
         if (!self->sdk_robot_.collaborationPort().cancelRecordPath(&reason)) {
           return self->replyJson(req, false, reason.empty() ? "cancel_record_path failed" : reason);
         }
         return self->replyJson(req, true, "cancel_record_path accepted");
       }},
      {"save_record_path", [allow_command](CoreRuntime* self, const std::string& req, const std::string& json_line) {
         std::string reason;
         if (!allow_command("save_record_path", &reason)) {
           return self->replyJson(req, false, reason);
         }
         const auto name = json::extractString(json_line, "name", "spine_demo_path");
         const auto save_as = json::extractString(json_line, "save_as", name);
         if (!self->sdk_robot_.collaborationPort().saveRecordPath(name, save_as, &reason)) {
           return self->replyJson(req, false, reason.empty() ? "save_record_path failed" : reason);
         }
         return self->replyJson(req, true, "save_record_path accepted");
       }},
      {"clear_fault", [](CoreRuntime* self, const std::string& req, const std::string&) {
         if (self->execution_state_ != RobotCoreState::Fault) {
           return self->replyJson(req, false, "no fault to clear");
         }
         self->fault_code_.clear();
         self->execution_state_ = self->plan_loaded_ ? RobotCoreState::PathValidated : RobotCoreState::AutoReady;
         return self->replyJson(req, true, "clear_fault accepted");
       }},
      {"emergency_stop", [](CoreRuntime* self, const std::string& req, const std::string&) {
         self->rt_motion_service_.stop();
         self->recovery_manager_.cancelRetry();
         self->recovery_manager_.latchEstop();
         self->execution_state_ = RobotCoreState::Estop;
         self->fault_code_ = "ESTOP";
         self->queueAlarmLocked("FATAL_FAULT", "safety", "急停触发");
         return self->replyJson(req, true, "emergency_stop accepted");
       }},
  };
  const auto it = handlers.find(command);
  if (it == handlers.end()) {
    return replyJson(request_id, false, "unsupported command: " + command);
  }
  return it->second(this, request_id, line);
}

}  // namespace robot_core
