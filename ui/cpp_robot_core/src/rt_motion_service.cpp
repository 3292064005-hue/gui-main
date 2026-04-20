#include "robot_core/rt_motion_service.h"

#include <algorithm>
#include <cmath>
#include <thread>

#include "robot_core/force_control_config.h"
#include "robot_core/sdk_robot_facade.h"

namespace robot_core {

AdaptiveTimer::AdaptiveTimer(double min_period_ms, double max_period_ms, double target_cpu)
    : min_period_ms_(min_period_ms), max_period_ms_(max_period_ms), target_cpu_(target_cpu), current_period_ms_(min_period_ms) {}

void AdaptiveTimer::start() {
  last_time_ = std::chrono::steady_clock::now();
}

void AdaptiveTimer::wait() {
  const auto now = std::chrono::steady_clock::now();
  const auto elapsed = std::chrono::duration<double, std::milli>(now - last_time_).count();
  max_observed_cycle_ms_ = std::max(max_observed_cycle_ms_, elapsed);
  if (elapsed > current_period_ms_) {
    overrun_count_ += 1;
  } else {
    std::this_thread::sleep_for(std::chrono::duration<double, std::milli>(current_period_ms_ - elapsed));
  }
  last_time_ = std::chrono::steady_clock::now();
}

double AdaptiveTimer::getCpuUsage() {
  return target_cpu_;
}

void AdaptiveTimer::adjustPeriod(double cpu_usage) {
  if (cpu_usage > target_cpu_) {
    current_period_ms_ = std::min(max_period_ms_, current_period_ms_ + 0.1);
  } else {
    current_period_ms_ = std::max(min_period_ms_, current_period_ms_ - 0.05);
  }
}

RtMotionService::RtMotionService(std::shared_ptr<rokae::xMateRobot> robot, SdkRobotFacade* sdk)
    : robot_(std::move(robot)),
      sdk_(sdk),
      impedance_manager_(std::make_unique<robot_core::ImpedanceControlManager>()),
      adaptive_timer_(std::make_unique<AdaptiveTimer>(1.0, 1.0, 70.0)) {
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.nominal_loop_hz = 1000;
  snapshot_.fixed_period_enforced = true;
  snapshot_.jitter_monitor_enabled = true;
  snapshot_.jitter_budget_ms = 0.2;
  snapshot_.contact_control_mode = "normal_axis_admittance";
}

RtMotionService::~RtMotionService() = default;

void RtMotionService::bindSdkFacade(SdkRobotFacade* sdk) {
  sdk_ = sdk;
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  syncSnapshotTelemetry();
}

bool RtMotionService::startCartesianImpedance() {
  return startScanFollowRt();
}

bool RtMotionService::startSeekContactRt() {
  std::string reason;
  return startRtPhase("seek_contact", &reason);
}

bool RtMotionService::startScanFollowRt() {
  std::string reason;
  return startRtPhase("scan_follow", &reason);
}

bool RtMotionService::startPauseHoldRt() {
  std::string reason;
  return startRtPhase("pause_hold", &reason);
}

bool RtMotionService::startControlledRetractRt() {
  std::string reason;
  return startRtPhase("controlled_retract", &reason);
}

bool RtMotionService::transitionToRtPhase(const std::string& phase_name, std::string* reason) {
  if (sdk_ == nullptr) {
    if (reason != nullptr) *reason = "no_sdk_facade";
    updateSnapshot("blocked", "transition:" + phase_name + ":no_sdk_facade");
    return false;
  }
  snapshot_.pause_hold = (phase_name == "pause_hold");
  updateSnapshot(phase_name, "transition:" + phase_name);
  return true;
}

double RtMotionService::desiredForceForPhase(const std::string& phase) const {
  if (phase == "seek_contact" || phase == "scan_follow") {
    return impedance_manager_->getCircuitBreaker().getLimits().desired_contact_force_n;
  }
  return 0.0;
}

bool RtMotionService::startRtPhase(const std::string& phase_name, std::string* reason) {
  if (!transitionToRtPhase(phase_name, reason)) {
    return false;
  }
  const auto desired_force_n = desiredForceForPhase(phase_name);
  sdk_->rtControlPort().resetPhaseIntegrators();
  if (!sdk_->rtControlPort().beginMainline(phase_name, snapshot_.nominal_loop_hz, reason)) {
    updateSnapshot("blocked", "start_rt_phase:" + phase_name + ":preconditions_failed");
    return false;
  }
  impedance_manager_->setDesiredContactForce(desired_force_n);
  impedance_manager_->activateImpedance();
  is_running_.store(true);
  snapshot_.desired_contact_force_n = desired_force_n;
  updateSnapshot(phase_name, "start_rt_phase:" + phase_name);
  return true;
}

bool RtMotionService::completeRtPhase(const std::string& phase_name, std::string* reason) {
  if (reason != nullptr) {
    *reason = "phase_completed:" + phase_name;
  }
  is_running_.store(false);
  impedance_manager_->deactivateImpedance();
  snapshot_.pause_hold = false;
  snapshot_.desired_contact_force_n = 0.0;
  if (sdk_ != nullptr) {
    std::string stop_reason;
    sdk_->rtControlPort().stop(&stop_reason);
  }
  updateSnapshot("idle", "complete_rt_phase:" + phase_name);
  return true;
}

bool RtMotionService::faultRtPhase(const std::string& phase_name, const std::string& reason) {
  const auto decision = reason.empty() ? std::string("fault") : reason;
  snapshot_.last_sensor_decision = decision;
  stopRtLoop();
  updateSnapshot("blocked", "fault_rt_phase:" + phase_name + ":" + decision);
  snapshot_.last_sensor_decision = decision;
  return false;
}

void RtMotionService::stopRtLoop() {
  is_running_.store(false);
  impedance_manager_->deactivateImpedance();
  snapshot_.pause_hold = false;
  if (sdk_ != nullptr) {
    std::string reason;
    sdk_->rtControlPort().stop(&reason);
  }
  updateSnapshot("idle", "stop_rt_loop");
}

void RtMotionService::stop() {
  stopRtLoop();
}

RtControlledRetractResult RtMotionService::controlledRetract() {
  RtControlledRetractResult result{};
  if (sdk_ == nullptr) {
    result.status = RtControlledRetractStatus::StartRejected;
    result.reason = "no_sdk_facade";
    faultRtPhase("controlled_retract", result.reason);
    return result;
  }

  std::string start_reason;
  if (!startRtPhase("controlled_retract", &start_reason)) {
    result.status = RtControlledRetractStatus::StartRejected;
    result.reason = start_reason.empty() ? "start_failed" : start_reason;
    faultRtPhase("controlled_retract", result.reason);
    return result;
  }
  result.phase_started = true;

  const auto config = sdk_->rtControlPort().runtimeConfig();
  const auto retreat_speed = std::max(1.0, config.retreat_speed_mm_s);
  const double wait_seconds = std::clamp(config.retract_timeout_ms / 1000.0,
                                         config.retract_travel_mm / retreat_speed + 0.15,
                                         3.0);

  const auto deadline = std::chrono::steady_clock::now() + std::chrono::duration<double>(wait_seconds);
  while (std::chrono::steady_clock::now() < deadline) {
    if (sdk_->rtControlPort().activeRtPhase() == "idle") {
      result.phase_completed = true;
      break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(10));
  }

  if (result.phase_completed) {
    std::string complete_reason;
    completeRtPhase("controlled_retract", &complete_reason);
    result.status = RtControlledRetractStatus::Completed;
    result.reason = complete_reason.empty() ? "phase_completed:controlled_retract" : complete_reason;
    return result;
  }

  result.status = RtControlledRetractStatus::TimedOut;
  result.reason = "timeout_waiting_phase_completion";
  faultRtPhase("controlled_retract", result.reason);
  return result;
}

SensorHealthDecision RtMotionService::evaluateSensorFreshnessMs(double age_ms) const {
  const auto& limits = impedance_manager_->getCircuitBreaker().getLimits();
  if (age_ms > limits.sensor_timeout_ms * 2.0) return SensorHealthDecision::Estop;
  if (age_ms > limits.sensor_timeout_ms) return SensorHealthDecision::ControlledRetract;
  if (age_ms > limits.stale_telemetry_ms) return SensorHealthDecision::Hold;
  return SensorHealthDecision::None;
}

bool RtMotionService::seekContact() {
  return startSeekContactRt();
}

void RtMotionService::pauseAndHold() {
  startPauseHoldRt();
}

void RtMotionService::recordLoopSample(double scheduled_period_ms, double execution_ms, double wake_jitter_ms, bool overrun) {
  snapshot_.current_period_ms = scheduled_period_ms > 0.0 ? scheduled_period_ms : snapshot_.current_period_ms;
  snapshot_.max_cycle_ms = std::max(snapshot_.max_cycle_ms, execution_ms);
  snapshot_.last_wake_jitter_ms = wake_jitter_ms;
  if (overrun) snapshot_.overrun_count += 1;
}

RtLoopContractSnapshot RtMotionService::snapshot() const {
  return snapshot_;
}

void RtMotionService::updateSnapshot(const std::string& phase, const std::string& event) {
  snapshot_.loop_active = is_running_.load();
  snapshot_.move_active = is_running_.load();
  snapshot_.phase = phase;
  snapshot_.phase_group = phaseGroupFor(phase);
  snapshot_.last_event = event;
  snapshot_.control_mode = "cartesianImpedance";
  snapshot_.degraded_without_sdk = (sdk_ == nullptr) || !sdk_->rtControlPort().liveBindingEstablished();
  snapshot_.last_sensor_decision = "none";
  syncSnapshotTelemetry();
  if (sdk_ != nullptr) {
    sdk_->rtControlPort().updatePhase(phase, event);
  }
}

void RtMotionService::syncSnapshotTelemetry() {
  snapshot_.current_period_ms = adaptive_timer_->getCurrentPeriodMs();
  snapshot_.max_cycle_ms = std::max(snapshot_.max_cycle_ms, adaptive_timer_->getMaxObservedCycleMs());
  snapshot_.overrun_count = std::max(snapshot_.overrun_count, adaptive_timer_->getOverrunCount());
  if (sdk_ != nullptr) {
    snapshot_.network_healthy = sdk_->rtControlPort().networkHealthy();
    snapshot_.nominal_loop_hz = std::max(1, sdk_->rtControlPort().nominalRtLoopHz());
    const auto phase = sdk_->rtControlPort().phaseTelemetry();
    snapshot_.estimated_normal_force_n = phase.estimated_normal_force_n;
    snapshot_.normal_force_confidence = phase.normal_force_confidence;
    snapshot_.normal_force_source = phase.normal_force_source;
    snapshot_.admittance_displacement_mm = phase.admittance_displacement_m * 1000.0;
    snapshot_.admittance_velocity_mm_s = phase.admittance_velocity_m_s * 1000.0;
    snapshot_.admittance_saturated = phase.admittance_saturated;
    snapshot_.orientation_trim_deg = phase.pose_trim_rad * 180.0 / M_PI;
    snapshot_.orientation_trim_saturated = phase.orientation_trim_saturated;
  }
}

std::string RtMotionService::phaseGroupFor(const std::string& phase) const {
  if (phase == "seek_contact" || phase == "contact_hold") return "contact";
  if (phase == "scan_follow" || phase == "pause_hold") return "scan";
  if (phase == "controlled_retract") return "recovery";
  if (phase == "blocked") return "guard";
  return "idle";
}

}  // namespace robot_core
