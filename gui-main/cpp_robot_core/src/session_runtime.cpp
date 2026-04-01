#include "robot_core/core_runtime.h"

#include <algorithm>

#include "json_utils.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {


void CoreRuntime::applyConfigFromJsonLocked(const std::string& json_line) {
  const auto config_json = json::extractObject(json_line, "config_snapshot", "{}");
  const auto& source = config_json != "{}" ? config_json : json_line;
  config_.pressure_target = json::extractDouble(source, "pressure_target", config_.pressure_target);
  config_.pressure_upper = json::extractDouble(source, "pressure_upper", config_.pressure_upper);
  config_.pressure_lower = json::extractDouble(source, "pressure_lower", config_.pressure_lower);
  config_.scan_speed_mm_s = json::extractDouble(source, "scan_speed_mm_s", config_.scan_speed_mm_s);
  config_.sample_step_mm = json::extractDouble(source, "sample_step_mm", config_.sample_step_mm);
  config_.segment_length_mm = json::extractDouble(source, "segment_length_mm", config_.segment_length_mm);
  config_.strip_width_mm = json::extractDouble(source, "strip_width_mm", config_.strip_width_mm);
  config_.strip_overlap_mm = json::extractDouble(source, "strip_overlap_mm", config_.strip_overlap_mm);
  config_.contact_seek_speed_mm_s = json::extractDouble(source, "contact_seek_speed_mm_s", config_.contact_seek_speed_mm_s);
  config_.retreat_speed_mm_s = json::extractDouble(source, "retreat_speed_mm_s", config_.retreat_speed_mm_s);
  config_.image_quality_threshold = json::extractDouble(source, "image_quality_threshold", config_.image_quality_threshold);
  config_.smoothing_factor = json::extractDouble(source, "smoothing_factor", config_.smoothing_factor);
  config_.reconstruction_step = json::extractDouble(source, "reconstruction_step", config_.reconstruction_step);
  config_.feature_threshold = json::extractDouble(source, "feature_threshold", config_.feature_threshold);
  config_.roi_mode = json::extractString(source, "roi_mode", config_.roi_mode);
  config_.network_stale_ms = json::extractInt(source, "network_stale_ms", config_.network_stale_ms);
  config_.pressure_stale_ms = json::extractInt(source, "pressure_stale_ms", config_.pressure_stale_ms);
  config_.telemetry_rate_hz = json::extractInt(source, "telemetry_rate_hz", config_.telemetry_rate_hz);
  config_.tool_name = json::extractString(source, "tool_name", config_.tool_name);
  config_.tcp_name = json::extractString(source, "tcp_name", config_.tcp_name);
  config_.load_kg = json::extractDouble(source, "load_kg", config_.load_kg);
  config_.rt_mode = json::extractString(source, "rt_mode", config_.rt_mode);
  config_.remote_ip = json::extractString(source, "remote_ip", config_.remote_ip);
  config_.local_ip = json::extractString(source, "local_ip", config_.local_ip);
  config_.force_sensor_provider = json::extractString(source, "force_sensor_provider", config_.force_sensor_provider);
  config_.robot_model = json::extractString(source, "robot_model", config_.robot_model);
  config_.axis_count = std::max(1, json::extractInt(source, "axis_count", config_.axis_count));
  config_.sdk_robot_class = json::extractString(source, "sdk_robot_class", config_.sdk_robot_class);
  config_.preferred_link = json::extractString(source, "preferred_link", config_.preferred_link);
  config_.requires_single_control_source = json::extractBool(source, "requires_single_control_source", config_.requires_single_control_source);
  config_.build_id = json::extractString(source, "build_id", config_.build_id);
  config_.software_version = json::extractString(source, "software_version", config_.software_version);
  config_.rt_network_tolerance_percent = json::extractInt(source, "rt_network_tolerance_percent", config_.rt_network_tolerance_percent);
  config_.joint_filter_hz = json::extractDouble(source, "joint_filter_hz", config_.joint_filter_hz);
  config_.cart_filter_hz = json::extractDouble(source, "cart_filter_hz", config_.cart_filter_hz);
  config_.torque_filter_hz = json::extractDouble(source, "torque_filter_hz", config_.torque_filter_hz);
  config_.collision_detection_enabled = json::extractBool(source, "collision_detection_enabled", config_.collision_detection_enabled);
  config_.collision_sensitivity = json::extractInt(source, "collision_sensitivity", config_.collision_sensitivity);
  config_.collision_behavior = json::extractString(source, "collision_behavior", config_.collision_behavior);
  config_.collision_fallback_mm = json::extractDouble(source, "collision_fallback_mm", config_.collision_fallback_mm);
  config_.soft_limit_enabled = json::extractBool(source, "soft_limit_enabled", config_.soft_limit_enabled);
  config_.joint_soft_limit_margin_deg = json::extractDouble(source, "joint_soft_limit_margin_deg", config_.joint_soft_limit_margin_deg);
  config_.singularity_avoidance_enabled = json::extractBool(source, "singularity_avoidance_enabled", config_.singularity_avoidance_enabled);
  config_.rl_project_name = json::extractString(source, "rl_project_name", config_.rl_project_name);
  config_.rl_task_name = json::extractString(source, "rl_task_name", config_.rl_task_name);
  config_.xpanel_vout_mode = json::extractString(source, "xpanel_vout_mode", config_.xpanel_vout_mode);
  config_.fc_frame_type = json::extractString(source, "fc_frame_type", config_.fc_frame_type);
  const auto cartesian_impedance = json::extractDoubleArray(source, "cartesian_impedance", config_.cartesian_impedance);
  if (!cartesian_impedance.empty()) config_.cartesian_impedance = cartesian_impedance;
  const auto desired_wrench_n = json::extractDoubleArray(source, "desired_wrench_n", config_.desired_wrench_n);
  if (!desired_wrench_n.empty()) config_.desired_wrench_n = desired_wrench_n;
  const auto fc_frame_matrix = json::extractDoubleArray(source, "fc_frame_matrix", config_.fc_frame_matrix);
  if (!fc_frame_matrix.empty()) config_.fc_frame_matrix = fc_frame_matrix;
  const auto tcp_frame_matrix = json::extractDoubleArray(source, "tcp_frame_matrix", config_.tcp_frame_matrix);
  if (!tcp_frame_matrix.empty()) config_.tcp_frame_matrix = tcp_frame_matrix;
  const auto load_com_mm = json::extractDoubleArray(source, "load_com_mm", config_.load_com_mm);
  if (!load_com_mm.empty()) config_.load_com_mm = load_com_mm;
  const auto load_inertia = json::extractDoubleArray(source, "load_inertia", config_.load_inertia);
  if (!load_inertia.empty()) config_.load_inertia = load_inertia;
}



void CoreRuntime::loadPlanFromJsonLocked(const std::string& json_line) {
  const auto plan = scan_plan_parser_.parseJsonEnvelope(json_line);
  std::string error;
  if (!scan_plan_validator_.validate(plan, &error)) {
    plan_loaded_ = false;
    state_reason_ = error;
    return;
  }
  plan_id_ = plan.plan_id;
  plan_hash_ = !plan.plan_hash.empty() ? plan.plan_hash : json::extractString(json_line, "scan_plan_hash");
  total_segments_ = static_cast<int>(plan.segments.size());
  total_points_ = std::max(total_segments_ * std::max(static_cast<int>(config_.segment_length_mm / std::max(config_.sample_step_mm, 0.1)), 2), 0);
  path_index_ = 0;
  active_waypoint_index_ = 0;
  progress_pct_ = 0.0;
  active_segment_ = total_segments_ > 0 ? plan.segments.front().segment_id : 0;
  sdk_robot_.updateSessionRegisters(active_segment_, frame_id_);
  plan_loaded_ = total_segments_ > 0;
}



FinalVerdict CoreRuntime::compileScanPlanVerdictLocked(const std::string& json_line) {
  applyConfigFromJsonLocked(json_line);
  const auto plan_json = json::extractObject(json_line, "scan_plan", "{}");
  auto plan = scan_plan_parser_.parseJsonEnvelope(plan_json == "{}" ? json_line : plan_json);
  if (plan.plan_hash.empty()) {
    plan.plan_hash = json::extractString(json_line, "scan_plan_hash", plan_hash_);
  }
  FinalVerdict verdict;
  verdict.source = "cpp_robot_core";
  verdict.plan_id = plan.plan_id;
  verdict.plan_hash = plan.plan_hash;
  verdict.evidence_id = std::string("cpp-final-verdict:") + (plan.plan_hash.empty() ? std::string("no-plan") : plan.plan_hash) + ":" + (session_id_.empty() ? std::string("unlocked") : session_id_);

  std::string error;
  if (!scan_plan_validator_.validate(plan, &error)) {
    verdict.accepted = false;
    verdict.reason = error;
    verdict.detail = error;
    verdict.policy_state = "blocked";
    verdict.summary_label = "模型前检阻塞";
    verdict.next_state = "replan_required";
    verdict.blockers.push_back(error);
    return verdict;
  }

  appendMainlineContractIssuesLocked(&verdict.blockers, &verdict.warnings);
  const auto safety = evaluateSafetyLocked();
  if (!safety.active_interlocks.empty()) {
    verdict.warnings.push_back("active interlocks present during compile");
  }
  if (!session_id_.empty() && !plan.session_id.empty() && plan.session_id != session_id_) {
    verdict.warnings.push_back("plan session_id differs from locked session");
  }
  if (!locked_scan_plan_hash_.empty() && !plan.plan_hash.empty() && locked_scan_plan_hash_ != plan.plan_hash) {
    verdict.blockers.push_back("plan_hash does not match locked session freeze");
  }
  if (plan.execution_constraints.max_segment_duration_ms == 0) {
    verdict.warnings.push_back("execution constraint max_segment_duration_ms not set");
  }

  verdict.accepted = verdict.blockers.empty();
  verdict.policy_state = verdict.accepted ? (verdict.warnings.empty() ? "ready" : "warning") : "blocked";
  verdict.summary_label = verdict.accepted ? (verdict.warnings.empty() ? "模型前检通过" : "模型前检告警") : "模型前检阻塞";
  verdict.next_state = verdict.accepted ? (session_id_.empty() ? "lock_session" : "load_scan_plan") : "replan_required";
  verdict.reason = verdict.accepted ? (verdict.warnings.empty() ? "scan plan compiled successfully" : "scan plan compiled with warnings") : verdict.blockers.front();
  verdict.detail = verdict.accepted ? (verdict.warnings.empty() ? "scan plan compiled successfully" : "scan plan compiled with warnings") : verdict.blockers.front();
  return verdict;
}





void CoreRuntime::appendMainlineContractIssuesLocked(std::vector<std::string>* blockers, std::vector<std::string>* warnings) const {
  const auto identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
  auto push_blocker = [&](const std::string& message) {
    if (blockers) blockers->push_back(message);
  };
  auto push_warning = [&](const std::string& message) {
    if (warnings) warnings->push_back(message);
  };
  if (config_.rt_mode != identity.clinical_mainline_mode) {
    push_blocker("clinical mainline requires " + identity.clinical_mainline_mode + " rt_mode");
  }
  if (std::find(identity.supported_rt_modes.begin(), identity.supported_rt_modes.end(), config_.rt_mode) == identity.supported_rt_modes.end()) {
    push_blocker("rt_mode is not supported by the resolved robot identity");
  }
  if (config_.rt_mode == "directTorque") {
    push_blocker("directTorque is forbidden in the clinical mainline");
  }
  if (config_.preferred_link != identity.preferred_link) {
    push_blocker("preferred_link deviates from official clinical mainline link");
  }
  if (!config_.requires_single_control_source || !identity.requires_single_control_source) {
    push_blocker("single control source must be locked before clinical execution");
  }
  if (config_.remote_ip.empty() || config_.local_ip.empty()) {
    push_blocker("remote_ip/local_ip must be configured for connectToRobot");
  }
  if (config_.sdk_robot_class != identity.sdk_robot_class || int(config_.axis_count) != int(identity.axis_count)) {
    push_blocker("robot identity does not match official clinical mainline");
  }
  if (config_.tool_name.empty()) {
    push_blocker("tool_name missing");
  }
  if (config_.tcp_name.empty()) {
    push_blocker("tcp_name missing");
  }
  if (config_.load_kg <= 0.0) {
    push_blocker("load_kg must be positive");
  }
  if (!vectorWithinLimits(config_.cartesian_impedance, identity.cartesian_impedance_limits)) {
    push_blocker("cartesian_impedance exceeds official limits");
  }
  if (!vectorWithinLimits(config_.desired_wrench_n, identity.desired_wrench_limits)) {
    push_blocker("desired_wrench_n exceeds official limits");
  }
  if (config_.joint_filter_hz < identity.joint_filter_range_hz.front() || config_.joint_filter_hz > identity.joint_filter_range_hz.back() ||
      config_.cart_filter_hz < identity.joint_filter_range_hz.front() || config_.cart_filter_hz > identity.joint_filter_range_hz.back() ||
      config_.torque_filter_hz < identity.joint_filter_range_hz.front() || config_.torque_filter_hz > identity.joint_filter_range_hz.back()) {
    push_blocker("filter cutoff frequency out of official range");
  }
  if (config_.rt_network_tolerance_percent < identity.rt_network_tolerance_range.front() || config_.rt_network_tolerance_percent > identity.rt_network_tolerance_range.back()) {
    push_blocker("rt_network_tolerance_percent out of official range");
  } else if (config_.rt_network_tolerance_percent < identity.rt_network_tolerance_recommended.front() || config_.rt_network_tolerance_percent > identity.rt_network_tolerance_recommended.back()) {
    push_warning("rt_network_tolerance_percent outside recommended range");
  }
  if (!config_.collision_detection_enabled) {
    push_blocker("collision detection must stay enabled in the clinical mainline");
  }
  if (!config_.soft_limit_enabled) {
    push_blocker("soft limit must stay enabled in the clinical mainline");
  }
  if (!config_.singularity_avoidance_enabled) {
    push_warning("singularity avoidance is disabled");
  }
  if (!sdk_robot_.sdkAvailable()) {
    push_warning("vendored xCore SDK is not linked; runtime remains contract-simulated");
  }
  if (!sdk_robot_.xmateModelAvailable()) {
    push_warning("xMateModel is unavailable; model authority is degraded");
  }
}



bool CoreRuntime::sessionFreezeConsistentLocked() const {
  if (session_id_.empty() || session_dir_.empty()) {
    return false;
  }
  if (!(tool_ready_ && tcp_ready_ && load_ready_)) {
    return false;
  }
  if (!locked_scan_plan_hash_.empty() && !plan_hash_.empty() && locked_scan_plan_hash_ != plan_hash_) {
    return false;
  }
  return true;
}


}  // namespace robot_core
