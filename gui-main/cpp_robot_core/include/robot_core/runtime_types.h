#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace robot_core {

enum class RobotCoreState {
  Boot,
  Disconnected,
  Connected,
  Powered,
  AutoReady,
  SessionLocked,
  PathValidated,
  Approaching,
  ContactSeeking,
  Scanning,
  PausedHold,
  Retreating,
  ScanComplete,
  Fault,
  Estop,
};

struct RuntimeConfig {
  double pressure_target{1.5};
  double pressure_upper{2.0};
  double pressure_lower{1.0};
  double scan_speed_mm_s{8.0};
  double sample_step_mm{0.5};
  double segment_length_mm{120.0};
  double contact_seek_speed_mm_s{3.0};
  double retreat_speed_mm_s{20.0};
  std::string rt_mode{"cartesianImpedance"};
  int network_stale_ms{150};
  int pressure_stale_ms{100};
  int telemetry_rate_hz{20};
  std::string tool_name{"ultrasound_probe"};
  std::string tcp_name{"ultrasound_tcp"};
  double load_kg{0.85};
};

struct ScanWaypoint {
  double x{0.0};
  double y{0.0};
  double z{0.0};
  double rx{0.0};
  double ry{0.0};
  double rz{0.0};
};

struct ScanSegment {
  int segment_id{0};
  std::vector<ScanWaypoint> waypoints;
  double target_pressure{1.5};
  std::string scan_direction{"caudal_to_cranial"};
  bool needs_resample{false};
};

struct ScanPlan {
  std::string session_id;
  std::string plan_id;
  ScanWaypoint approach_pose;
  ScanWaypoint retreat_pose;
  std::vector<ScanSegment> segments;
};

struct CoreStateSnapshot {
  RobotCoreState execution_state{RobotCoreState::Boot};
  bool armed{false};
  std::string fault_code;
  int active_segment{0};
  double progress_pct{0.0};
  std::string session_id;
  std::string recovery_state;
};

struct DeviceHealth {
  std::string device_name;
  bool online{false};
  bool fresh{false};
  int64_t last_ts_ns{0};
  std::string detail;
};

struct SafetyStatus {
  bool safe_to_arm{false};
  bool safe_to_scan{false};
  std::vector<std::string> active_interlocks;
};

struct RecorderStatus {
  std::string session_id;
  bool recording{false};
  int dropped_samples{0};
  int64_t last_flush_ns{0};
};

struct RobotStateSnapshot {
  int64_t timestamp_ns{};
  std::string power_state{"off"};
  std::string operate_mode{"manual"};
  std::string operation_state{"idle"};
  std::vector<double> joint_pos;
  std::vector<double> joint_vel;
  std::vector<double> joint_torque;
  std::vector<double> tcp_pose;
  std::vector<double> cart_force;
  std::string last_event{"-"};
  std::string last_controller_log{"-"};
};

struct ContactTelemetry {
  std::string mode{"NO_CONTACT"};
  double confidence{0.0};
  double pressure_current{0.0};
  std::string recommended_action{"IDLE"};
};

struct ScanProgress {
  int active_segment{0};
  int path_index{0};
  double overall_progress{0.0};
  int frame_id{0};
};

struct QualityFeedback {
  double image_quality{0.0};
  double feature_confidence{0.0};
  double quality_score{0.0};
  bool need_resample{false};
};

struct AlarmEvent {
  std::string severity{"INFO"};
  std::string source{"robot_core"};
  std::string message;
  std::string session_id;
  int segment_id{0};
  int64_t event_ts_ns{0};
  std::string workflow_step;
  std::string request_id;
  std::string auto_action;
};

struct TelemetrySnapshot {
  CoreStateSnapshot core_state;
  RobotStateSnapshot robot_state;
  ContactTelemetry contact_state;
  ScanProgress scan_progress;
  std::vector<DeviceHealth> devices;
  SafetyStatus safety_status;
  RecorderStatus recorder_status;
  QualityFeedback quality_feedback;
  std::vector<AlarmEvent> alarms;
};

}  // namespace robot_core
