#include "robot_core/core_runtime.h"

#include <algorithm>
#include <cmath>

namespace robot_core {
namespace {

double waypointDistanceM(const ScanWaypoint& a, const ScanWaypoint& b) {
  const double dx = b.x - a.x;
  const double dy = b.y - a.y;
  const double dz = b.z - a.z;
  return std::sqrt(dx * dx + dy * dy + dz * dz);
}

int totalWaypointCount(const std::vector<ExecutionSegmentRuntime>& segments) {
  int count = 0;
  for (const auto& segment : segments) {
    count += static_cast<int>(segment.segment.waypoints.size());
  }
  return count;
}

}  // namespace

void CoreRuntime::clearExecutionPlanRuntimeLocked() {
  execution_plan_runtime_ = ExecutionPlanRuntime{};
  sdk_robot_.clearPlannedSegment();
  nrt_motion_service_.clearSessionTargets();
}

bool CoreRuntime::rebuildExecutionPlanRuntimeLocked(const ScanPlan& plan, std::string* error) {
  ExecutionPlanRuntime runtime;
  runtime.session_id = plan.session_id;
  runtime.plan_id = plan.plan_id;
  runtime.plan_hash = plan.plan_hash;
  runtime.approach_pose = plan.approach_pose;
  runtime.retreat_pose = plan.retreat_pose;
  runtime.active_segment_index = 0;
  runtime.active_waypoint_index = 0;
  runtime.completed_waypoints = 0;
  runtime.started = false;
  runtime.finished = false;
  for (const auto& segment : plan.segments) {
    if (segment.waypoints.empty()) {
      if (error) *error = "execution_plan_runtime segment missing waypoints";
      return false;
    }
    ExecutionSegmentRuntime segment_runtime;
    segment_runtime.segment = segment;
    segment_runtime.cumulative_lengths_m.reserve(segment.waypoints.size());
    double cumulative = 0.0;
    segment_runtime.cumulative_lengths_m.push_back(0.0);
    for (std::size_t idx = 1; idx < segment.waypoints.size(); ++idx) {
      cumulative += std::max(0.0, waypointDistanceM(segment.waypoints[idx - 1], segment.waypoints[idx]));
      segment_runtime.cumulative_lengths_m.push_back(cumulative);
    }
    segment_runtime.total_length_m = cumulative;
    runtime.segments.push_back(std::move(segment_runtime));
  }
  runtime.total_waypoints = totalWaypointCount(runtime.segments);
  runtime.active_checkpoint_tag = runtime.segments.empty() || runtime.segments.front().segment.waypoints.empty()
                                      ? std::string{}
                                      : runtime.segments.front().segment.waypoints.front().checkpoint_tag;
  execution_plan_runtime_ = std::move(runtime);
  return true;
}

bool CoreRuntime::configureActiveSegmentLocked(std::string* reason) {
  if (execution_plan_runtime_.segments.empty()) {
    if (reason) *reason = "no_execution_plan_runtime";
    return false;
  }
  const auto segment_index = std::clamp(execution_plan_runtime_.active_segment_index, 0, static_cast<int>(execution_plan_runtime_.segments.size()) - 1);
  execution_plan_runtime_.active_segment_index = segment_index;
  const auto& active = execution_plan_runtime_.segments[static_cast<std::size_t>(segment_index)].segment;
  active_segment_ = active.segment_id;
  active_waypoint_index_ = std::clamp(execution_plan_runtime_.active_waypoint_index, 0, static_cast<int>(active.waypoints.size()) - 1);
  execution_plan_runtime_.active_waypoint_index = active_waypoint_index_;
  execution_plan_runtime_.active_checkpoint_tag = active.waypoints[static_cast<std::size_t>(active_waypoint_index_)].checkpoint_tag;
  sdk_robot_.setPlannedSegment(active);
  NrtSessionTargets targets{};
  targets.home_joint_rad = config_.home_joint_rad;
  targets.approach_pose = execution_plan_runtime_.approach_pose;
  targets.retreat_pose = execution_plan_runtime_.retreat_pose;
  targets.approach_pose_valid = true;
  targets.retreat_pose_valid = true;
  targets.entry_pose = active.waypoints.front();
  targets.entry_pose_valid = true;
  nrt_motion_service_.configureSessionTargets(targets);
  sdk_robot_.updateSessionRegisters(active_segment_, frame_id_);
  return true;
}

bool CoreRuntime::startPlanDrivenScanLocked(std::string* reason) {
  if (!configureActiveSegmentLocked(reason)) {
    return false;
  }
  if (!rt_motion_service_.startScanFollowRt()) {
    if (reason) *reason = "rt_scan_follow_start_failed";
    return false;
  }
  execution_state_ = RobotCoreState::Scanning;
  execution_plan_runtime_.started = true;
  state_reason_ = "scan_active";
  contact_state_.mode = "STABLE_CONTACT";
  contact_state_.recommended_action = "SCAN";
  sdk_robot_.collaborationPort().setRlStatus(config_.rl_project_name, config_.rl_task_name, true);
  return true;
}

bool CoreRuntime::advancePlanSegmentLocked(std::string* reason) {
  if (execution_plan_runtime_.segments.empty()) {
    if (reason) *reason = "no_execution_plan_runtime";
    return false;
  }
  const int next_segment = execution_plan_runtime_.active_segment_index + 1;
  if (next_segment >= static_cast<int>(execution_plan_runtime_.segments.size())) {
    execution_plan_runtime_.finished = true;
    progress_pct_ = 100.0;
    execution_state_ = RobotCoreState::ScanComplete;
    contact_state_.mode = "NO_CONTACT";
    contact_state_.recommended_action = "POSTPROCESS";
    sdk_robot_.collaborationPort().setRlStatus(config_.rl_project_name, config_.rl_task_name, false);
    sdk_robot_.clearPlannedSegment();
    return true;
  }
  execution_plan_runtime_.active_segment_index = next_segment;
  execution_plan_runtime_.active_waypoint_index = 0;
  return startPlanDrivenScanLocked(reason);
}

void CoreRuntime::updatePlanProgressLocked(const RtObservedState& observed, const RtPhaseTelemetry& phase_telemetry) {
  (void)observed;
  if (execution_plan_runtime_.segments.empty()) {
    return;
  }
  const auto segment_index = std::clamp(execution_plan_runtime_.active_segment_index, 0, static_cast<int>(execution_plan_runtime_.segments.size()) - 1);
  const auto& segment_runtime = execution_plan_runtime_.segments[static_cast<std::size_t>(segment_index)];
  const auto& segment = segment_runtime.segment;
  const double segment_length_m = std::max(segment_runtime.total_length_m, std::max(0.001, config_.sample_step_mm / 1000.0 * std::max<int>(1, static_cast<int>(segment.waypoints.size()) - 1)));
  const double tangent_progress_m = std::clamp(phase_telemetry.tangent_progress_m, 0.0, segment_length_m);
  std::size_t waypoint_index = 0;
  while (waypoint_index + 1 < segment_runtime.cumulative_lengths_m.size() &&
         segment_runtime.cumulative_lengths_m[waypoint_index + 1] <= tangent_progress_m + 1e-9) {
    ++waypoint_index;
  }
  execution_plan_runtime_.active_waypoint_index = static_cast<int>(waypoint_index);
  active_waypoint_index_ = execution_plan_runtime_.active_waypoint_index;
  execution_plan_runtime_.active_checkpoint_tag = segment.waypoints[waypoint_index].checkpoint_tag;

  int completed = 0;
  for (int idx = 0; idx < segment_index; ++idx) {
    completed += static_cast<int>(execution_plan_runtime_.segments[static_cast<std::size_t>(idx)].segment.waypoints.size());
  }
  completed += static_cast<int>(waypoint_index);
  execution_plan_runtime_.completed_waypoints = completed;
  path_index_ = completed;
  total_points_ = execution_plan_runtime_.total_waypoints;
  progress_pct_ = total_points_ > 0 ? (100.0 * static_cast<double>(completed) / static_cast<double>(total_points_)) : 0.0;
  active_segment_ = segment.segment_id;
  sdk_robot_.updateSessionRegisters(active_segment_, frame_id_);
}

}  // namespace robot_core
