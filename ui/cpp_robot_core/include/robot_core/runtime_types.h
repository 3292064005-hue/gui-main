#pragma once

#include <cstdint>
#include <map>
#include <string>
#include <vector>

#include "robot_core/generated_runtime_config_field_decls.inc"

#ifndef ROBOT_CORE_MAINLINE_FAMILY_KEY
#define ROBOT_CORE_MAINLINE_FAMILY_KEY "xmate3_cobot_6"
#endif
#ifndef ROBOT_CORE_DEFAULT_ROBOT_MODEL
#define ROBOT_CORE_DEFAULT_ROBOT_MODEL "xmate3"
#endif
#ifndef ROBOT_CORE_DEFAULT_SDK_CLASS
#define ROBOT_CORE_DEFAULT_SDK_CLASS "xMateRobot"
#endif
#ifndef ROBOT_CORE_DEFAULT_AXIS_COUNT
#define ROBOT_CORE_DEFAULT_AXIS_COUNT 6
#endif
#ifndef ROBOT_CORE_DEFAULT_PREFERRED_LINK
#define ROBOT_CORE_DEFAULT_PREFERRED_LINK "wired_direct"
#endif
#ifndef ROBOT_CORE_DEFAULT_CLINICAL_MAINLINE_MODE
#define ROBOT_CORE_DEFAULT_CLINICAL_MAINLINE_MODE "cartesianImpedance"
#endif

namespace robot_core {

struct ContactControlConfig {
  ROBOT_CORE_CONTACT_CONTROL_CONFIG_FIELDS
};

struct ForceEstimatorRuntimeConfig {
  ROBOT_CORE_FORCE_ESTIMATOR_CONFIG_FIELDS
};

struct OrientationTrimRuntimeConfig {
  ROBOT_CORE_ORIENTATION_TRIM_CONFIG_FIELDS
};


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
  ContactStable,
  Scanning,
  PausedHold,
  RecoveryRetract,
  SegmentAborted,
  PlanAborted,
  Retreating,
  ScanComplete,
  Fault,
  Estop,
};

struct RuntimeConfig {
  ROBOT_CORE_RUNTIME_CONFIG_FIELDS
};

struct ScanWaypoint {
  double x{0.0};
  double y{0.0};
  double z{0.0};
  double rx{0.0};
  double ry{0.0};
  double rz{0.0};
  int sequence_index{0};
  int dwell_ms{0};
  bool probe_required{false};
  std::string checkpoint_tag;
  std::string transition_hint;
};

struct ExecutionConstraints {
  int max_segment_duration_ms{0};
  std::map<std::string, double> allowed_contact_band;
  std::string transition_smoothing{"standard"};
  std::string recovery_checkpoint_policy{"segment_boundary"};
  double probe_spacing_mm{0.0};
  double probe_depth_mm{0.0};
};

struct ScanSegment {
  int segment_id{0};
  std::vector<ScanWaypoint> waypoints;
  double target_pressure{1.5};
  std::string scan_direction{"caudal_to_cranial"};
  bool needs_resample{false};
  int estimated_duration_ms{0};
  bool requires_contact_probe{false};
  int segment_priority{0};
  int rescan_origin_segment{0};
  double quality_target{0.0};
  double coverage_target{0.0};
  std::string segment_hash;
  std::map<std::string, double> contact_band;
  std::string transition_policy{"serpentine"};
};

struct ScanPlan {
  std::string session_id;
  std::string plan_id;
  ScanWaypoint approach_pose;
  ScanWaypoint retreat_pose;
  std::vector<ScanSegment> segments;
  std::string planner_version;
  std::string registration_hash;
  std::string plan_kind{"preview"};
  std::string plan_hash;
  std::string validation_summary;
  std::string score_summary;
  std::string surface_model_hash;
  ExecutionConstraints execution_constraints;
  int64_t created_ts_ns{0};
};

struct ExecutionSegmentRuntime {
  ScanSegment segment;
  std::vector<double> cumulative_lengths_m;
  double total_length_m{0.0};
};

struct ExecutionPlanRuntime {
  std::string session_id;
  std::string plan_id;
  std::string plan_hash;
  ScanWaypoint approach_pose;
  ScanWaypoint retreat_pose;
  std::vector<ExecutionSegmentRuntime> segments;
  int total_waypoints{0};
  int active_segment_index{0};
  int active_waypoint_index{0};
  int completed_waypoints{0};
  bool started{false};
  bool finished{false};
  std::string active_checkpoint_tag;
};

struct FinalVerdict {
  bool accepted{false};
  std::string reason;
  std::string evidence_id;
  std::string policy_state{"blocked"};
  std::string source{"cpp_robot_core"};
  std::string next_state{"replan_required"};
  std::string summary_label{"模型前检阻塞"};
  std::string detail;
  std::string plan_id;
  std::string plan_hash;
  bool advisory_only{false};
  std::vector<std::string> warnings;
  std::vector<std::string> blockers;
};

struct CoreStateSnapshot {
  RobotCoreState execution_state{RobotCoreState::Boot};
  bool armed{false};
  std::string fault_code;
  int active_segment{0};
  double progress_pct{0.0};
  std::string session_id;
  std::string recovery_state;
  std::string plan_hash;
  bool contact_stable{false};
  int64_t contact_stable_since_ns{0};
  int active_waypoint_index{0};
  std::string last_transition;
  std::string state_reason;
  std::string resume_token;
};

struct DeviceHealth {
  std::string device_name;
  bool present{false};
  bool connected{false};
  bool streaming{false};
  bool online{false};  // Deprecated compatibility alias kept for older telemetry/UI consumers.
  bool fresh{false};
  bool authoritative{false};
  int64_t last_ts_ns{0};
  std::string detail;
};

struct SafetyStatus {
  bool safe_to_arm{false};
  bool safe_to_scan{false};
  std::vector<std::string> active_interlocks;
  std::string recovery_reason;
  std::string last_recovery_action;
  int sensor_freshness_ms{0};
  std::string pressure_band_state{"UNKNOWN"};
  int force_excursion_count{0};
  int contact_instability_count{0};
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
  std::string runtime_source{"unknown"};
  std::string pose_source{"unavailable"};
  std::string force_source{"unavailable"};
  bool pose_available{false};
  bool force_available{false};
  bool pose_authoritative{false};
  bool force_authoritative{false};
};

struct ContactTelemetry {
  std::string mode{"NO_CONTACT"};
  double confidence{0.0};
  double pressure_current{0.0};
  std::string recommended_action{"IDLE"};
  std::string pressure_source{"unavailable"};
  std::string quality_source{"unavailable"};
  bool pressure_available{false};
  bool quality_available{false};
  bool authoritative{false};
  bool contact_stable{false};
};

struct ScanProgress {
  int active_segment{0};
  int active_waypoint_index{0};
  int completed_waypoints{0};
  int remaining_waypoints{0};
  int total_waypoints{0};
  int path_index{0};
  double overall_progress{0.0};
  int frame_id{0};
  std::string checkpoint_tag;
};

struct QualityFeedback {
  double image_quality{0.0};
  double feature_confidence{0.0};
  double quality_score{0.0};
  bool need_resample{false};
  std::string source{"unavailable"};
  bool available{false};
  bool authoritative{false};
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
