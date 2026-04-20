#include "robot_core/core_runtime.h"

#include <algorithm>

#include "json_utils.h"
#include "robot_core/robot_identity_contract.h"
#include "robot_core/generated_runtime_config_apply_snapshot.inc"

namespace robot_core {


void CoreRuntime::applyConfigSnapshotLocked(const std::string& config_snapshot_json) {
  const auto& source = config_snapshot_json.empty() ? std::string("{}") : config_snapshot_json;
  ROBOT_CORE_APPLY_RUNTIME_CONFIG_SNAPSHOT(config_, source);
  config_.normal_damping_gain = config_.contact_control.virtual_damping * 1e-6;
  config_.normal_admittance_gain = config_.contact_control.virtual_mass > 0.0
                                       ? (1.0 / config_.contact_control.virtual_mass) * 1e-4
                                       : config_.normal_admittance_gain;
  config_.seek_contact_max_step_mm = config_.contact_control.max_normal_step_mm;
  config_.seek_contact_max_travel_mm = config_.contact_control.max_normal_travel_mm;
  config_.pause_hold_integrator_leak = config_.contact_control.integrator_leak;
  config_.rt_integrator_limit_n = config_.contact_control.anti_windup_limit_n;
  config_.scan_pose_trim_gain = config_.orientation_trim.gain;
  config_.rt_max_pose_trim_deg = config_.orientation_trim.max_trim_deg;
  const auto& identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
  config_.robot_model = identity.robot_model;
  config_.axis_count = identity.axis_count;
  config_.sdk_robot_class = identity.sdk_robot_class;
  if (config_.preferred_link.empty()) {
    config_.preferred_link = identity.preferred_link;
  }
  config_.requires_single_control_source = identity.requires_single_control_source && config_.requires_single_control_source;
}



void CoreRuntime::loadPlanLocked(const std::string& scan_plan_json, const std::string& scan_plan_hash) {
  const auto plan = scan_plan_parser_.parseJsonEnvelope(scan_plan_json.empty() ? std::string("{}") : scan_plan_json);
  std::string error;
  if (!scan_plan_validator_.validate(plan, &config_, &error)) {
    clearExecutionPlanRuntimeLocked();
    plan_loaded_ = false;
    state_reason_ = error.empty() ? std::string("scan plan validation failed") : error;
    return;
  }
  const auto authoritative_precheck = sdk_robot_.validatePlanAuthoritativeKinematics(plan);
  if (authoritative_precheck.available && !authoritative_precheck.passed) {
    clearExecutionPlanRuntimeLocked();
    plan_loaded_ = false;
    state_reason_ = authoritative_precheck.reason.empty() ? std::string("authoritative xMateModel precheck failed") : authoritative_precheck.reason;
    return;
  }
  for (const auto& warning : authoritative_precheck.warnings) {
    sdk_robot_.appendLog(std::string("authoritative_precheck_warning:") + warning);
  }
  if (!rebuildExecutionPlanRuntimeLocked(plan, &error)) {
    clearExecutionPlanRuntimeLocked();
    plan_loaded_ = false;
    state_reason_ = error.empty() ? std::string("scan plan validation failed") : error;
    return;
  }
  plan_id_ = plan.plan_id;
  plan_hash_ = !plan.plan_hash.empty() ? plan.plan_hash : scan_plan_hash;
  total_segments_ = static_cast<int>(execution_plan_runtime_.segments.size());
  total_points_ = execution_plan_runtime_.total_waypoints;
  path_index_ = 0;
  active_waypoint_index_ = 0;
  progress_pct_ = 0.0;
  active_segment_ = total_segments_ > 0 ? execution_plan_runtime_.segments.front().segment.segment_id : 0;
  sdk_robot_.updateSessionRegisters(active_segment_, frame_id_);
  NrtSessionTargets targets{};
  targets.home_joint_rad = config_.home_joint_rad;
  targets.approach_pose = execution_plan_runtime_.approach_pose;
  targets.retreat_pose = execution_plan_runtime_.retreat_pose;
  targets.approach_pose_valid = true;
  targets.retreat_pose_valid = true;
  if (!execution_plan_runtime_.segments.empty() && !execution_plan_runtime_.segments.front().segment.waypoints.empty()) {
    targets.entry_pose = execution_plan_runtime_.segments.front().segment.waypoints.front();
    targets.entry_pose_valid = true;
  }
  nrt_motion_service_.configureSessionTargets(targets);
  NrtFallbackTargets fallback{};
  fallback.home_joint_rad = config_.emergency_home_joint_rad;
  fallback.approach_pose_xyzabc = config_.emergency_approach_pose_xyzabc;
  fallback.entry_pose_xyzabc = config_.emergency_entry_pose_xyzabc;
  fallback.retreat_pose_xyzabc = config_.emergency_retreat_pose_xyzabc;
  nrt_motion_service_.configureFallbackTargets(fallback);
  plan_loaded_ = total_segments_ > 0;
  scan_procedure_active_ = false;
}



FinalVerdict CoreRuntime::compileScanPlanVerdictLocked(const std::string& config_snapshot_json, const std::string& scan_plan_json, const std::string& scan_plan_hash) {
  applyConfigSnapshotLocked(config_snapshot_json);
  auto plan = scan_plan_parser_.parseJsonEnvelope(scan_plan_json.empty() ? std::string("{}") : scan_plan_json);
  if (plan.plan_hash.empty()) {
    plan.plan_hash = scan_plan_hash.empty() ? plan_hash_ : scan_plan_hash;
  }
  FinalVerdict verdict;
  verdict.source = "cpp_robot_core";
  verdict.plan_id = plan.plan_id;
  verdict.plan_hash = plan.plan_hash;
  verdict.evidence_id = std::string("cpp-final-verdict:") + (plan.plan_hash.empty() ? std::string("no-plan") : plan.plan_hash) + ":" + (session_id_.empty() ? std::string("unlocked") : session_id_);

  std::string error;
  if (!scan_plan_validator_.validate(plan, &config_, &error)) {
    verdict.accepted = false;
    verdict.reason = error;
    verdict.detail = error;
    verdict.policy_state = "blocked";
    verdict.summary_label = "模型前检阻塞";
    verdict.next_state = "replan_required";
    verdict.blockers.push_back(error);
    return verdict;
  }

  const auto authoritative_precheck = sdk_robot_.validatePlanAuthoritativeKinematics(plan);
  if (authoritative_precheck.available) {
    if (!authoritative_precheck.passed) {
      verdict.blockers.push_back(authoritative_precheck.reason.empty() ? std::string("kinematic_valid: authoritative xMateModel feasibility failed") : authoritative_precheck.reason);
    }
    for (const auto& warning : authoritative_precheck.warnings) {
      verdict.warnings.push_back(std::string("kinematic_valid: ") + warning);
    }
  } else if (!authoritative_precheck.reason.empty()) {
    verdict.warnings.push_back(std::string("kinematic_valid advisory degraded: ") + authoritative_precheck.reason);
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
  const auto& identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
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




}  // namespace robot_core
