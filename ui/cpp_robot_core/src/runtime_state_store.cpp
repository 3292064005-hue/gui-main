#include "robot_core/core_runtime.h"

#include <cmath>

#include "json_utils.h"
#include "robot_core/force_state.h"
#include "robot_core/safety_decision.h"

namespace robot_core {

namespace {

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
    case RobotCoreState::ContactStable: return "CONTACT_STABLE";
    case RobotCoreState::Scanning: return "SCANNING";
    case RobotCoreState::PausedHold: return "PAUSED_HOLD";
    case RobotCoreState::RecoveryRetract: return "RECOVERY_RETRACT";
    case RobotCoreState::SegmentAborted: return "SEGMENT_ABORTED";
    case RobotCoreState::PlanAborted: return "PLAN_ABORTED";
    case RobotCoreState::Retreating: return "RETREATING";
    case RobotCoreState::ScanComplete: return "SCAN_COMPLETE";
    case RobotCoreState::Fault: return "FAULT";
    case RobotCoreState::Estop: return "ESTOP";
  }
  return "BOOT";
}

std::vector<double> arrayToVector(const std::array<double, 6>& values) {
  return std::vector<double>(values.begin(), values.end());
}

bool hasNonZeroMagnitude(const std::vector<double>& values) {
  for (double value : values) {
    if (std::fabs(value) > 1e-9) {
      return true;
    }
  }
  return false;
}

std::string pressureSourceName(const RtObservedState& observed) {
  return observed.pressure_valid ? "pressure_sensor" : "unavailable";
}

}  // namespace

bool CoreRuntime::simulatedTelemetryAllowedLocked() const {
#if defined(ROBOT_CORE_PROFILE_mock)
  return sdk_robot_.queryPort().runtimeSource() == "simulated_contract";
#else
  return false;
#endif
}

void CoreRuntime::setState(RobotCoreState state) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  if (execution_state_ != state) {
    last_transition_ = stateName(state);
  }
  execution_state_ = state;
}

RobotCoreState CoreRuntime::state() const {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  return execution_state_;
}

TelemetrySnapshot CoreRuntime::takeTelemetrySnapshot() {
  std::lock_guard<std::mutex> lane_lock(query_lane_mutex_);

  CoreStateSnapshot core_state;
  ContactTelemetry contact_state;
  ScanProgress scan_progress;
  std::vector<DeviceHealth> devices;
  std::vector<AlarmEvent> alarms;
  double image_quality = 0.0;
  double feature_confidence = 0.0;
  double quality_score = 0.0;
  std::string quality_source;
  bool quality_available = false;
  bool quality_authoritative = false;
  double quality_threshold = 0.7;
  {
    std::lock_guard<std::mutex> state_lock(state_mutex_);
    core_state = buildCoreSnapshotLocked();
    contact_state = contact_state_;
    scan_progress = buildScanProgressLocked();
    devices = devices_;
    alarms = pending_alarms_;
    pending_alarms_.clear();
    image_quality = image_quality_;
    feature_confidence = feature_confidence_;
    quality_score = quality_score_;
    quality_source = quality_source_;
    quality_available = quality_available_;
    quality_authoritative = quality_authoritative_;
    quality_threshold = config_.image_quality_threshold;
  }

  TelemetrySnapshot snapshot;
  snapshot.core_state = core_state;
  snapshot.robot_state = robot_state_hub_.latest();
  snapshot.contact_state = contact_state;
  snapshot.scan_progress = scan_progress;
  snapshot.devices = devices;
  {
    std::lock_guard<std::mutex> state_lock(state_mutex_);
    snapshot.safety_status = evaluateSafetyLocked();
  }
  snapshot.recorder_status = recording_service_.status();
  snapshot.quality_feedback = QualityFeedback{
      image_quality,
      feature_confidence,
      quality_score,
      quality_available ? quality_score < quality_threshold : true,
      quality_source,
      quality_available,
      quality_authoritative,
  };
  snapshot.alarms = alarms;
  return snapshot;
}

void CoreRuntime::rtStep() {
  PendingRecordBundle record_bundle{};
  {
    std::lock_guard<std::mutex> lane_lock(rt_lane_mutex_);
    std::lock_guard<std::mutex> state_lock(state_mutex_);
    phase_ += 0.03;
    ++frame_id_;
    RtObservedState observed{};
    std::string observed_reason;
    sdk_robot_.rtControlPort().populateObservedState(observed, &observed_reason);
    const auto phase_telemetry = sdk_robot_.queryPort().phaseTelemetry();
    updateQualityLocked(observed, phase_telemetry);
    updateKinematicsLocked();
    updateContactAndProgressLocked(observed);
    refreshDeviceHealthLocked(json::nowNs(), observed);
    record_bundle = buildRecordBundleLocked();
  }
  flushRecordBundle(record_bundle);
}

void CoreRuntime::recordRtLoopSample(double scheduled_period_ms, double execution_ms, double wake_jitter_ms, bool overrun) {
  std::lock_guard<std::mutex> lane_lock(rt_lane_mutex_);
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  rt_motion_service_.recordLoopSample(scheduled_period_ms, execution_ms, wake_jitter_ms, overrun);
  const auto rt_snapshot = rt_motion_service_.snapshot();
  const bool within_jitter_budget = std::abs(rt_snapshot.last_wake_jitter_ms) <= rt_snapshot.jitter_budget_ms;
  const bool within_cycle_budget = rt_snapshot.max_cycle_ms <= (rt_snapshot.current_period_ms + rt_snapshot.jitter_budget_ms);
  rt_jitter_ok_ = !overrun && within_jitter_budget && within_cycle_budget;
}

void CoreRuntime::statePollStep() {
  std::lock_guard<std::mutex> lane_lock(rt_lane_mutex_);
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  RtObservedState observed{};
  std::string observed_reason;
  const bool observed_ok = sdk_robot_.rtControlPort().populateObservedState(observed, &observed_reason);

  RobotStateSnapshot snapshot;
  snapshot.timestamp_ns = json::nowNs();
  snapshot.power_state = sdk_robot_.powered() ? "on" : "off";
  snapshot.operate_mode = sdk_robot_.automaticMode() ? "automatic" : "manual";
  snapshot.operation_state = stateName(execution_state_);
  snapshot.joint_pos = sdk_robot_.jointPos();
  snapshot.joint_vel = sdk_robot_.jointVel();
  snapshot.joint_torque = sdk_robot_.jointTorque();
  snapshot.tcp_pose = sdk_robot_.tcpPose();
  snapshot.runtime_source = sdk_robot_.queryPort().runtimeSource();
  snapshot.pose_available = !snapshot.tcp_pose.empty();
  snapshot.pose_source = snapshot.pose_available ? (observed_ok && observed.valid ? "sdk_query_cache" : "runtime_cache") : "unavailable";
  snapshot.pose_authoritative = snapshot.pose_available && snapshot.runtime_source != "simulated_contract";
  snapshot.cart_force = arrayToVector(observed.external_wrench);
  if (snapshot.cart_force.size() < 6) {
    snapshot.cart_force.resize(6, 0.0);
  }
  if (observed.pressure_valid && snapshot.cart_force.size() >= 3) {
    snapshot.cart_force[2] = observed.pressure_force_n;
  }
  snapshot.force_available = observed.pressure_valid || (observed.valid && hasNonZeroMagnitude(snapshot.cart_force));
  snapshot.force_source = observed.pressure_valid ? "pressure_sensor" : (snapshot.force_available ? "external_wrench" : "unavailable");
  snapshot.force_authoritative = snapshot.force_available && snapshot.runtime_source != "simulated_contract";
  snapshot.last_event = stateName(execution_state_);
  snapshot.last_controller_log = fault_code_.empty() ? "-" : fault_code_;
  robot_state_hub_.update(snapshot);
}

void CoreRuntime::watchdogStep() {
  std::lock_guard<std::mutex> lane_lock(rt_lane_mutex_);
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto safety = evaluateSafetyLocked();
  const auto now = json::nowNs();
  const auto force_state = makeForceStateSnapshot(
      now,
      0.0,
      std::vector<double>{0.0, 0.0, pressure_current_, 0.0, 0.0, 0.0},
      force_limits_,
      config_.pressure_target);
  const auto decision = decideSafetyAction(force_state);
  const auto recovery_decision = recovery_policy_.evaluate(pressure_current_, config_.pressure_target, config_.pressure_upper, pressure_fresh_ ? 0.0 : static_cast<double>(config_.pressure_stale_ms));
  (void)recovery_decision;
  const auto rt_snapshot = rt_motion_service_.snapshot();
  rt_jitter_ok_ = rt_snapshot.overrun_count == 0 && rt_snapshot.max_cycle_ms <= (rt_snapshot.current_period_ms + rt_snapshot.jitter_budget_ms) && std::abs(rt_snapshot.last_wake_jitter_ms) <= rt_snapshot.jitter_budget_ms;
  if (injected_faults_.count("rt_jitter_high") > 0) {
    rt_jitter_ok_ = false;
  }
  if (injected_faults_.count("pressure_stale") > 0) {
    pressure_fresh_ = false;
  }
  if (injected_faults_.count("overpressure") > 0 && execution_state_ == RobotCoreState::Scanning) {
    pressure_current_ = std::max(config_.pressure_upper + 0.5, force_limits_.max_z_force_n + 0.5);
  }
  if (decision == SafetyDecision::WarnOnly && execution_state_ == RobotCoreState::Scanning) {
    queueAlarmLocked("WARN", "force_monitor", "力控接近告警阈值", "force_monitor", "", "warn_only");
  }
  if (pressure_current_ > config_.pressure_upper && execution_state_ == RobotCoreState::Scanning) {
    rt_motion_service_.pauseAndHold();
    recovery_manager_.pauseAndHold();
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
    execution_state_ = RobotCoreState::PausedHold;
    contact_state_.mode = "OVERPRESSURE";
    contact_state_.recommended_action = "CONTROLLED_RETRACT";
    queueAlarmLocked("RECOVERABLE_FAULT", "contact", "压力超上限，已进入保持状态", "scan_monitor", "", "hold");
  }
  if (decision == SafetyDecision::ControlledRetract && execution_state_ != RobotCoreState::Estop) {
    rt_motion_service_.controlledRetract();
    recovery_manager_.controlledRetract();
    sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
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

void CoreRuntime::updateQualityLocked(const RtObservedState& observed, const RtPhaseTelemetry& phase_telemetry) {
  (void)observed;
  (void)phase_telemetry;
  if (simulatedTelemetryAllowedLocked()) {
    image_quality_ = 0.78 + 0.12 * std::sin(phase_ * 0.7);
    feature_confidence_ = 0.74 + 0.10 * std::cos(phase_ * 0.45);
    quality_score_ = (image_quality_ + feature_confidence_) / 2.0;
    quality_source_ = "mock_profile_simulated";
    quality_available_ = true;
    quality_authoritative_ = false;
    return;
  }
  image_quality_ = 0.0;
  feature_confidence_ = 0.0;
  quality_score_ = 0.0;
  quality_source_ = "unavailable";
  quality_available_ = false;
  quality_authoritative_ = false;
}

void CoreRuntime::updateContactAndProgressLocked(const RtObservedState& observed) {
  const bool allow_simulated_pressure = simulatedTelemetryAllowedLocked();
  const bool pressure_available = observed.pressure_valid;
  const std::string pressure_source = allow_simulated_pressure && !pressure_available ? "mock_profile_simulated" : pressureSourceName(observed);
  const auto assign_contact_metadata = [&](bool authoritative) {
    contact_state_.pressure_source = pressure_source;
    contact_state_.quality_source = quality_source_;
    contact_state_.pressure_available = allow_simulated_pressure || pressure_available;
    contact_state_.quality_available = quality_available_;
    contact_state_.authoritative = authoritative;
    contact_state_.contact_stable = execution_state_ == RobotCoreState::ContactStable || execution_state_ == RobotCoreState::Scanning || execution_state_ == RobotCoreState::PausedHold;
  };

  if (execution_state_ == RobotCoreState::ContactSeeking) {
    ContactObservationInput input;
    if (pressure_available) {
      pressure_current_ = observed.pressure_force_n;
    } else if (allow_simulated_pressure) {
      pressure_current_ = std::max(config_.pressure_lower, config_.pressure_target - 0.1 + 0.04 * std::sin(phase_));
    } else {
      pressure_current_ = 0.0;
      contact_stable_since_ns_ = 0;
      contact_state_.mode = "WAITING_FOR_PRESSURE_SOURCE";
      contact_state_.confidence = 0.0;
      contact_state_.pressure_current = 0.0;
      contact_state_.recommended_action = "WAIT_PRESSURE_SOURCE";
      assign_contact_metadata(false);
      return;
    }
    input.external_pressure = pressure_current_;
    input.cart_force_z = pressure_current_;
    input.quality_score = quality_available_ ? quality_score_ : config_.image_quality_threshold;
    const auto observed_contact = contact_observer_.evaluate(input);
    if (pressure_current_ >= config_.pressure_target - 0.05) {
      if (contact_stable_since_ns_ <= 0) {
        contact_stable_since_ns_ = json::nowNs();
      }
      const auto gate = contact_gate_.evaluate(pressure_current_, config_.pressure_target, contact_stable_since_ns_, json::nowNs());
      contact_state_.mode = gate.mode;
      if (gate.contact_stable) {
        execution_state_ = RobotCoreState::ContactStable;
        state_reason_ = "contact_stable";
      }
    } else {
      contact_stable_since_ns_ = 0;
      contact_state_.mode = observed_contact.mode;
    }
    contact_state_.confidence = pressure_available ? 0.78 : 0.52;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = execution_state_ == RobotCoreState::ContactStable ? "START_SCAN" : "WAIT_CONTACT_STABLE";
    active_segment_ = std::max(active_segment_, 1);
    assign_contact_metadata(pressure_available && !allow_simulated_pressure && (!quality_available_ || quality_authoritative_));
    return;
  }

  if (execution_state_ == RobotCoreState::ContactStable) {
    if (pressure_available) {
      pressure_current_ = observed.pressure_force_n;
    } else if (allow_simulated_pressure) {
      pressure_current_ = config_.pressure_target;
    } else {
      pressure_current_ = 0.0;
      contact_state_.mode = "WAITING_FOR_PRESSURE_SOURCE";
      contact_state_.confidence = 0.0;
      contact_state_.pressure_current = 0.0;
      contact_state_.recommended_action = "WAIT_PRESSURE_SOURCE";
      assign_contact_metadata(false);
      return;
    }
    if (injected_faults_.count("overpressure") > 0) {
      pressure_current_ = std::max(config_.pressure_upper + 0.5, force_limits_.max_z_force_n + 0.5);
    }
    contact_state_.mode = "STABLE_CONTACT";
    contact_state_.confidence = pressure_available ? 0.83 : 0.58;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = "START_SCAN";
    assign_contact_metadata(pressure_available && !allow_simulated_pressure && (!quality_available_ || quality_authoritative_));
    return;
  }

  if (execution_state_ == RobotCoreState::Scanning) {
    if (!pressure_available && !allow_simulated_pressure) {
      pressure_current_ = 0.0;
      contact_state_.mode = "PRESSURE_UNAVAILABLE";
      contact_state_.confidence = 0.0;
      contact_state_.pressure_current = 0.0;
      contact_state_.recommended_action = "PAUSE_AND_HOLD";
      assign_contact_metadata(false);
      return;
    }
    if (frame_id_ % 25 == 0) {
      ++path_index_;
    }
    if (total_points_ > 0) {
      progress_pct_ = std::min(100.0, 100.0 * static_cast<double>(path_index_) / static_cast<double>(total_points_));
      active_waypoint_index_ = std::min(total_points_, path_index_);
    }
    if (total_segments_ > 0) {
      const int points_per_segment = std::max(total_points_ / total_segments_, 1);
      active_segment_ = std::min(total_segments_, std::max(1, path_index_ / points_per_segment + 1));
    }
    sdk_robot_.updateSessionRegisters(active_segment_, frame_id_);
    pressure_current_ = pressure_available ? observed.pressure_force_n : (config_.pressure_target + 0.08 * std::sin(phase_));
    if (injected_faults_.count("overpressure") > 0) {
      pressure_current_ = std::max(config_.pressure_upper + 0.5, force_limits_.max_z_force_n + 0.5);
    }
    contact_state_.mode = "STABLE_CONTACT";
    contact_state_.confidence = pressure_available ? 0.87 : 0.61;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = "SCAN";
    assign_contact_metadata(pressure_available && !allow_simulated_pressure && (!quality_available_ || quality_authoritative_));
    if (progress_pct_ >= 100.0) {
      sdk_robot_.setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
      execution_state_ = RobotCoreState::ScanComplete;
      contact_state_.mode = "NO_CONTACT";
      contact_state_.recommended_action = "POSTPROCESS";
      contact_state_.contact_stable = false;
    }
    return;
  }

  if (execution_state_ == RobotCoreState::PausedHold) {
    if (pressure_available) {
      pressure_current_ = observed.pressure_force_n;
    } else if (allow_simulated_pressure) {
      pressure_current_ = config_.pressure_target - 0.03;
    } else {
      pressure_current_ = 0.0;
      contact_state_.mode = "WAITING_FOR_PRESSURE_SOURCE";
      contact_state_.confidence = 0.0;
      contact_state_.pressure_current = 0.0;
      contact_state_.recommended_action = "WAIT_PRESSURE_SOURCE";
      assign_contact_metadata(false);
      return;
    }
    contact_state_.mode = "HOLDING_CONTACT";
    contact_state_.confidence = pressure_available ? 0.75 : 0.5;
    contact_state_.pressure_current = pressure_current_;
    contact_state_.recommended_action = "RESUME_OR_RETREAT";
    assign_contact_metadata(pressure_available && !allow_simulated_pressure && (!quality_available_ || quality_authoritative_));
    return;
  }

  if (execution_state_ == RobotCoreState::Retreating) {
    pressure_current_ = 0.0;
    sdk_robot_.updateSessionRegisters(active_segment_, frame_id_);
    contact_state_.mode = "NO_CONTACT";
    contact_state_.confidence = 0.0;
    contact_state_.pressure_current = 0.0;
    contact_state_.recommended_action = "WAIT_RETREAT_COMPLETE";
    assign_contact_metadata(false);
    return;
  }

  pressure_current_ = 0.0;
  contact_stable_since_ns_ = 0;
  contact_state_.mode = "NO_CONTACT";
  contact_state_.confidence = 0.0;
  contact_state_.pressure_current = 0.0;
  contact_state_.recommended_action = "IDLE";
  assign_contact_metadata(false);
}

void CoreRuntime::refreshDeviceHealthLocked(int64_t ts_ns, const RtObservedState& observed) {
  pressure_fresh_ = observed.pressure_valid && observed.pressure_age_ms <= static_cast<double>(config_.pressure_stale_ms);
  robot_state_fresh_ = observed.valid && !observed.stale;
  for (auto& device : devices_) {
    if (device.device_name == "pressure") {
      device.fresh = device.online && pressure_fresh_;
      device.last_ts_ns = pressure_fresh_ ? ts_ns : 0;
      if (device.online && !pressure_fresh_) {
        device.detail = "压力信号不可用或已过期";
      }
      continue;
    }
    if (device.device_name == "robot") {
      device.fresh = device.online && robot_state_fresh_;
      device.last_ts_ns = robot_state_fresh_ ? ts_ns : 0;
      if (device.online && !robot_state_fresh_) {
        device.detail = "机器人状态镜像未收到可信更新";
      }
      if (execution_state_ == RobotCoreState::Fault || execution_state_ == RobotCoreState::Estop) {
        device.detail = "机器人控制器处于故障或急停状态";
      }
      continue;
    }
    device.fresh = device.online;
    device.last_ts_ns = device.online ? ts_ns : 0;
  }
}

SafetyStatus CoreRuntime::evaluateSafetyLocked() const {
  auto status = safety_service_.evaluate(
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
  const auto recovery = recovery_policy_.evaluate(pressure_current_, config_.pressure_target, config_.pressure_upper, pressure_fresh_ ? 0.0 : static_cast<double>(config_.pressure_stale_ms));
  status.recovery_reason = recovery.reason;
  status.last_recovery_action = recovery.action;
  status.sensor_freshness_ms = pressure_fresh_ ? 0 : config_.pressure_stale_ms;
  status.pressure_band_state = std::fabs(pressure_current_ - config_.pressure_target) <= force_limits_.resume_force_band_n ? "WITHIN_RESUME_BAND" : "OUT_OF_BAND";
  return status;
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
  snapshot.plan_hash = plan_hash_;
  snapshot.contact_stable = execution_state_ == RobotCoreState::ContactStable || execution_state_ == RobotCoreState::Scanning || execution_state_ == RobotCoreState::PausedHold;
  snapshot.contact_stable_since_ns = contact_stable_since_ns_;
  snapshot.active_waypoint_index = active_waypoint_index_;
  snapshot.last_transition = last_transition_;
  snapshot.state_reason = state_reason_;
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

CoreRuntime::PendingRecordBundle CoreRuntime::buildRecordBundleLocked() const {
  PendingRecordBundle bundle{};
  if (!recording_service_.active()) {
    return bundle;
  }
  bundle.enabled = true;
  bundle.robot_state = robot_state_hub_.latest();
  bundle.contact_state = contact_state_;
  bundle.core_state = buildCoreSnapshotLocked();
  bundle.scan_progress = buildScanProgressLocked();
  return bundle;
}

void CoreRuntime::flushRecordBundle(const PendingRecordBundle& bundle) {
  if (!bundle.enabled) {
    return;
  }
  recording_service_.recordRobotState(bundle.robot_state);
  recording_service_.recordContactState(bundle.contact_state);
  recording_service_.recordScanProgress(bundle.core_state, bundle.scan_progress);
}

}  // namespace robot_core
