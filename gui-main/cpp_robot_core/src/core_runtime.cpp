#include "robot_core/core_runtime.h"

#include <algorithm>
#include <cmath>
#include <filesystem>

#include "json_utils.h"
#include "robot_core/force_state.h"
#include "robot_core/safety_decision.h"

namespace robot_core {

namespace {

constexpr int kProtocolVersion = 1;

std::string stateName(RobotCoreState state) {
  switch (state) {
    case RobotCoreState::Boot: return "BOOT";
    case RobotCoreState::Disconnected: return "DISCONNECTED";
    case RobotCoreState::Connected: return "CONNECTED";
    case RobotCoreState::Powered: return "POWERED";
    case RobotCoreState::AutoReady: return "AUTO_READY";
    case RobotCoreState::SessionLocked: return "SESSION_LOCKED";
    case RobotCoreState::PathValidated: return "PATH_VALIDATED";
    case RobotCoreState::Approaching: return "APPROACHING";
    case RobotCoreState::ContactSeeking: return "CONTACT_SEEKING";
    case RobotCoreState::Scanning: return "SCANNING";
    case RobotCoreState::PausedHold: return "PAUSED_HOLD";
    case RobotCoreState::Retreating: return "RETREATING";
    case RobotCoreState::ScanComplete: return "SCAN_COMPLETE";
    case RobotCoreState::Fault: return "FAULT";
    case RobotCoreState::Estop: return "ESTOP";
  }
  return "BOOT";
}

DeviceHealth makeDevice(const std::string& name, bool online, const std::string& detail) {
  DeviceHealth device;
  device.device_name = name;
  device.online = online;
  device.fresh = online;
  device.detail = detail;
  return device;
}

std::vector<double> filledVector(size_t count, double value) {
  return std::vector<double>(count, value);
}

}  // namespace

CoreRuntime::CoreRuntime() {
  devices_ = {
      makeDevice("robot", false, "机械臂控制器未连接"),
      makeDevice("camera", false, "摄像头未连接"),
      makeDevice("pressure", false, "压力传感器未连接"),
      makeDevice("ultrasound", false, "超声设备未连接"),
  };
  recovery_manager_.setRetrySettleWindow(std::chrono::milliseconds(static_cast<int>(force_limits_.force_settle_window_ms)));
}

void CoreRuntime::setState(RobotCoreState state) {
  std::lock_guard<std::mutex> lock(mutex_);
  execution_state_ = state;
}

RobotCoreState CoreRuntime::state() const {
  std::lock_guard<std::mutex> lock(mutex_);
  return execution_state_;
}

std::string CoreRuntime::handleCommandJson(const std::string& line) {
  std::lock_guard<std::mutex> lock(mutex_);
  const auto request_id = json::extractString(line, "request_id");
  const auto command = json::extractString(line, "command");
  if (command == "connect_robot") {
    if (execution_state_ != RobotCoreState::Boot && execution_state_ != RobotCoreState::Disconnected) {
      return replyJson(request_id, false, "robot already connected");
    }
    controller_online_ = true;
    execution_state_ = RobotCoreState::Connected;
    devices_[0] = makeDevice("robot", true, "robot_core 已连接");
    devices_[1] = makeDevice("camera", true, "摄像头在线");
    devices_[2] = makeDevice("pressure", true, "压力传感器在线");
    devices_[3] = makeDevice("ultrasound", true, "超声设备在线");
    return replyJson(request_id, true, "connect_robot accepted");
  }
  if (command == "disconnect_robot") {
    recording_service_.closeSession();
    execution_state_ = RobotCoreState::Disconnected;
    controller_online_ = false;
    powered_ = false;
    automatic_mode_ = false;
    tool_ready_ = false;
    tcp_ready_ = false;
    load_ready_ = false;
    pressure_fresh_ = false;
    robot_state_fresh_ = false;
    rt_jitter_ok_ = true;
    fault_code_.clear();
    session_id_.clear();
    session_dir_.clear();
    plan_id_.clear();
    plan_loaded_ = false;
    total_points_ = 0;
    total_segments_ = 0;
    path_index_ = 0;
    frame_id_ = 0;
    active_segment_ = 0;
    retreat_ticks_remaining_ = 0;
    progress_pct_ = 0.0;
    pressure_current_ = 0.0;
    contact_state_ = ContactTelemetry{};
    pending_alarms_.clear();
    recovery_manager_.resetToIdle();
    devices_ = {
        makeDevice("robot", false, "机械臂控制器未连接"),
        makeDevice("camera", false, "摄像头未连接"),
        makeDevice("pressure", false, "压力传感器未连接"),
        makeDevice("ultrasound", false, "超声设备未连接"),
    };
    return replyJson(request_id, true, "disconnect_robot accepted");
  }
  if (command == "power_on") {
    if (!controller_online_) {
      return replyJson(request_id, false, "robot not connected");
    }
    powered_ = true;
    execution_state_ = RobotCoreState::Powered;
    return replyJson(request_id, true, "power_on accepted");
  }
  if (command == "power_off") {
    powered_ = false;
    automatic_mode_ = false;
    execution_state_ = controller_online_ ? RobotCoreState::Connected : RobotCoreState::Disconnected;
    return replyJson(request_id, true, "power_off accepted");
  }
  if (command == "set_auto_mode") {
    if (!powered_) {
      return replyJson(request_id, false, "robot not powered");
    }
    automatic_mode_ = true;
    execution_state_ = RobotCoreState::AutoReady;
    return replyJson(request_id, true, "set_auto_mode accepted");
  }
  if (command == "set_manual_mode") {
    automatic_mode_ = false;
    execution_state_ = powered_ ? RobotCoreState::Powered : RobotCoreState::Connected;
    return replyJson(request_id, true, "set_manual_mode accepted");
  }
  if (command == "validate_setup") {
    const auto safety = evaluateSafetyLocked();
    const auto data_json = json::object({
        json::field("safe_to_arm", json::boolLiteral(safety.safe_to_arm)),
        json::field("safe_to_scan", json::boolLiteral(safety.safe_to_scan)),
        json::field("active_interlocks", json::stringArray(safety.active_interlocks)),
    });
    return replyJson(request_id, safety.safe_to_arm, safety.safe_to_arm ? "setup validated" : "setup invalid", data_json);
  }
  if (command == "lock_session") {
    if (execution_state_ != RobotCoreState::AutoReady) {
      return replyJson(request_id, false, "core not ready for session lock");
    }
    session_id_ = json::extractString(line, "session_id");
    session_dir_ = json::extractString(line, "session_dir");
    if (session_id_.empty() || session_dir_.empty()) {
      return replyJson(request_id, false, "session_id or session_dir missing");
    }
    applyConfigFromJsonLocked(line);
    tool_ready_ = !config_.tool_name.empty();
    tcp_ready_ = !config_.tcp_name.empty();
    load_ready_ = config_.load_kg > 0.0;
    std::filesystem::create_directories(session_dir_);
    recording_service_.openSession(session_dir_, session_id_);
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
    execution_state_ = RobotCoreState::PathValidated;
    return replyJson(request_id, true, "load_scan_plan accepted", json::object({json::field("plan_id", json::quote(plan_id_))}));
  }
  if (command == "approach_prescan") {
    if (execution_state_ != RobotCoreState::PathValidated) {
      return replyJson(request_id, false, "scan plan not ready");
    }
    nrt_motion_service_.approachPrescan();
    execution_state_ = RobotCoreState::Approaching;
    contact_state_.recommended_action = "SEEK_CONTACT";
    return replyJson(request_id, true, "approach_prescan accepted");
  }
  if (command == "seek_contact") {
    if (execution_state_ != RobotCoreState::Approaching && execution_state_ != RobotCoreState::PathValidated) {
      return replyJson(request_id, false, "cannot seek contact from current state");
    }
    if (!rt_motion_service_.seekContact()) {
      return replyJson(request_id, false, "seek_contact failed");
    }
    execution_state_ = RobotCoreState::ContactSeeking;
    contact_state_.mode = "SEEKING_CONTACT";
    contact_state_.recommended_action = "START_SCAN";
    return replyJson(request_id, true, "seek_contact accepted");
  }
  if (command == "start_scan") {
    if (execution_state_ != RobotCoreState::ContactSeeking && execution_state_ != RobotCoreState::PathValidated &&
        execution_state_ != RobotCoreState::PausedHold) {
      return replyJson(request_id, false, "cannot start scan from current state");
    }
    if (!rt_motion_service_.startCartesianImpedance()) {
      return replyJson(request_id, false, "start_scan failed");
    }
    execution_state_ = RobotCoreState::Scanning;
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
    execution_state_ = RobotCoreState::PausedHold;
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
    execution_state_ = RobotCoreState::Scanning;
    contact_state_.mode = "STABLE_CONTACT";
    contact_state_.recommended_action = "SCAN";
    return replyJson(request_id, true, "resume_scan accepted");
  }
  if (command == "safe_retreat") {
    if (execution_state_ == RobotCoreState::Boot || execution_state_ == RobotCoreState::Disconnected || execution_state_ == RobotCoreState::Estop) {
      return replyJson(request_id, false, "cannot retreat from current state");
    }
    rt_motion_service_.controlledRetract();
    nrt_motion_service_.safeRetreat();
    recovery_manager_.controlledRetract();
    execution_state_ = RobotCoreState::Retreating;
    retreat_ticks_remaining_ = 30;
    contact_state_.mode = "NO_CONTACT";
    contact_state_.recommended_action = "WAIT_RETREAT_COMPLETE";
    return replyJson(request_id, true, "safe_retreat accepted");
  }
  if (command == "go_home") {
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

TelemetrySnapshot CoreRuntime::takeTelemetrySnapshot() {
  std::lock_guard<std::mutex> lock(mutex_);
  TelemetrySnapshot snapshot;
  snapshot.core_state = buildCoreSnapshotLocked();
  snapshot.robot_state = robot_state_hub_.latest();
  snapshot.contact_state = contact_state_;
  snapshot.scan_progress = buildScanProgressLocked();
  snapshot.devices = devices_;
  snapshot.safety_status = evaluateSafetyLocked();
  snapshot.recorder_status = recording_service_.status();
  snapshot.quality_feedback = QualityFeedback{
      image_quality_,
      feature_confidence_,
      quality_score_,
      quality_score_ < 0.7,
  };
  snapshot.alarms = pending_alarms_;
  pending_alarms_.clear();
  return snapshot;
}

void CoreRuntime::rtStep() {
  std::lock_guard<std::mutex> lock(mutex_);
  phase_ += 0.03;
  ++frame_id_;
  updateQualityLocked();
  updateKinematicsLocked();
  updateContactAndProgressLocked();
  refreshDeviceHealthLocked(json::nowNs());
  recordStreamsLocked();
}

void CoreRuntime::statePollStep() {
  std::lock_guard<std::mutex> lock(mutex_);
  RobotStateSnapshot snapshot;
  snapshot.timestamp_ns = json::nowNs();
  snapshot.power_state = powered_ ? "on" : "off";
  snapshot.operate_mode = automatic_mode_ ? "automatic" : "manual";
  snapshot.operation_state = stateName(execution_state_);
  snapshot.joint_pos = {
      std::sin(phase_ * 0.4 + 0.0),
      std::sin(phase_ * 0.4 + 0.2),
      std::sin(phase_ * 0.4 + 0.4),
      std::sin(phase_ * 0.4 + 0.6),
      std::sin(phase_ * 0.4 + 0.8),
      std::sin(phase_ * 0.4 + 1.0),
  };
  snapshot.joint_vel = {
      0.08 * std::cos(phase_ * 0.3 + 0.0),
      0.08 * std::cos(phase_ * 0.3 + 0.2),
      0.08 * std::cos(phase_ * 0.3 + 0.4),
      0.08 * std::cos(phase_ * 0.3 + 0.6),
      0.08 * std::cos(phase_ * 0.3 + 0.8),
      0.08 * std::cos(phase_ * 0.3 + 1.0),
  };
  snapshot.joint_torque = {
      0.45 * std::sin(phase_ * 0.2 + 0.0),
      0.45 * std::sin(phase_ * 0.2 + 0.2),
      0.45 * std::sin(phase_ * 0.2 + 0.4),
      0.45 * std::sin(phase_ * 0.2 + 0.6),
      0.45 * std::sin(phase_ * 0.2 + 0.8),
      0.45 * std::sin(phase_ * 0.2 + 1.0),
  };
  const double z_base = execution_state_ == RobotCoreState::Approaching
                            ? 220.0
                            : (execution_state_ == RobotCoreState::Retreating ? 230.0
                                                                               : (execution_state_ == RobotCoreState::ContactSeeking ||
                                                                                          execution_state_ == RobotCoreState::Scanning ||
                                                                                          execution_state_ == RobotCoreState::PausedHold
                                                                                      ? 205.0
                                                                                      : 240.0));
  snapshot.tcp_pose = {
      118.0 + 8.0 * std::sin(phase_ * 0.2),
      15.0 + 5.0 * std::cos(phase_ * 0.25),
      z_base + 2.5 * std::sin(phase_ * 0.33),
      180.0,
      0.3 * std::sin(phase_),
      90.0,
  };
  snapshot.cart_force = {0.02, 0.01, pressure_current_, 0.0, 0.0, 0.0};
  snapshot.last_event = stateName(execution_state_);
  snapshot.last_controller_log = fault_code_.empty() ? "-" : fault_code_;
  robot_state_hub_.update(snapshot);
}

void CoreRuntime::watchdogStep() {
  std::lock_guard<std::mutex> lock(mutex_);
  const auto safety = evaluateSafetyLocked();
  const auto now = json::nowNs();
  const auto force_state = makeForceStateSnapshot(
      now,
      0.0,
      std::vector<double>{0.0, 0.0, pressure_current_, 0.0, 0.0, 0.0},
      force_limits_,
      config_.pressure_target);
  const auto decision = decideSafetyAction(force_state);
  if (decision == SafetyDecision::WarnOnly && execution_state_ == RobotCoreState::Scanning) {
    queueAlarmLocked("WARN", "force_monitor", "力控接近告警阈值", "force_monitor", "", "warn_only");
  }
  if (pressure_current_ > config_.pressure_upper && execution_state_ == RobotCoreState::Scanning) {
    rt_motion_service_.pauseAndHold();
    recovery_manager_.pauseAndHold();
    execution_state_ = RobotCoreState::PausedHold;
    contact_state_.mode = "OVERPRESSURE";
    contact_state_.recommended_action = "CONTROLLED_RETRACT";
    queueAlarmLocked("RECOVERABLE_FAULT", "contact", "压力超上限，已进入保持状态", "scan_monitor", "", "hold");
  }
  if (decision == SafetyDecision::ControlledRetract && execution_state_ != RobotCoreState::Estop) {
    rt_motion_service_.controlledRetract();
    recovery_manager_.controlledRetract();
    execution_state_ = RobotCoreState::Retreating;
    queueAlarmLocked("RECOVERABLE_FAULT", "force_monitor", "力控进入受控退让", "force_monitor", "", "controlled_retract");
  }
  if (decision == SafetyDecision::EstopLatch && execution_state_ != RobotCoreState::Estop) {
    recovery_manager_.latchEstop();
    execution_state_ = RobotCoreState::Estop;
    queueAlarmLocked("FATAL_FAULT", "force_monitor", "力传感器超时，进入急停锁存", "telemetry_watchdog", "", "estop");
  }
  if (execution_state_ == RobotCoreState::PausedHold || execution_state_ == RobotCoreState::Retreating) {
    const bool within_band = std::fabs(pressure_current_ - config_.pressure_target) <= force_limits_.resume_force_band_n;
    recovery_manager_.updateStableCondition(within_band, now);
  }
  if (!safety.safe_to_arm && controller_online_ && powered_ && automatic_mode_ && execution_state_ != RobotCoreState::Fault &&
      execution_state_ != RobotCoreState::Estop && !fault_code_.empty()) {
    queueAlarmLocked("WARN", "safety", "存在联锁，safe_to_arm 退化", "validate_setup", "", "warn_only");
  }
}

void CoreRuntime::updateKinematicsLocked() {
  if (execution_state_ == RobotCoreState::Retreating && retreat_ticks_remaining_ > 0) {
    --retreat_ticks_remaining_;
    if (retreat_ticks_remaining_ <= 0) {
      execution_state_ = plan_loaded_ ? RobotCoreState::PathValidated : RobotCoreState::AutoReady;
      contact_state_.recommended_action = "IDLE";
    }
  }
}

void CoreRuntime::updateQualityLocked() {
  image_quality_ = 0.78 + 0.12 * std::sin(phase_ * 0.7);
  feature_confidence_ = 0.74 + 0.10 * std::cos(phase_ * 0.45);
  quality_score_ = (image_quality_ + feature_confidence_) / 2.0;
}

void CoreRuntime::updateContactAndProgressLocked() {
  if (execution_state_ == RobotCoreState::ContactSeeking) {
    ContactObservationInput input;
    pressure_current_ = std::max(config_.pressure_lower, config_.pressure_target - 0.1 + 0.04 * std::sin(phase_));
    input.external_pressure = pressure_current_;
    input.cart_force_z = pressure_current_;
    input.quality_score = quality_score_;
    auto observed = contact_observer_.evaluate(input);
    contact_state_.mode = pressure_current_ >= config_.pressure_target - 0.05 ? "STABLE_CONTACT" : observed.mode;
    contact_state_.confidence = 0.78;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = "START_SCAN";
    active_segment_ = std::max(active_segment_, 1);
    return;
  }
  if (execution_state_ == RobotCoreState::Scanning) {
    if (frame_id_ % 25 == 0) {
      ++path_index_;
    }
    if (total_points_ > 0) {
      progress_pct_ = std::min(100.0, 100.0 * static_cast<double>(path_index_) / static_cast<double>(total_points_));
    }
    if (total_segments_ > 0) {
      const int points_per_segment = std::max(total_points_ / total_segments_, 1);
      active_segment_ = std::min(total_segments_, std::max(1, path_index_ / points_per_segment + 1));
    }
    pressure_current_ = config_.pressure_target + 0.08 * std::sin(phase_);
    contact_state_.mode = "STABLE_CONTACT";
    contact_state_.confidence = 0.87;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = "SCAN";
    if (progress_pct_ >= 100.0) {
      execution_state_ = RobotCoreState::ScanComplete;
      contact_state_.mode = "NO_CONTACT";
      contact_state_.recommended_action = "POSTPROCESS";
    }
    return;
  }
  if (execution_state_ == RobotCoreState::PausedHold) {
    pressure_current_ = config_.pressure_target - 0.03;
    contact_state_.mode = "HOLDING_CONTACT";
    contact_state_.confidence = 0.75;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = "RESUME_OR_RETREAT";
    return;
  }
  if (execution_state_ == RobotCoreState::Retreating) {
    pressure_current_ = 0.0;
    contact_state_.mode = "NO_CONTACT";
    contact_state_.confidence = 0.0;
    contact_state_.pressure_current = 0.0;
    contact_state_.recommended_action = "WAIT_RETREAT_COMPLETE";
    return;
  }
  pressure_current_ = std::max(0.0, config_.pressure_target - 0.25);
  contact_state_.mode = "NO_CONTACT";
  contact_state_.confidence = 0.0;
  contact_state_.pressure_current = pressure_current_;
  contact_state_.recommended_action = "IDLE";
}

void CoreRuntime::refreshDeviceHealthLocked(int64_t ts_ns) {
  pressure_fresh_ = false;
  robot_state_fresh_ = false;
  for (auto& device : devices_) {
    device.fresh = device.online;
    device.last_ts_ns = device.online ? ts_ns : 0;
    if (device.device_name == "pressure" && device.online) {
      pressure_fresh_ = true;
    }
    if (device.device_name == "robot" && device.online) {
      robot_state_fresh_ = true;
    }
    if (device.device_name == "robot" && (execution_state_ == RobotCoreState::Fault || execution_state_ == RobotCoreState::Estop)) {
      device.detail = "机器人控制器处于故障或急停状态";
    }
  }
}

SafetyStatus CoreRuntime::evaluateSafetyLocked() const {
  return safety_service_.evaluate(
      controller_online_,
      powered_,
      automatic_mode_,
      !session_id_.empty(),
      plan_loaded_,
      pressure_fresh_,
      robot_state_fresh_,
      pressure_current_ <= config_.pressure_upper,
      rt_jitter_ok_,
      tool_ready_,
      tcp_ready_,
      load_ready_);
}

void CoreRuntime::queueAlarmLocked(const std::string& severity, const std::string& source, const std::string& message, const std::string& workflow_step, const std::string& request_id, const std::string& auto_action) {
  AlarmEvent alarm;
  alarm.severity = severity;
  alarm.source = source;
  alarm.message = message;
  alarm.session_id = session_id_;
  alarm.segment_id = active_segment_;
  alarm.event_ts_ns = json::nowNs();
  alarm.workflow_step = workflow_step;
  alarm.request_id = request_id;
  alarm.auto_action = auto_action;
  pending_alarms_.push_back(alarm);
  recording_service_.recordAlarm(alarm);
  if (severity == "FATAL_FAULT") {
    fault_code_ = source;
    execution_state_ = execution_state_ == RobotCoreState::Estop ? RobotCoreState::Estop : RobotCoreState::Fault;
  }
}

CoreStateSnapshot CoreRuntime::buildCoreSnapshotLocked() const {
  CoreStateSnapshot snapshot;
  snapshot.execution_state = execution_state_;
  snapshot.armed = !session_id_.empty() && plan_loaded_ && execution_state_ != RobotCoreState::Fault && execution_state_ != RobotCoreState::Estop;
  snapshot.fault_code = fault_code_;
  snapshot.active_segment = active_segment_;
  snapshot.progress_pct = progress_pct_;
  snapshot.session_id = session_id_;
  snapshot.recovery_state = recovery_manager_.currentStateName();
  return snapshot;
}

ScanProgress CoreRuntime::buildScanProgressLocked() const {
  ScanProgress progress;
  progress.active_segment = active_segment_;
  progress.path_index = path_index_;
  progress.overall_progress = progress_pct_;
  progress.frame_id = frame_id_;
  return progress;
}

void CoreRuntime::recordStreamsLocked() {
  if (!recording_service_.active()) {
    return;
  }
  recording_service_.recordRobotState(robot_state_hub_.latest());
  recording_service_.recordContactState(contact_state_);
  recording_service_.recordScanProgress(buildCoreSnapshotLocked(), buildScanProgressLocked());
}

void CoreRuntime::applyConfigFromJsonLocked(const std::string& json_line) {
  config_.pressure_target = json::extractDouble(json_line, "pressure_target", config_.pressure_target);
  config_.pressure_upper = json::extractDouble(json_line, "pressure_upper", config_.pressure_upper);
  config_.pressure_lower = json::extractDouble(json_line, "pressure_lower", config_.pressure_lower);
  config_.scan_speed_mm_s = json::extractDouble(json_line, "scan_speed_mm_s", config_.scan_speed_mm_s);
  config_.sample_step_mm = json::extractDouble(json_line, "sample_step_mm", config_.sample_step_mm);
  config_.segment_length_mm = json::extractDouble(json_line, "segment_length_mm", config_.segment_length_mm);
  config_.contact_seek_speed_mm_s = json::extractDouble(json_line, "contact_seek_speed_mm_s", config_.contact_seek_speed_mm_s);
  config_.retreat_speed_mm_s = json::extractDouble(json_line, "retreat_speed_mm_s", config_.retreat_speed_mm_s);
  config_.network_stale_ms = json::extractInt(json_line, "network_stale_ms", config_.network_stale_ms);
  config_.pressure_stale_ms = json::extractInt(json_line, "pressure_stale_ms", config_.pressure_stale_ms);
  config_.telemetry_rate_hz = json::extractInt(json_line, "telemetry_rate_hz", config_.telemetry_rate_hz);
  config_.tool_name = json::extractString(json_line, "tool_name", config_.tool_name);
  config_.tcp_name = json::extractString(json_line, "tcp_name", config_.tcp_name);
  config_.load_kg = json::extractDouble(json_line, "load_kg", config_.load_kg);
  config_.rt_mode = json::extractString(json_line, "rt_mode", config_.rt_mode);
}

void CoreRuntime::loadPlanFromJsonLocked(const std::string& json_line) {
  plan_id_ = json::extractString(json_line, "plan_id");
  const auto segments = json::extractAllInts(json_line, "segment_id");
  total_segments_ = static_cast<int>(segments.size());
  total_points_ = std::max(total_segments_ * std::max(static_cast<int>(config_.segment_length_mm / std::max(config_.sample_step_mm, 0.1)), 2), 0);
  path_index_ = 0;
  progress_pct_ = 0.0;
  active_segment_ = total_segments_ > 0 ? segments.front() : 0;
  plan_loaded_ = total_segments_ > 0;
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

}  // namespace robot_core
