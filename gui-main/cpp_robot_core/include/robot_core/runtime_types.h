#pragma once

#include <cstdint>
#include <map>
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
  double pressure_target{8.0};
  double pressure_upper{12.0};
  double pressure_lower{5.0};
  double scan_speed_mm_s{8.0};
  double sample_step_mm{0.5};
  double segment_length_mm{120.0};
  double strip_width_mm{18.0};
  double strip_overlap_mm{6.0};
  double contact_seek_speed_mm_s{3.0};
  double retreat_speed_mm_s{20.0};
  double image_quality_threshold{0.7};
  double smoothing_factor{0.35};
  double reconstruction_step{0.5};
  double feature_threshold{0.6};
  std::string roi_mode{"auto"};
  std::string rt_mode{"cartesianImpedance"};
  int network_stale_ms{150};
  int pressure_stale_ms{100};
  int telemetry_rate_hz{20};
  std::string tool_name{"ultrasound_probe"};
  std::string tcp_name{"ultrasound_tcp"};
  double load_kg{0.85};
  std::string remote_ip{"192.168.0.160"};
  std::string local_ip{"192.168.0.100"};
  std::string force_sensor_provider{"mock_force_sensor"};
  std::string robot_model{"xmate3"};
  int axis_count{6};
  std::string sdk_robot_class{"xMateRobot"};
  std::string preferred_link{"wired_direct"};
  bool requires_single_control_source{true};
  std::string build_id{"dev"};
  std::string software_version{"0.3.0"};
  int rt_network_tolerance_percent{15};
  double joint_filter_hz{40.0};
  double cart_filter_hz{30.0};
  double torque_filter_hz{25.0};
  bool collision_detection_enabled{true};
  int collision_sensitivity{4};
  std::string collision_behavior{"pause_hold"};
  double collision_fallback_mm{8.0};
  bool soft_limit_enabled{true};
  double joint_soft_limit_margin_deg{5.0};
  bool singularity_avoidance_enabled{true};
  std::string rl_project_name{"spine_mainline"};
  std::string rl_task_name{"scan"};
  std::string xpanel_vout_mode{"off"};
  std::vector<double> cartesian_impedance{1000.0, 1000.0, 1000.0, 80.0, 80.0, 80.0};
  std::vector<double> desired_wrench_n{0.0, 0.0, 8.0, 0.0, 0.0, 0.0};
  std::string fc_frame_type{"path"};
  std::vector<double> fc_frame_matrix{1.0, 0.0, 0.0, 0.0,
                                      0.0, 1.0, 0.0, 0.0,
                                      0.0, 0.0, 1.0, 0.0,
                                      0.0, 0.0, 0.0, 1.0};
  std::vector<double> tcp_frame_matrix{1.0, 0.0, 0.0, 0.0,
                                       0.0, 1.0, 0.0, 0.0,
                                       0.0, 0.0, 1.0, 62.0,
                                       0.0, 0.0, 0.0, 1.0};
  std::vector<double> load_com_mm{0.0, 0.0, 62.0};
  std::vector<double> load_inertia{0.0012, 0.0012, 0.0008, 0.0, 0.0, 0.0};
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
  bool online{false};
  bool fresh{false};
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
