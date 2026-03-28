#pragma once

#include <mutex>
#include <string>
#include <vector>

#include "robot_core/contact_observer.h"
#include "robot_core/nrt_motion_service.h"
#include "robot_core/recording_service.h"
#include "robot_core/recovery_manager.h"
#include "robot_core/robot_state_hub.h"
#include "robot_core/rt_motion_service.h"
#include "robot_core/runtime_types.h"
#include "robot_core/safety_service.h"

namespace robot_core {

class CoreRuntime {
public:
  CoreRuntime();

  std::string handleCommandJson(const std::string& line);
  TelemetrySnapshot takeTelemetrySnapshot();
  void rtStep();
  void statePollStep();
  void watchdogStep();
  void setState(RobotCoreState state);
  RobotCoreState state() const;

private:
  void updateKinematicsLocked();
  void updateQualityLocked();
  void updateContactAndProgressLocked();
  void refreshDeviceHealthLocked(int64_t ts_ns);
  SafetyStatus evaluateSafetyLocked() const;
  void queueAlarmLocked(const std::string& severity, const std::string& source, const std::string& message);
  CoreStateSnapshot buildCoreSnapshotLocked() const;
  ScanProgress buildScanProgressLocked() const;
  void recordStreamsLocked();
  void applyConfigFromJsonLocked(const std::string& json_line);
  void loadPlanFromJsonLocked(const std::string& json_line);
  std::string replyJson(const std::string& request_id, bool ok, const std::string& message, const std::string& data_json = "{}") const;

  mutable std::mutex mutex_;
  RuntimeConfig config_{};
  RobotCoreState execution_state_{RobotCoreState::Disconnected};
  bool controller_online_{false};
  bool powered_{false};
  bool automatic_mode_{false};
  bool tool_ready_{false};
  bool tcp_ready_{false};
  bool load_ready_{false};
  bool pressure_fresh_{false};
  bool robot_state_fresh_{false};
  bool rt_jitter_ok_{true};
  std::string fault_code_;
  std::string session_id_;
  std::string session_dir_;
  std::string plan_id_;
  bool plan_loaded_{false};
  int total_points_{0};
  int total_segments_{0};
  int path_index_{0};
  int frame_id_{0};
  int active_segment_{0};
  int retreat_ticks_remaining_{0};
  double progress_pct_{0.0};
  double phase_{0.0};
  double pressure_current_{0.0};
  double image_quality_{0.82};
  double feature_confidence_{0.76};
  double quality_score_{0.79};
  ContactTelemetry contact_state_{};
  std::vector<DeviceHealth> devices_{};
  std::vector<AlarmEvent> pending_alarms_{};
  RobotStateHub robot_state_hub_{};
  RecordingService recording_service_{};
  SafetyService safety_service_{};
  ContactObserver contact_observer_{};
  NrtMotionService nrt_motion_service_{};
  RtMotionService rt_motion_service_{};
  RecoveryManager recovery_manager_{};
};

}  // namespace robot_core
