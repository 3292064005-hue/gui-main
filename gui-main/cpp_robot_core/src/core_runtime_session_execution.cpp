#include "robot_core/core_runtime.h"

#include <algorithm>
#include <filesystem>

#include "json_utils.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {

std::string CoreRuntime::handleFaultInjectionCommand(const std::string& request_id, const std::string& line) {
  const auto command = json::extractString(line, "command");
  if (command == "inject_fault") {
    const auto fault_name = json::extractString(line, "fault_name");
    std::string error_message;
    if (!applyFaultInjectionLocked(fault_name, &error_message)) {
      return replyJson(request_id, false, error_message.empty() ? "fault injection failed" : error_message);
    }
    return replyJson(request_id, true, "inject_fault accepted", faultInjectionContractJsonLocked());
  }
  if (command == "clear_injected_faults") {
    clearInjectedFaultsLocked();
    return replyJson(request_id, true, "clear_injected_faults accepted", faultInjectionContractJsonLocked());
  }
  return replyJson(request_id, false, "unsupported command: " + command);
}

std::string CoreRuntime::handleSessionCommand(const std::string& request_id, const std::string& line) {
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
    auto runtime_cfg = sdk_robot_.runtimeConfig();
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
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, config_.cartesian_impedance.size()); ++idx) runtime_cfg.cartesian_impedance[idx] = config_.cartesian_impedance[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, config_.desired_wrench_n.size()); ++idx) runtime_cfg.desired_wrench_n[idx] = config_.desired_wrench_n[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(16, config_.fc_frame_matrix.size()); ++idx) runtime_cfg.fc_frame_matrix[idx] = config_.fc_frame_matrix[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(16, config_.tcp_frame_matrix.size()); ++idx) runtime_cfg.tcp_frame_matrix[idx] = config_.tcp_frame_matrix[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(3, config_.load_com_mm.size()); ++idx) runtime_cfg.load_com_mm[idx] = config_.load_com_mm[idx];
    for (std::size_t idx = 0; idx < std::min<std::size_t>(6, config_.load_inertia.size()); ++idx) runtime_cfg.load_inertia[idx] = config_.load_inertia[idx];
    sdk_robot_.configureRtMainline(runtime_cfg);
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
    sdk_robot_.setDragState(false, "cartesian", "admittance");
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
  const auto command = json::extractString(line, "command");
  if (command == "approach_prescan") {
    if (execution_state_ != RobotCoreState::PathValidated) {
      return replyJson(request_id, false, "scan plan not ready");
    }
    nrt_motion_service_.approachPrescan();
    execution_state_ = RobotCoreState::Approaching;
    state_reason_ = "approach_prescan";
    contact_state_.recommended_action = "SEEK_CONTACT";
    return replyJson(request_id, true, "approach_prescan accepted");
  }
  if (command == "seek_contact") {
    std::string reason;
    if (!state_machine_guard_.allow(command, execution_state_, &reason)) {
      return replyJson(request_id, false, reason);
    }
    if (!rt_motion_service_.seekContact()) {
      return replyJson(request_id, false, "seek_contact failed");
    }
    execution_state_ = RobotCoreState::ContactSeeking;
    state_reason_ = "waiting_for_contact_stability";
    contact_state_.mode = "SEEKING_CONTACT";
    contact_state_.recommended_action = "WAIT_CONTACT_STABLE";
    return replyJson(request_id, true, "seek_contact accepted");
  }
  if (command == "start_scan") {
    std::string reason;
    if (!state_machine_guard_.allow(command, execution_state_, &reason)) {
      return replyJson(request_id, false, reason);
    }
    if (!rt_motion_service_.startCartesianImpedance()) {
      return replyJson(request_id, false, "start_scan failed");
    }
    execution_state_ = RobotCoreState::Scanning;
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, true);
    state_reason_ = "scan_active";
    contact_state_.mode = "STABLE_CONTACT";
    contact_state_.recommended_action = "SCAN";
    return replyJson(request_id, true, "start_scan accepted");
  }
  if (command == "pause_scan") {
    if (execution_state_ != RobotCoreState::Scanning) {
      return replyJson(request_id, false, "scan not active");
    }
    rt_motion_service_.pauseAndHold();
    recovery_manager_.pauseAndHold();
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
    execution_state_ = RobotCoreState::PausedHold;
    state_reason_ = "pause_hold";
    contact_state_.mode = "HOLDING_CONTACT";
    contact_state_.recommended_action = "RESUME_OR_RETREAT";
    return replyJson(request_id, true, "pause_scan accepted");
  }
  if (command == "resume_scan") {
    if (execution_state_ != RobotCoreState::PausedHold) {
      return replyJson(request_id, false, "scan not paused");
    }
    if (!rt_motion_service_.startCartesianImpedance()) {
      return replyJson(request_id, false, "resume_scan failed");
    }
    recovery_manager_.cancelRetry();
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, true);
    execution_state_ = RobotCoreState::Scanning;
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, true);
    state_reason_ = "scan_active";
    contact_state_.mode = "STABLE_CONTACT";
    contact_state_.recommended_action = "SCAN";
    return replyJson(request_id, true, "resume_scan accepted");
  }
  if (command == "safe_retreat") {
    std::string reason;
    if (!state_machine_guard_.allow(command, execution_state_, &reason)) {
      return replyJson(request_id, false, reason);
    }
    rt_motion_service_.controlledRetract();
    nrt_motion_service_.safeRetreat();
    recovery_manager_.controlledRetract();
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
    execution_state_ = RobotCoreState::Retreating;
    state_reason_ = "safe_retreat";
    retreat_ticks_remaining_ = 30;
    contact_state_.mode = "NO_CONTACT";
    contact_state_.recommended_action = "WAIT_RETREAT_COMPLETE";
    return replyJson(request_id, true, "safe_retreat accepted");
  }
  if (command == "go_home") {
    std::string reason;
    if (!state_machine_guard_.allow(command, execution_state_, &reason)) {
      return replyJson(request_id, false, reason);
    }
    nrt_motion_service_.goHome();
    return replyJson(request_id, true, "go_home accepted");
  }
  if (command == "clear_fault") {
    if (execution_state_ != RobotCoreState::Fault) {
      return replyJson(request_id, false, "no fault to clear");
    }
    fault_code_.clear();
    execution_state_ = plan_loaded_ ? RobotCoreState::PathValidated : RobotCoreState::AutoReady;
    return replyJson(request_id, true, "clear_fault accepted");
  }
  if (command == "emergency_stop") {
    rt_motion_service_.stop();
    recovery_manager_.cancelRetry();
    recovery_manager_.latchEstop();
    execution_state_ = RobotCoreState::Estop;
    fault_code_ = "ESTOP";
    queueAlarmLocked("FATAL_FAULT", "safety", "急停触发");
    return replyJson(request_id, true, "emergency_stop accepted");
  }
  return replyJson(request_id, false, "unsupported command: " + command);
}

}  // namespace robot_core
