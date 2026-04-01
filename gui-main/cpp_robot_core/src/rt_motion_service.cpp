#include "robot_core/rt_motion_service.h"

#include <array>
#include <cstring>
#include <fstream>
#include <sstream>
#include <thread>

#include "robot_core/sdk_robot_facade.h"

namespace rokae {
struct CartesianPosition { std::array<double, 16> pos; };
enum CoordinateType { endInRef };
enum FrameType { path };
enum RtControllerMode { cartesianImpedance };
enum RtSupportedFields { tcpPose_m, tau_m };
}  // namespace rokae

namespace robot_core {

namespace {
constexpr double kDefaultCartesianStiffnessTranslation = 1500.0;
constexpr double kDefaultCartesianStiffnessRotation = 100.0;
constexpr double kDefaultCartesianDampingTranslation = 50.0;
constexpr double kDefaultCartesianDampingRotation = 20.0;

std::string sensorDecisionName(SensorHealthDecision decision) {
  switch (decision) {
    case SensorHealthDecision::None: return "none";
    case SensorHealthDecision::Hold: return "hold";
    case SensorHealthDecision::ControlledRetract: return "controlled_retract";
    case SensorHealthDecision::Estop: return "estop";
  }
  return "none";
}

int64_t get_current_time_ns() {
  const auto now = std::chrono::steady_clock::now();
  return std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count();
}
}  // namespace

AdaptiveTimer::AdaptiveTimer(double min_period_ms, double max_period_ms, double target_cpu)
    : min_period_ms_(min_period_ms),
      max_period_ms_(max_period_ms),
      target_cpu_(target_cpu),
      current_period_ms_(std::clamp(1.0, min_period_ms, max_period_ms)) {}

void AdaptiveTimer::start() {
  last_time_ = std::chrono::steady_clock::now();
  max_observed_cycle_ms_ = 0.0;
  overrun_count_ = 0;
}

void AdaptiveTimer::wait() {
  const auto now = std::chrono::steady_clock::now();
  const auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(now - last_time_).count();
  const double elapsed_ms = static_cast<double>(elapsed) / 1000.0;
  max_observed_cycle_ms_ = std::max(max_observed_cycle_ms_, elapsed_ms);
  if (elapsed_ms > current_period_ms_ + 0.05) {
    ++overrun_count_;
  }
  if (elapsed_ms < current_period_ms_) {
    std::this_thread::sleep_for(std::chrono::microseconds(static_cast<long>((current_period_ms_ - elapsed_ms) * 1000.0)));
  }
  last_time_ = std::chrono::steady_clock::now();
}

void AdaptiveTimer::adjustPeriod(double cpu_usage) {
  (void)cpu_usage;
  current_period_ms_ = std::clamp(current_period_ms_, min_period_ms_, max_period_ms_);
}

double AdaptiveTimer::getCpuUsage() {
  std::ifstream file("/proc/stat");
  std::string line;
  if (std::getline(file, line)) {
    std::istringstream iss(line);
    std::string cpu;
    long user = 0;
    long nice = 0;
    long system = 0;
    long idle = 0;
    long iowait = 0;
    long irq = 0;
    long softirq = 0;
    iss >> cpu >> user >> nice >> system >> idle >> iowait >> irq >> softirq;
    const long total = user + nice + system + idle + iowait + irq + softirq;
    static long prev_total = 0;
    static long prev_idle = 0;
    const long total_diff = total - prev_total;
    const long idle_diff = idle - prev_idle;
    prev_total = total;
    prev_idle = idle;
    if (total_diff > 0) {
      return 100.0 * (1.0 - static_cast<double>(idle_diff) / static_cast<double>(total_diff));
    }
  }
  return 0.0;
}

RtMotionService::RtMotionService(std::shared_ptr<rokae::xMateErProRobot> robot, SdkRobotFacade* sdk)
    : robot_(std::move(robot)),
      sdk_(sdk),
      cmd_queue(100),
      telemetry_queue(100),
      adaptive_timer_(std::make_unique<AdaptiveTimer>(1.0, 1.0, 70.0)),
      impedance_manager_(std::make_unique<ImpedanceControlManager>()) {
  std::memset(current_target_.tcp_pose_td, 0, sizeof(current_target_.tcp_pose_td));
  current_target_.tcp_pose_td[0] = 1.0;
  current_target_.tcp_pose_td[5] = 1.0;
  current_target_.tcp_pose_td[10] = 1.0;
  current_target_.tcp_pose_td[15] = 1.0;
  current_target_.timestamp_ns = get_current_time_ns();
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.desired_contact_force_n = impedance_manager_->getCircuitBreaker().getLimits().desired_contact_force_n;
  snapshot_.reference_limiter_enabled = true;
  snapshot_.freshness_guard_enabled = true;
  snapshot_.jitter_monitor_enabled = true;
  snapshot_.contact_band_monitor_enabled = true;
  snapshot_.network_guard_enabled = true;
  snapshot_.fixed_period_enforced = true;
  snapshot_.network_healthy = true;
  snapshot_.nominal_loop_hz = 1000;
  snapshot_.jitter_budget_ms = 0.2;
}


RtMotionService::~RtMotionService() {
  stop();
}

void RtMotionService::bindSdkFacade(SdkRobotFacade* sdk) {
  sdk_ = sdk;
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  syncSnapshotTelemetry();
}

bool RtMotionService::startCartesianImpedance() {
  if (sdk_ != nullptr) {
    std::string reason;
    if (!sdk_->beginRtMainline("scan_follow", snapshot_.nominal_loop_hz, &reason)) {
      updateSnapshot("blocked", std::string("rt_preconditions_missing:") + reason);
      return false;
    }
  }

  is_running_ = true;
  adaptive_timer_->start();

  CartesianImpedanceParams params;
  params.stiffness = {kDefaultCartesianStiffnessTranslation, kDefaultCartesianStiffnessTranslation,
                      std::min(kDefaultCartesianStiffnessTranslation, snapshot_.desired_contact_force_n * 10.0 + 20.0),
                      kDefaultCartesianStiffnessRotation, kDefaultCartesianStiffnessRotation, kDefaultCartesianStiffnessRotation};
  params.damping = {kDefaultCartesianDampingTranslation, kDefaultCartesianDampingTranslation, 10.0,
                    kDefaultCartesianDampingRotation, kDefaultCartesianDampingRotation, kDefaultCartesianDampingRotation};
  if (sdk_ != nullptr) {
    const auto config = sdk_->runtimeConfig();
    params.stiffness = config.cartesian_impedance;
    params.damping = {50.0, 50.0, 10.0, 20.0, 20.0, 20.0};
    snapshot_.desired_contact_force_n = std::abs(config.desired_wrench_n[2]);
    impedance_manager_->setDesiredWrench(config.desired_wrench_n);
    snapshot_.network_healthy = sdk_->networkHealthy();
    snapshot_.nominal_loop_hz = std::max(1, sdk_->nominalRtLoopHz());
  }
  if (!impedance_manager_->configureImpedance(params)) {
    is_running_ = false;
    if (sdk_ != nullptr) {
      sdk_->finishRtMainline("scan_follow", "impedance_config_failed");
    }
    updateSnapshot("fault", "impedance_config_failed");
    return false;
  }

  if (sdk_ == nullptr) {
    const auto& force_limits = impedance_manager_->getCircuitBreaker().getLimits();
    snapshot_.desired_contact_force_n = force_limits.desired_contact_force_n;
    impedance_manager_->setDesiredWrench({0.0, 0.0, -std::abs(force_limits.desired_contact_force_n), 0.0, 0.0, 0.0});
  }
  impedance_manager_->activateImpedance();
  updateSnapshot("scan_follow", "start_cartesian_impedance");
  return true;
}

void RtMotionService::controlledRetract() {
  is_running_ = false;
  impedance_manager_->setDesiredWrench({0.0, 0.0, 0.0, 0.0, 0.0, 0.0});
  impedance_manager_->deactivateImpedance();
  snapshot_.pause_hold = false;
  if (sdk_ != nullptr) {
    sdk_->updateRtPhase("controlled_retract", "controlled_retract");
    sdk_->finishRtMainline("controlled_retract", "controlled_retract_completed");
  }
  updateSnapshot("controlled_retract", "controlled_retract");
}

SensorHealthDecision RtMotionService::evaluateSensorFreshnessMs(double age_ms) const {
  const auto& limits = impedance_manager_->getCircuitBreaker().getLimits();
  if (age_ms > limits.sensor_timeout_ms * 2.0) {
    return SensorHealthDecision::Estop;
  }
  if (age_ms > limits.sensor_timeout_ms) {
    return SensorHealthDecision::ControlledRetract;
  }
  if (age_ms > limits.stale_telemetry_ms) {
    return SensorHealthDecision::Hold;
  }
  return SensorHealthDecision::None;
}

void RtMotionService::stop() {
  is_running_ = false;
  impedance_manager_->deactivateImpedance();
  snapshot_.pause_hold = false;
  if (sdk_ != nullptr) {
    sdk_->finishRtMainline(snapshot_.phase, "stop");
  }
  updateSnapshot("idle", "stop");
}

bool RtMotionService::seekContact() {
  if (sdk_ != nullptr) {
    std::string reason;
    if (!sdk_->beginRtMainline("seek_contact", snapshot_.nominal_loop_hz, &reason)) {
      updateSnapshot("blocked", std::string("seek_contact_preconditions_missing:") + reason);
      return false;
    }
    snapshot_.network_healthy = sdk_->networkHealthy();
  }
  impedance_manager_->setDesiredContactForce(impedance_manager_->getCircuitBreaker().getLimits().desired_contact_force_n);
  impedance_manager_->activateImpedance();
  updateSnapshot("seek_contact", "seek_contact");
  return true;
}

void RtMotionService::pauseAndHold() {
  impedance_manager_->setDesiredContactForce(0.0);
  impedance_manager_->activateImpedance();
  snapshot_.pause_hold = true;
  if (sdk_ != nullptr) {
    sdk_->updateRtPhase("pause_hold", "pause_and_hold");
  }
  updateSnapshot("pause_hold", "pause_and_hold");
}

void RtMotionService::recordLoopSample(double scheduled_period_ms, double execution_ms, double wake_jitter_ms, bool overrun) {
  snapshot_.current_period_ms = scheduled_period_ms > 0.0 ? scheduled_period_ms : snapshot_.current_period_ms;
  snapshot_.max_cycle_ms = std::max(snapshot_.max_cycle_ms, execution_ms);
  snapshot_.last_wake_jitter_ms = wake_jitter_ms;
  if (overrun) {
    snapshot_.overrun_count += 1;
  }
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
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.last_sensor_decision = sensorDecisionName(evaluateSensorFreshnessMs(0.0));
  syncSnapshotTelemetry();
  if (sdk_ != nullptr) {
    sdk_->updateRtPhase(phase, event);
  }
}

void RtMotionService::syncSnapshotTelemetry() {
  const double adaptive_period_ms = adaptive_timer_->getCurrentPeriodMs();
  const double adaptive_max_cycle_ms = adaptive_timer_->getMaxObservedCycleMs();
  if (snapshot_.current_period_ms <= 0.0) {
    snapshot_.current_period_ms = adaptive_period_ms;
  }
  snapshot_.max_cycle_ms = std::max(snapshot_.max_cycle_ms, adaptive_max_cycle_ms);
  snapshot_.overrun_count = std::max(snapshot_.overrun_count, adaptive_timer_->getOverrunCount());
  if (sdk_ != nullptr) {
    snapshot_.network_healthy = sdk_->networkHealthy();
    snapshot_.nominal_loop_hz = std::max(1, sdk_->nominalRtLoopHz());
  }
}

std::string RtMotionService::phaseGroupFor(const std::string& phase) const {
  if (phase == "seek_contact" || phase == "contact_hold") {
    return "contact";
  }
  if (phase == "scan_follow" || phase == "pause_hold") {
    return "scan";
  }
  if (phase == "controlled_retract") {
    return "recovery";
  }
  if (phase == "blocked") {
    return "guard";
  }
  return "idle";
}

}  // namespace robot_core
