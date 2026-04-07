#pragma once

#include <array>
#include <atomic>
#include <chrono>
#include <memory>
#include <string>

#include "../../include/ipc_messages.hpp"
#include "../../include/impedance_control_manager.hpp"
#include "../../include/spsc_queue.hpp"

namespace rokae {
class xMateRobot;
}

namespace robot_core {

class SdkRobotFacade;

enum class SensorHealthDecision {
  None,
  Hold,
  ControlledRetract,
  Estop,
};

struct RtLoopContractSnapshot {
  bool loop_active{false};
  bool move_active{false};
  bool pause_hold{false};
  bool degraded_without_sdk{true};
  bool reference_limiter_enabled{true};
  bool freshness_guard_enabled{true};
  bool jitter_monitor_enabled{true};
  bool contact_band_monitor_enabled{true};
  bool network_guard_enabled{true};
  bool fixed_period_enforced{true};
  bool network_healthy{true};
  int nominal_loop_hz{1000};
  int overrun_count{0};
  std::string control_mode{"cartesianImpedance"};
  std::string phase{"idle"};
  std::string phase_group{"idle"};
  std::string last_event{"boot"};
  std::string last_sensor_decision{"none"};
  double desired_contact_force_n{0.0};
  double estimated_normal_force_n{0.0};
  double normal_force_confidence{0.0};
  std::string normal_force_source{"invalid"};
  double admittance_displacement_mm{0.0};
  double admittance_velocity_mm_s{0.0};
  bool admittance_saturated{false};
  double orientation_trim_deg{0.0};
  bool orientation_trim_saturated{false};
  std::string contact_control_mode{"normal_axis_admittance"};
  double current_period_ms{1.0};
  double max_cycle_ms{0.0};
  double last_wake_jitter_ms{0.0};
  double jitter_budget_ms{0.2};
};

class AdaptiveTimer {
public:
  AdaptiveTimer(double min_period_ms = 1.0, double max_period_ms = 1.0, double target_cpu = 70.0);
  ~AdaptiveTimer() = default;

  void start();
  void wait();
  double getCurrentPeriodMs() const { return current_period_ms_; }
  double getMaxObservedCycleMs() const { return max_observed_cycle_ms_; }
  int getOverrunCount() const { return overrun_count_; }
  void adjustPeriod(double cpu_usage);

private:
  double min_period_ms_;
  double max_period_ms_;
  double target_cpu_;
  double current_period_ms_;
  double max_observed_cycle_ms_{0.0};
  int overrun_count_{0};
  std::chrono::steady_clock::time_point last_time_;
  double getCpuUsage();
};

class RtMotionService {
public:
  explicit RtMotionService(std::shared_ptr<rokae::xMateRobot> robot = nullptr, SdkRobotFacade* sdk = nullptr);
  ~RtMotionService();

  spine_core::SPSCQueue<spine_core_pod::CommandPose> cmd_queue{100};
  spine_core::SPSCQueue<spine_core_pod::RobotTelemetry> telemetry_queue{100};

  void bindSdkFacade(SdkRobotFacade* sdk);
  bool startCartesianImpedance();
  bool startSeekContactRt();
  bool startScanFollowRt();
  bool startPauseHoldRt();
  bool startControlledRetractRt();
  bool transitionToRtPhase(const std::string& phase_name, std::string* reason = nullptr);
  bool startRtPhase(const std::string& phase_name, std::string* reason = nullptr);
  bool completeRtPhase(const std::string& phase_name, std::string* reason = nullptr);
  bool faultRtPhase(const std::string& phase_name, const std::string& reason);
  void stopRtLoop();
  void stop();
  void controlledRetract();
  SensorHealthDecision evaluateSensorFreshnessMs(double age_ms) const;
  bool seekContact();
  void pauseAndHold();

  /**
   * @brief Record one RT timing sample.
   * @param scheduled_period_ms Target control period in milliseconds.
   * @param execution_ms Observed control callback execution duration.
   * @param wake_jitter_ms Wake-up jitter in milliseconds.
   * @param overrun True when the loop missed its deadline.
   * @throws No exceptions are thrown.
   * @boundary Only timing-derived telemetry is updated.
   */
  void recordLoopSample(double scheduled_period_ms, double execution_ms, double wake_jitter_ms, bool overrun);
  RtLoopContractSnapshot snapshot() const;

private:
  void updateSnapshot(const std::string& phase, const std::string& event);
  void syncSnapshotTelemetry();
  std::string phaseGroupFor(const std::string& phase) const;
  double desiredForceForPhase(const std::string& phase) const;

  std::shared_ptr<rokae::xMateRobot> robot_;
  SdkRobotFacade* sdk_{nullptr};
  std::unique_ptr<robot_core::ImpedanceControlManager> impedance_manager_;
  std::atomic<bool> is_running_{false};
  spine_core_pod::CommandPose current_target_{};
  std::unique_ptr<AdaptiveTimer> adaptive_timer_;
  RtLoopContractSnapshot snapshot_{};
};

}  // namespace robot_core
