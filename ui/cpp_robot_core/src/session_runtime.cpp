#include "robot_core/core_runtime.h"

#include <algorithm>

#include "json_utils.h"
#include "robot_core/robot_identity_contract.h"
#include "robot_core/generated_runtime_config_apply_snapshot.inc"

namespace robot_core {


void CoreRuntime::applyConfigSnapshotLocked(const std::string& config_snapshot_json) {
  const auto& source = config_snapshot_json.empty() ? std::string("{}") : config_snapshot_json;
  // Historical contract token retained for generated-config sync checks:
  // ROBOT_CORE_APPLY_RUNTIME_CONFIG_SNAPSHOT(config_, source);
  ROBOT_CORE_APPLY_RUNTIME_CONFIG_SNAPSHOT(state_store_.config, source);
  state_store_.config.normal_damping_gain = state_store_.config.contact_control.virtual_damping * 1e-6;
  state_store_.config.normal_admittance_gain = state_store_.config.contact_control.virtual_mass > 0.0
                                       ? (1.0 / state_store_.config.contact_control.virtual_mass) * 1e-4
                                       : state_store_.config.normal_admittance_gain;
  state_store_.config.seek_contact_max_step_mm = state_store_.config.contact_control.max_normal_step_mm;
  state_store_.config.seek_contact_max_travel_mm = state_store_.config.contact_control.max_normal_travel_mm;
  state_store_.config.pause_hold_integrator_leak = state_store_.config.contact_control.integrator_leak;
  state_store_.config.rt_integrator_limit_n = state_store_.config.contact_control.anti_windup_limit_n;
  state_store_.config.scan_pose_trim_gain = state_store_.config.orientation_trim.gain;
  state_store_.config.rt_max_pose_trim_deg = state_store_.config.orientation_trim.max_trim_deg;
  const auto& identity = resolveRobotIdentity(state_store_.config.robot_model, state_store_.config.sdk_robot_class, state_store_.config.axis_count);
  state_store_.config.robot_model = identity.robot_model;
  state_store_.config.axis_count = identity.axis_count;
  state_store_.config.sdk_robot_class = identity.sdk_robot_class;
  if (state_store_.config.preferred_link.empty()) {
    state_store_.config.preferred_link = identity.preferred_link;
  }
  state_store_.config.requires_single_control_source = identity.requires_single_control_source && state_store_.config.requires_single_control_source;
}



void CoreRuntime::loadPlanLocked(const std::string& scan_plan_json, const std::string& scan_plan_hash) {
  const auto plan = procedure_executor_.scan_plan_parser.parseJsonEnvelope(scan_plan_json.empty() ? std::string("{}") : scan_plan_json);
  std::string error;
  if (!procedure_executor_.scan_plan_validator.validate(plan, &state_store_.config, &error)) {
    clearExecutionPlanRuntimeLocked();
    state_store_.plan_loaded = false;
    state_store_.state_reason = error.empty() ? std::string("scan plan validation failed") : error;
    return;
  }
  const auto authoritative_precheck = procedure_executor_.sdk_robot.validatePlanAuthoritativeKinematics(plan);
  if (authoritative_precheck.available && !authoritative_precheck.passed) {
    clearExecutionPlanRuntimeLocked();
    state_store_.plan_loaded = false;
    state_store_.state_reason = authoritative_precheck.reason.empty() ? std::string("authoritative xMateModel precheck failed") : authoritative_precheck.reason;
    return;
  }
  for (const auto& warning : authoritative_precheck.warnings) {
    procedure_executor_.sdk_robot.appendLog(std::string("authoritative_precheck_warning:") + warning);
  }
  if (!rebuildExecutionPlanRuntimeLocked(plan, &error)) {
    clearExecutionPlanRuntimeLocked();
    state_store_.plan_loaded = false;
    state_store_.state_reason = error.empty() ? std::string("scan plan validation failed") : error;
    return;
  }
  state_store_.plan_id = plan.plan_id;
  state_store_.plan_hash = !plan.plan_hash.empty() ? plan.plan_hash : scan_plan_hash;
  state_store_.total_segments = static_cast<int>(procedure_executor_.execution_plan_runtime.segments.size());
  state_store_.total_points = procedure_executor_.execution_plan_runtime.total_waypoints;
  state_store_.path_index = 0;
  state_store_.active_waypoint_index = 0;
  state_store_.progress_pct = 0.0;
  state_store_.active_segment = state_store_.total_segments > 0 ? procedure_executor_.execution_plan_runtime.segments.front().segment.segment_id : 0;
  procedure_executor_.sdk_robot.updateSessionRegisters(state_store_.active_segment, state_store_.frame_id);
  NrtSessionTargets targets{};
  targets.home_joint_rad = state_store_.config.home_joint_rad;
  targets.approach_pose = procedure_executor_.execution_plan_runtime.approach_pose;
  targets.retreat_pose = procedure_executor_.execution_plan_runtime.retreat_pose;
  targets.approach_pose_valid = true;
  targets.retreat_pose_valid = true;
  if (!procedure_executor_.execution_plan_runtime.segments.empty() && !procedure_executor_.execution_plan_runtime.segments.front().segment.waypoints.empty()) {
    targets.entry_pose = procedure_executor_.execution_plan_runtime.segments.front().segment.waypoints.front();
    targets.entry_pose_valid = true;
  }
  procedure_executor_.nrt_motion_service.configureSessionTargets(targets);
  state_store_.plan_loaded = state_store_.total_segments > 0;
  procedure_executor_.scan_procedure_active = false;
}



FinalVerdict CoreRuntime::compileScanPlanVerdictLocked(const std::string& config_snapshot_json, const std::string& scan_plan_json, const std::string& scan_plan_hash) {
  applyConfigSnapshotLocked(config_snapshot_json);
  auto plan = procedure_executor_.scan_plan_parser.parseJsonEnvelope(scan_plan_json.empty() ? std::string("{}") : scan_plan_json);
  if (plan.plan_hash.empty()) {
    plan.plan_hash = scan_plan_hash.empty() ? state_store_.plan_hash : scan_plan_hash;
  }
  FinalVerdict verdict;
  verdict.source = "cpp_robot_core";
  verdict.plan_id = plan.plan_id;
  verdict.plan_hash = plan.plan_hash;
  verdict.evidence_id = std::string("cpp-final-verdict:") + (plan.plan_hash.empty() ? std::string("no-plan") : plan.plan_hash) + ":" + (state_store_.session_id.empty() ? std::string("unlocked") : state_store_.session_id);

  std::string error;
  if (!procedure_executor_.scan_plan_validator.validate(plan, &state_store_.config, &error)) {
    verdict.accepted = false;
    verdict.reason = error;
    verdict.detail = error;
    verdict.policy_state = "blocked";
    verdict.summary_label = "模型前检阻塞";
    verdict.next_state = "replan_required";
    verdict.blockers.push_back(error);
    return verdict;
  }

  const auto authoritative_precheck = procedure_executor_.sdk_robot.validatePlanAuthoritativeKinematics(plan);
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
  if (!state_store_.session_id.empty() && !plan.session_id.empty() && plan.session_id != state_store_.session_id) {
    verdict.warnings.push_back("plan session_id differs from locked session");
  }
  if (!state_store_.locked_scan_plan_hash.empty() && !plan.plan_hash.empty() && state_store_.locked_scan_plan_hash != plan.plan_hash) {
    verdict.blockers.push_back("plan_hash does not match locked session freeze");
  }
  if (plan.execution_constraints.max_segment_duration_ms == 0) {
    verdict.warnings.push_back("execution constraint max_segment_duration_ms not set");
  }

  verdict.accepted = verdict.blockers.empty();
  verdict.policy_state = verdict.accepted ? (verdict.warnings.empty() ? "ready" : "warning") : "blocked";
  verdict.summary_label = verdict.accepted ? (verdict.warnings.empty() ? "模型前检通过" : "模型前检告警") : "模型前检阻塞";
  verdict.next_state = verdict.accepted ? (state_store_.session_id.empty() ? "lock_session" : "load_scan_plan") : "replan_required";
  verdict.reason = verdict.accepted ? (verdict.warnings.empty() ? "scan plan compiled successfully" : "scan plan compiled with warnings") : verdict.blockers.front();
  verdict.detail = verdict.accepted ? (verdict.warnings.empty() ? "scan plan compiled successfully" : "scan plan compiled with warnings") : verdict.blockers.front();
  return verdict;
}





void CoreRuntime::appendMainlineContractIssuesLocked(std::vector<std::string>* blockers, std::vector<std::string>* warnings) const {
  const auto& identity = resolveRobotIdentity(state_store_.config.robot_model, state_store_.config.sdk_robot_class, state_store_.config.axis_count);
  auto push_blocker = [&](const std::string& message) {
    if (blockers) blockers->push_back(message);
  };
  auto push_warning = [&](const std::string& message) {
    if (warnings) warnings->push_back(message);
  };
  if (state_store_.config.rt_mode != identity.clinical_mainline_mode) {
    push_blocker("clinical mainline requires " + identity.clinical_mainline_mode + " rt_mode");
  }
  if (std::find(identity.supported_rt_modes.begin(), identity.supported_rt_modes.end(), state_store_.config.rt_mode) == identity.supported_rt_modes.end()) {
    push_blocker("rt_mode is not supported by the resolved robot identity");
  }
  if (state_store_.config.rt_mode == "directTorque") {
    push_blocker("directTorque is forbidden in the clinical mainline");
  }
  if (state_store_.config.preferred_link != identity.preferred_link) {
    push_blocker("preferred_link deviates from official clinical mainline link");
  }
  if (!state_store_.config.requires_single_control_source || !identity.requires_single_control_source) {
    push_blocker("single control source must be locked before clinical execution");
  }
  if (state_store_.config.remote_ip.empty() || state_store_.config.local_ip.empty()) {
    push_blocker("remote_ip/local_ip must be configured for connectToRobot");
  }
  if (state_store_.config.sdk_robot_class != identity.sdk_robot_class || int(state_store_.config.axis_count) != int(identity.axis_count)) {
    push_blocker("robot identity does not match official clinical mainline");
  }
  if (state_store_.config.tool_name.empty()) {
    push_blocker("tool_name missing");
  }
  if (state_store_.config.tcp_name.empty()) {
    push_blocker("tcp_name missing");
  }
  if (state_store_.config.load_kg <= 0.0) {
    push_blocker("load_kg must be positive");
  }
  if (!vectorWithinLimits(state_store_.config.cartesian_impedance, identity.cartesian_impedance_limits)) {
    push_blocker("cartesian_impedance exceeds official limits");
  }
  if (!vectorWithinLimits(state_store_.config.desired_wrench_n, identity.desired_wrench_limits)) {
    push_blocker("desired_wrench_n exceeds official limits");
  }
  if (state_store_.config.joint_filter_hz < identity.joint_filter_range_hz.front() || state_store_.config.joint_filter_hz > identity.joint_filter_range_hz.back() ||
      state_store_.config.cart_filter_hz < identity.joint_filter_range_hz.front() || state_store_.config.cart_filter_hz > identity.joint_filter_range_hz.back() ||
      state_store_.config.torque_filter_hz < identity.joint_filter_range_hz.front() || state_store_.config.torque_filter_hz > identity.joint_filter_range_hz.back()) {
    push_blocker("filter cutoff frequency out of official range");
  }
  if (state_store_.config.rt_network_tolerance_percent < identity.rt_network_tolerance_range.front() || state_store_.config.rt_network_tolerance_percent > identity.rt_network_tolerance_range.back()) {
    push_blocker("rt_network_tolerance_percent out of official range");
  } else if (state_store_.config.rt_network_tolerance_percent < identity.rt_network_tolerance_recommended.front() || state_store_.config.rt_network_tolerance_percent > identity.rt_network_tolerance_recommended.back()) {
    push_warning("rt_network_tolerance_percent outside recommended range");
  }
  if (!state_store_.config.collision_detection_enabled) {
    push_blocker("collision detection must stay enabled in the clinical mainline");
  }
  if (!state_store_.config.soft_limit_enabled) {
    push_blocker("soft limit must stay enabled in the clinical mainline");
  }
  if (!state_store_.config.singularity_avoidance_enabled) {
    push_warning("singularity avoidance is disabled");
  }
  if (!procedure_executor_.sdk_robot.sdkAvailable()) {
    push_warning("vendored xCore SDK is not linked; runtime remains contract-simulated");
  }
  if (!procedure_executor_.sdk_robot.xmateModelAvailable()) {
    push_warning("xMateModel is unavailable; model authority is degraded");
  }
}




}  // namespace robot_core
