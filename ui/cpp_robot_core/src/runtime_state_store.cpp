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
  return procedure_executor_.sdk_robot.queryPort().runtimeSource() == "simulated_contract";
#else
  return false;
#endif
}

void CoreRuntime::setState(RobotCoreState state) {
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  if (state_store_.execution_state != state) {
    state_store_.last_transition = stateName(state);
  }
  state_store_.execution_state = state;
}

RobotCoreState CoreRuntime::state() const {
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  return state_store_.execution_state;
}

TelemetrySnapshot CoreRuntime::takeTelemetrySnapshot() {
  std::lock_guard<std::mutex> lane_lock(lanes_.query);

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
    std::lock_guard<std::mutex> state_lock(state_store_.mutex);
    core_state = buildCoreSnapshotLocked();
    contact_state = state_store_.contact_state;
    scan_progress = buildScanProgressLocked();
    devices = evidence_projector_.devices;
    alarms = evidence_projector_.pending_alarms;
    evidence_projector_.pending_alarms.clear();
    image_quality = state_store_.image_quality;
    feature_confidence = state_store_.feature_confidence;
    quality_score = state_store_.quality_score;
    quality_source = state_store_.quality_source;
    quality_available = state_store_.quality_available;
    quality_authoritative = state_store_.quality_authoritative;
    quality_threshold = state_store_.config.image_quality_threshold;
  }

  TelemetrySnapshot snapshot;
  snapshot.core_state = core_state;
  snapshot.robot_state = query_projector_.robot_state_hub.latest();
  snapshot.contact_state = contact_state;
  snapshot.scan_progress = scan_progress;
  snapshot.devices = devices;
  {
    std::lock_guard<std::mutex> state_lock(state_store_.mutex);
    snapshot.safety_status = evaluateSafetyLocked();
  }
  snapshot.recorder_status = evidence_projector_.recording_service.status();
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
    std::lock_guard<std::mutex> lane_lock(lanes_.rt);
    std::lock_guard<std::mutex> state_lock(state_store_.mutex);
    state_store_.phase += 0.03;
    ++state_store_.frame_id;
    RtObservedState observed{};
    std::string observed_reason;
    procedure_executor_.sdk_robot.rtControlPort().populateObservedState(observed, &observed_reason);
    const auto phase_telemetry = procedure_executor_.sdk_robot.queryPort().phaseTelemetry();
    updateQualityLocked(observed, phase_telemetry);
    updateKinematicsLocked();
    updateContactAndProgressLocked(observed);
    if (procedure_executor_.scan_procedure_active && state_store_.execution_state == RobotCoreState::Scanning && procedure_executor_.sdk_robot.activeRtPhase() == "idle") {
      std::string transition_reason;
      advancePlanSegmentLocked(&transition_reason);
    }
    refreshDeviceHealthLocked(json::nowNs(), observed);
    record_bundle = buildRecordBundleLocked();
  }
  flushRecordBundle(record_bundle);
}

void CoreRuntime::recordRtLoopSample(double scheduled_period_ms, double execution_ms, double wake_jitter_ms, bool overrun) {
  std::lock_guard<std::mutex> lane_lock(lanes_.rt);
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  procedure_executor_.rt_motion_service.recordLoopSample(scheduled_period_ms, execution_ms, wake_jitter_ms, overrun);
  const auto rt_snapshot = procedure_executor_.rt_motion_service.snapshot();
  const bool within_jitter_budget = std::abs(rt_snapshot.last_wake_jitter_ms) <= rt_snapshot.jitter_budget_ms;
  const bool within_cycle_budget = rt_snapshot.max_cycle_ms <= (rt_snapshot.current_period_ms + rt_snapshot.jitter_budget_ms);
  state_store_.rt_jitter_ok = !overrun && within_jitter_budget && within_cycle_budget;
}

void CoreRuntime::statePollStep() {
  std::lock_guard<std::mutex> lane_lock(lanes_.rt);
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  RtObservedState observed{};
  std::string observed_reason;
  const bool observed_ok = procedure_executor_.sdk_robot.rtControlPort().populateObservedState(observed, &observed_reason);

  RobotStateSnapshot snapshot;
  snapshot.timestamp_ns = json::nowNs();
  snapshot.power_state = procedure_executor_.sdk_robot.powered() ? "on" : "off";
  snapshot.operate_mode = procedure_executor_.sdk_robot.automaticMode() ? "automatic" : "manual";
  snapshot.operation_state = stateName(state_store_.execution_state);
  snapshot.joint_pos = procedure_executor_.sdk_robot.jointPos();
  snapshot.joint_vel = procedure_executor_.sdk_robot.jointVel();
  snapshot.joint_torque = procedure_executor_.sdk_robot.jointTorque();
  snapshot.tcp_pose = procedure_executor_.sdk_robot.tcpPose();
  snapshot.runtime_source = procedure_executor_.sdk_robot.queryPort().runtimeSource();
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
  snapshot.last_event = stateName(state_store_.execution_state);
  snapshot.last_controller_log = state_store_.fault_code.empty() ? "-" : state_store_.fault_code;
  query_projector_.robot_state_hub.update(snapshot);
}

void CoreRuntime::watchdogStep() {
  std::lock_guard<std::mutex> lane_lock(lanes_.rt);
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  const auto safety = evaluateSafetyLocked();
  const auto now = json::nowNs();
  const auto force_state = makeForceStateSnapshot(
      now,
      0.0,
      std::vector<double>{0.0, 0.0, state_store_.pressure_current, 0.0, 0.0, 0.0},
      procedure_executor_.force_limits,
      state_store_.config.pressure_target);
  const auto decision = decideSafetyAction(force_state);
  const auto recovery_decision = procedure_executor_.recovery_policy.evaluate(state_store_.pressure_current, state_store_.config.pressure_target, state_store_.config.pressure_upper, state_store_.pressure_fresh ? 0.0 : static_cast<double>(state_store_.config.pressure_stale_ms));
  (void)recovery_decision;
  const auto rt_snapshot = procedure_executor_.rt_motion_service.snapshot();
  state_store_.rt_jitter_ok = rt_snapshot.overrun_count == 0 && rt_snapshot.max_cycle_ms <= (rt_snapshot.current_period_ms + rt_snapshot.jitter_budget_ms) && std::abs(rt_snapshot.last_wake_jitter_ms) <= rt_snapshot.jitter_budget_ms;
  if (authority_kernel_.injected_faults.count("rt_jitter_high") > 0) {
    state_store_.rt_jitter_ok = false;
  }
  if (authority_kernel_.injected_faults.count("pressure_stale") > 0) {
    state_store_.pressure_fresh = false;
  }
  if (authority_kernel_.injected_faults.count("overpressure") > 0 && state_store_.execution_state == RobotCoreState::Scanning) {
    state_store_.pressure_current = std::max(state_store_.config.pressure_upper + 0.5, procedure_executor_.force_limits.max_z_force_n + 0.5);
  }
  if (decision == SafetyDecision::WarnOnly && state_store_.execution_state == RobotCoreState::Scanning) {
    queueAlarmLocked("WARN", "force_monitor", "力控接近告警阈值", "force_monitor", "", "warn_only");
  }
  if (state_store_.pressure_current > state_store_.config.pressure_upper && state_store_.execution_state == RobotCoreState::Scanning) {
    procedure_executor_.rt_motion_service.pauseAndHold();
    procedure_executor_.recovery_manager.pauseAndHold();
    procedure_executor_.sdk_robot.setRlStatus(state_store_.config.rl_project_name, state_store_.config.rl_task_name, false);
    state_store_.execution_state = RobotCoreState::PausedHold;
    state_store_.contact_state.mode = "OVERPRESSURE";
    state_store_.contact_state.recommended_action = "CONTROLLED_RETRACT";
    queueAlarmLocked("RECOVERABLE_FAULT", "contact", "压力超上限，已进入保持状态", "scan_monitor", "", "hold");
  }
  if (decision == SafetyDecision::ControlledRetract && state_store_.execution_state != RobotCoreState::Estop) {
    const auto rt_retract = procedure_executor_.rt_motion_service.controlledRetract();
    procedure_executor_.sdk_robot.setRlStatus(state_store_.config.rl_project_name, state_store_.config.rl_task_name, false);
    if (rt_retract.canProceedToNrtRetreat()) {
      procedure_executor_.recovery_manager.controlledRetract();
      state_store_.execution_state = RobotCoreState::Retreating;
      queueAlarmLocked("RECOVERABLE_FAULT", "force_monitor", "力控进入受控退让", "force_monitor", rt_retract.reason, "controlled_retract");
    } else {
      procedure_executor_.recovery_manager.cancelRetry();
      state_store_.execution_state = RobotCoreState::Fault;
      state_store_.fault_code = "CONTROLLED_RETRACT_INCOMPLETE";
      queueAlarmLocked("RECOVERABLE_FAULT", "force_monitor", "RT受控回撤未完成，已阻断后续恢复链", "force_monitor", rt_retract.reason, "controlled_retract_incomplete");
    }
  }
  if (decision == SafetyDecision::EstopLatch && state_store_.execution_state != RobotCoreState::Estop) {
    procedure_executor_.recovery_manager.latchEstop();
    state_store_.execution_state = RobotCoreState::Estop;
    queueAlarmLocked("FATAL_FAULT", "force_monitor", "力传感器超时，进入急停锁存", "telemetry_watchdog", "", "estop");
  }
  if (state_store_.execution_state == RobotCoreState::PausedHold || state_store_.execution_state == RobotCoreState::Retreating) {
    const bool within_band = std::fabs(state_store_.pressure_current - state_store_.config.pressure_target) <= procedure_executor_.force_limits.resume_force_band_n;
    procedure_executor_.recovery_manager.updateStableCondition(within_band, now);
  }
  if (!safety.safe_to_arm && state_store_.controller_online && state_store_.powered && state_store_.automatic_mode && state_store_.execution_state != RobotCoreState::Fault &&
      state_store_.execution_state != RobotCoreState::Estop && !state_store_.fault_code.empty()) {
    queueAlarmLocked("WARN", "safety", "存在联锁，safe_to_arm 退化", "validate_setup", "", "warn_only");
  }
}

void CoreRuntime::updateKinematicsLocked() {
  if (state_store_.execution_state == RobotCoreState::Retreating && state_store_.retreat_ticks_remaining > 0) {
    --state_store_.retreat_ticks_remaining;
    if (state_store_.retreat_ticks_remaining <= 0) {
      state_store_.execution_state = state_store_.retreat_completion_state;
      if (state_store_.execution_state == RobotCoreState::ScanComplete) {
        state_store_.contact_state.recommended_action = "POSTPROCESS";
        state_store_.state_reason = "scan_complete";
        procedure_executor_.scan_procedure_active = false;
      } else {
        state_store_.contact_state.recommended_action = "IDLE";
      }
      state_store_.retreat_completion_state = state_store_.plan_loaded ? RobotCoreState::PathValidated : RobotCoreState::AutoReady;
    }
  }
}

void CoreRuntime::updateQualityLocked(const RtObservedState& observed, const RtPhaseTelemetry& phase_telemetry) {
  (void)observed;
  (void)phase_telemetry;
  if (simulatedTelemetryAllowedLocked()) {
    state_store_.image_quality = 0.78 + 0.12 * std::sin(state_store_.phase * 0.7);
    state_store_.feature_confidence = 0.74 + 0.10 * std::cos(state_store_.phase * 0.45);
    state_store_.quality_score = (state_store_.image_quality + state_store_.feature_confidence) / 2.0;
    state_store_.quality_source = "mock_profile_simulated";
    state_store_.quality_available = true;
    state_store_.quality_authoritative = false;
    return;
  }
  state_store_.image_quality = 0.0;
  state_store_.feature_confidence = 0.0;
  state_store_.quality_score = 0.0;
  state_store_.quality_source = "unavailable";
  state_store_.quality_available = false;
  state_store_.quality_authoritative = false;
}

void CoreRuntime::updateContactAndProgressLocked(const RtObservedState& observed) {
  const bool allow_simulated_pressure = simulatedTelemetryAllowedLocked();
  const bool pressure_available = observed.pressure_valid;
  const auto phase_telemetry = procedure_executor_.sdk_robot.queryPort().phaseTelemetry();
  const std::string pressure_source = allow_simulated_pressure && !pressure_available ? "mock_profile_simulated" : pressureSourceName(observed);
  const auto assign_contact_metadata = [&](bool authoritative) {
    state_store_.contact_state.pressure_source = pressure_source;
    state_store_.contact_state.quality_source = state_store_.quality_source;
    state_store_.contact_state.pressure_available = allow_simulated_pressure || pressure_available;
    state_store_.contact_state.quality_available = state_store_.quality_available;
    state_store_.contact_state.authoritative = authoritative;
    state_store_.contact_state.contact_stable = state_store_.execution_state == RobotCoreState::ContactStable || state_store_.execution_state == RobotCoreState::Scanning || state_store_.execution_state == RobotCoreState::PausedHold;
  };

  if (state_store_.execution_state == RobotCoreState::ContactSeeking) {
    ContactObservationInput input;
    if (pressure_available) {
      state_store_.pressure_current = observed.pressure_force_n;
    } else if (allow_simulated_pressure) {
      state_store_.pressure_current = std::max(state_store_.config.pressure_lower, state_store_.config.pressure_target - 0.1 + 0.04 * std::sin(state_store_.phase));
    } else {
      state_store_.pressure_current = 0.0;
      state_store_.contact_stable_since_ns = 0;
      state_store_.contact_state.mode = "WAITING_FOR_PRESSURE_SOURCE";
      state_store_.contact_state.confidence = 0.0;
      state_store_.contact_state.pressure_current = 0.0;
      state_store_.contact_state.recommended_action = "WAIT_PRESSURE_SOURCE";
      assign_contact_metadata(false);
      return;
    }
    input.external_pressure = state_store_.pressure_current;
    input.cart_force_z = state_store_.pressure_current;
    input.quality_score = state_store_.quality_available ? state_store_.quality_score : state_store_.config.image_quality_threshold;
    const auto observed_contact = procedure_executor_.contact_observer.evaluate(input);
    if (state_store_.pressure_current >= state_store_.config.pressure_target - 0.05) {
      if (state_store_.contact_stable_since_ns <= 0) {
        state_store_.contact_stable_since_ns = json::nowNs();
      }
      const auto gate = procedure_executor_.contact_gate.evaluate(state_store_.pressure_current, state_store_.config.pressure_target, state_store_.contact_stable_since_ns, json::nowNs());
      state_store_.contact_state.mode = gate.mode;
      if (gate.contact_stable) {
        state_store_.execution_state = RobotCoreState::ContactStable;
        state_store_.state_reason = "contact_stable";
      }
    } else {
      state_store_.contact_stable_since_ns = 0;
      state_store_.contact_state.mode = observed_contact.mode;
    }
    state_store_.contact_state.confidence = pressure_available ? 0.78 : 0.52;
    state_store_.contact_state.pressure_current = state_store_.pressure_current;
    state_store_.contact_state.recommended_action = state_store_.execution_state == RobotCoreState::ContactStable ? "START_SCAN" : "WAIT_CONTACT_STABLE";
    state_store_.active_segment = std::max(state_store_.active_segment, 1);
    assign_contact_metadata(pressure_available && !allow_simulated_pressure && (!state_store_.quality_available || state_store_.quality_authoritative));
    return;
  }

  if (state_store_.execution_state == RobotCoreState::ContactStable) {
    if (pressure_available) {
      state_store_.pressure_current = observed.pressure_force_n;
    } else if (allow_simulated_pressure) {
      state_store_.pressure_current = state_store_.config.pressure_target;
    } else {
      state_store_.pressure_current = 0.0;
      state_store_.contact_state.mode = "WAITING_FOR_PRESSURE_SOURCE";
      state_store_.contact_state.confidence = 0.0;
      state_store_.contact_state.pressure_current = 0.0;
      state_store_.contact_state.recommended_action = "WAIT_PRESSURE_SOURCE";
      assign_contact_metadata(false);
      return;
    }
    if (authority_kernel_.injected_faults.count("overpressure") > 0) {
      state_store_.pressure_current = std::max(state_store_.config.pressure_upper + 0.5, procedure_executor_.force_limits.max_z_force_n + 0.5);
    }
    state_store_.contact_state.mode = "STABLE_CONTACT";
    state_store_.contact_state.confidence = pressure_available ? 0.83 : 0.58;
    state_store_.contact_state.pressure_current = state_store_.pressure_current;
    state_store_.contact_state.recommended_action = procedure_executor_.scan_procedure_active ? "RUNTIME_START_SCAN" : "START_SCAN";
    assign_contact_metadata(pressure_available && !allow_simulated_pressure && (!state_store_.quality_available || state_store_.quality_authoritative));
    if (procedure_executor_.scan_procedure_active) {
      std::string reason;
      if (!startPlanDrivenScanLocked(&reason)) {
        state_store_.contact_state.recommended_action = "PAUSE_AND_HOLD";
        state_store_.execution_state = RobotCoreState::PausedHold;
        state_store_.state_reason = reason.empty() ? "scan_start_blocked" : reason;
      }
    }
    return;
  }

  if (state_store_.execution_state == RobotCoreState::Scanning) {
    if (!pressure_available && !allow_simulated_pressure) {
      state_store_.pressure_current = 0.0;
      state_store_.contact_state.mode = "PRESSURE_UNAVAILABLE";
      state_store_.contact_state.confidence = 0.0;
      state_store_.contact_state.pressure_current = 0.0;
      state_store_.contact_state.recommended_action = "PAUSE_AND_HOLD";
      assign_contact_metadata(false);
      return;
    }
    state_store_.pressure_current = pressure_available ? observed.pressure_force_n : (state_store_.config.pressure_target + 0.08 * std::sin(state_store_.phase));
    if (authority_kernel_.injected_faults.count("overpressure") > 0) {
      state_store_.pressure_current = std::max(state_store_.config.pressure_upper + 0.5, procedure_executor_.force_limits.max_z_force_n + 0.5);
    }
    updatePlanProgressLocked(observed, phase_telemetry);
    state_store_.contact_state.mode = "STABLE_CONTACT";
    state_store_.contact_state.confidence = pressure_available ? 0.87 : 0.61;
    state_store_.contact_state.pressure_current = state_store_.pressure_current;
    state_store_.contact_state.recommended_action = "SCAN";
    assign_contact_metadata(pressure_available && !allow_simulated_pressure && (!state_store_.quality_available || state_store_.quality_authoritative));
    return;
  }

  if (state_store_.execution_state == RobotCoreState::PausedHold) {
    if (pressure_available) {
      state_store_.pressure_current = observed.pressure_force_n;
    } else if (allow_simulated_pressure) {
      state_store_.pressure_current = state_store_.config.pressure_target - 0.03;
    } else {
      state_store_.pressure_current = 0.0;
      state_store_.contact_state.mode = "WAITING_FOR_PRESSURE_SOURCE";
      state_store_.contact_state.confidence = 0.0;
      state_store_.contact_state.pressure_current = 0.0;
      state_store_.contact_state.recommended_action = "WAIT_PRESSURE_SOURCE";
      assign_contact_metadata(false);
      return;
    }
    state_store_.contact_state.mode = "HOLDING_CONTACT";
    state_store_.contact_state.confidence = pressure_available ? 0.75 : 0.5;
    state_store_.contact_state.pressure_current = state_store_.pressure_current;
    state_store_.contact_state.recommended_action = "RESUME_OR_RETREAT";
    assign_contact_metadata(pressure_available && !allow_simulated_pressure && (!state_store_.quality_available || state_store_.quality_authoritative));
    return;
  }

  if (state_store_.execution_state == RobotCoreState::Retreating) {
    state_store_.pressure_current = 0.0;
    procedure_executor_.sdk_robot.updateSessionRegisters(state_store_.active_segment, state_store_.frame_id);
    state_store_.contact_state.mode = "NO_CONTACT";
    state_store_.contact_state.confidence = 0.0;
    state_store_.contact_state.pressure_current = 0.0;
    state_store_.contact_state.recommended_action = "WAIT_RETREAT_COMPLETE";
    assign_contact_metadata(false);
    return;
  }

  state_store_.pressure_current = 0.0;
  state_store_.contact_stable_since_ns = 0;
  state_store_.contact_state.mode = "NO_CONTACT";
  state_store_.contact_state.confidence = 0.0;
  state_store_.contact_state.pressure_current = 0.0;
  state_store_.contact_state.recommended_action = "IDLE";
  assign_contact_metadata(false);
}

void CoreRuntime::refreshDeviceHealthLocked(int64_t ts_ns, const RtObservedState& observed) {
  state_store_.pressure_fresh = observed.pressure_valid && observed.pressure_age_ms <= static_cast<double>(state_store_.config.pressure_stale_ms);
  state_store_.robot_state_fresh = observed.valid && !observed.stale;
  const bool live_runtime = procedure_executor_.sdk_robot.liveBindingEstablished();
  for (auto& device : evidence_projector_.devices) {
    if (device.device_name == "pressure") {
      device.present = true;
      device.connected = state_store_.pressure_fresh || observed.pressure_valid;
      device.streaming = observed.pressure_valid;
      device.online = device.connected;
      device.authoritative = live_runtime && observed.pressure_valid;
      device.fresh = observed.pressure_valid && state_store_.pressure_fresh;
      device.last_ts_ns = device.fresh ? ts_ns : 0;
      device.detail = device.connected ? (device.fresh ? "压力传感已接入并新鲜" : "压力通道已接入但数据过期") : "压力传感未建立 authoritative stream";
      continue;
    }
    if (device.device_name == "robot") {
      device.present = true;
      device.connected = state_store_.controller_online;
      device.streaming = observed.valid;
      device.online = device.connected;
      device.authoritative = live_runtime;
      device.fresh = device.connected && state_store_.robot_state_fresh;
      device.last_ts_ns = device.fresh ? ts_ns : 0;
      if (state_store_.execution_state == RobotCoreState::Fault || state_store_.execution_state == RobotCoreState::Estop) {
        device.detail = "机器人控制器处于故障或急停状态";
      } else if (device.connected && !device.fresh) {
        device.detail = "机器人状态镜像未收到可信更新";
      } else if (device.connected) {
        device.detail = live_runtime ? "live robot binding active" : "contract-shell connected without live authoritative binding";
      }
      continue;
    }
    device.present = true;
    device.connected = false;
    device.streaming = false;
    device.online = false;
    device.authoritative = false;
    device.fresh = false;
    device.last_ts_ns = 0;
    if (device.detail.empty()) {
      device.detail = std::string("未建立 authoritative ") + device.device_name + " stream";
    }
  }
}

SafetyStatus CoreRuntime::evaluateSafetyLocked() const {
  auto status = services_.safety_service.evaluate(
      state_store_.controller_online,
      state_store_.powered,
      state_store_.automatic_mode,
      !state_store_.session_id.empty(),
      state_store_.plan_loaded,
      state_store_.pressure_fresh,
      state_store_.robot_state_fresh,
      state_store_.pressure_current <= state_store_.config.pressure_upper,
      state_store_.rt_jitter_ok,
      state_store_.tool_ready,
      state_store_.tcp_ready,
      state_store_.load_ready);
  const auto recovery = procedure_executor_.recovery_policy.evaluate(state_store_.pressure_current, state_store_.config.pressure_target, state_store_.config.pressure_upper, state_store_.pressure_fresh ? 0.0 : static_cast<double>(state_store_.config.pressure_stale_ms));
  status.recovery_reason = recovery.reason;
  status.last_recovery_action = recovery.action;
  status.sensor_freshness_ms = state_store_.pressure_fresh ? 0 : state_store_.config.pressure_stale_ms;
  status.pressure_band_state = std::fabs(state_store_.pressure_current - state_store_.config.pressure_target) <= procedure_executor_.force_limits.resume_force_band_n ? "WITHIN_RESUME_BAND" : "OUT_OF_BAND";
  return status;
}

void CoreRuntime::queueAlarmLocked(const std::string& severity, const std::string& source, const std::string& message, const std::string& workflow_step, const std::string& request_id, const std::string& auto_action) {
  AlarmEvent alarm;
  alarm.severity = severity;
  alarm.source = source;
  alarm.message = message;
  alarm.session_id = state_store_.session_id;
  alarm.segment_id = state_store_.active_segment;
  alarm.event_ts_ns = json::nowNs();
  alarm.workflow_step = workflow_step;
  alarm.request_id = request_id;
  alarm.auto_action = auto_action;
  evidence_projector_.pending_alarms.push_back(alarm);
  evidence_projector_.recording_service.recordAlarm(alarm);
  if (severity == "FATAL_FAULT") {
    state_store_.fault_code = source;
    state_store_.execution_state = state_store_.execution_state == RobotCoreState::Estop ? RobotCoreState::Estop : RobotCoreState::Fault;
  }
}

CoreStateSnapshot CoreRuntime::buildCoreSnapshotLocked() const {
  CoreStateSnapshot snapshot;
  snapshot.execution_state = state_store_.execution_state;
  snapshot.armed = !state_store_.session_id.empty() && state_store_.plan_loaded && state_store_.execution_state != RobotCoreState::Fault && state_store_.execution_state != RobotCoreState::Estop;
  snapshot.fault_code = state_store_.fault_code;
  snapshot.active_segment = state_store_.active_segment;
  snapshot.progress_pct = state_store_.progress_pct;
  snapshot.session_id = state_store_.session_id;
  snapshot.recovery_state = procedure_executor_.recovery_manager.currentStateName();
  snapshot.plan_hash = state_store_.plan_hash;
  snapshot.contact_stable = state_store_.execution_state == RobotCoreState::ContactStable || state_store_.execution_state == RobotCoreState::Scanning || state_store_.execution_state == RobotCoreState::PausedHold;
  snapshot.contact_stable_since_ns = state_store_.contact_stable_since_ns;
  snapshot.active_waypoint_index = state_store_.active_waypoint_index;
  snapshot.last_transition = state_store_.last_transition;
  snapshot.state_reason = state_store_.state_reason;
  return snapshot;
}

ScanProgress CoreRuntime::buildScanProgressLocked() const {
  ScanProgress progress;
  progress.active_segment = state_store_.active_segment;
  progress.active_waypoint_index = state_store_.active_waypoint_index;
  progress.completed_waypoints = procedure_executor_.execution_plan_runtime.completed_waypoints;
  progress.total_waypoints = procedure_executor_.execution_plan_runtime.total_waypoints;
  progress.remaining_waypoints = std::max(0, progress.total_waypoints - progress.completed_waypoints);
  progress.path_index = state_store_.path_index;
  progress.overall_progress = state_store_.progress_pct;
  progress.frame_id = state_store_.frame_id;
  progress.checkpoint_tag = procedure_executor_.execution_plan_runtime.active_checkpoint_tag;
  return progress;
}

CoreRuntime::PendingRecordBundle CoreRuntime::buildRecordBundleLocked() const {
  PendingRecordBundle bundle{};
  if (!evidence_projector_.recording_service.active()) {
    return bundle;
  }
  bundle.enabled = true;
  bundle.robot_state = query_projector_.robot_state_hub.latest();
  bundle.contact_state = state_store_.contact_state;
  bundle.core_state = buildCoreSnapshotLocked();
  bundle.scan_progress = buildScanProgressLocked();
  return bundle;
}

void CoreRuntime::flushRecordBundle(const PendingRecordBundle& bundle) {
  if (!bundle.enabled) {
    return;
  }
  evidence_projector_.recording_service.recordRobotState(bundle.robot_state);
  evidence_projector_.recording_service.recordContactState(bundle.contact_state);
  evidence_projector_.recording_service.recordScanProgress(bundle.core_state, bundle.scan_progress);
}

}  // namespace robot_core
