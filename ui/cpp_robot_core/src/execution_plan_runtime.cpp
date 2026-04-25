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
  procedure_executor_.execution_plan_runtime = ExecutionPlanRuntime{};
  procedure_executor_.sdk_robot.clearPlannedSegment();
  procedure_executor_.nrt_motion_service.clearSessionTargets();
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
  procedure_executor_.execution_plan_runtime = std::move(runtime);
  return true;
}

bool CoreRuntime::configureActiveSegmentLocked(std::string* reason) {
  if (procedure_executor_.execution_plan_runtime.segments.empty()) {
    if (reason) *reason = "no_execution_plan_runtime";
    return false;
  }
  const auto segment_index = std::clamp(procedure_executor_.execution_plan_runtime.active_segment_index, 0, static_cast<int>(procedure_executor_.execution_plan_runtime.segments.size()) - 1);
  procedure_executor_.execution_plan_runtime.active_segment_index = segment_index;
  const auto& active = procedure_executor_.execution_plan_runtime.segments[static_cast<std::size_t>(segment_index)].segment;
  state_store_.active_segment = active.segment_id;
  state_store_.active_waypoint_index = std::clamp(procedure_executor_.execution_plan_runtime.active_waypoint_index, 0, static_cast<int>(active.waypoints.size()) - 1);
  procedure_executor_.execution_plan_runtime.active_waypoint_index = state_store_.active_waypoint_index;
  procedure_executor_.execution_plan_runtime.active_checkpoint_tag = active.waypoints[static_cast<std::size_t>(state_store_.active_waypoint_index)].checkpoint_tag;
  procedure_executor_.sdk_robot.setPlannedSegment(active);
  NrtSessionTargets targets{};
  targets.home_joint_rad = state_store_.config.home_joint_rad;
  targets.approach_pose = procedure_executor_.execution_plan_runtime.approach_pose;
  targets.retreat_pose = procedure_executor_.execution_plan_runtime.retreat_pose;
  targets.approach_pose_valid = true;
  targets.retreat_pose_valid = true;
  targets.entry_pose = active.waypoints.front();
  targets.entry_pose_valid = true;
  procedure_executor_.nrt_motion_service.configureSessionTargets(targets);
  procedure_executor_.sdk_robot.updateSessionRegisters(state_store_.active_segment, state_store_.frame_id);
  return true;
}

bool CoreRuntime::startPlanDrivenScanLocked(std::string* reason) {
  if (!configureActiveSegmentLocked(reason)) {
    return false;
  }
  if (!procedure_executor_.rt_motion_service.startScanFollowRt()) {
    if (reason) *reason = "rt_scan_follow_start_failed";
    return false;
  }
  state_store_.execution_state = RobotCoreState::Scanning;
  procedure_executor_.execution_plan_runtime.started = true;
  state_store_.state_reason = "scan_active";
  state_store_.contact_state.mode = "STABLE_CONTACT";
  state_store_.contact_state.recommended_action = "SCAN";
  procedure_executor_.sdk_robot.collaborationPort().setRlStatus(state_store_.config.rl_project_name, state_store_.config.rl_task_name, true);
  return true;
}

bool CoreRuntime::advancePlanSegmentLocked(std::string* reason) {
  if (procedure_executor_.execution_plan_runtime.segments.empty()) {
    if (reason) *reason = "no_execution_plan_runtime";
    return false;
  }
  const int next_segment = procedure_executor_.execution_plan_runtime.active_segment_index + 1;
  if (next_segment >= static_cast<int>(procedure_executor_.execution_plan_runtime.segments.size())) {
    procedure_executor_.execution_plan_runtime.finished = true;
    state_store_.progress_pct = 100.0;
    state_store_.execution_state = RobotCoreState::ScanComplete;
    state_store_.contact_state.mode = "NO_CONTACT";
    state_store_.contact_state.recommended_action = "POSTPROCESS";
    procedure_executor_.sdk_robot.collaborationPort().setRlStatus(state_store_.config.rl_project_name, state_store_.config.rl_task_name, false);
    procedure_executor_.sdk_robot.clearPlannedSegment();
    return true;
  }
  procedure_executor_.execution_plan_runtime.active_segment_index = next_segment;
  procedure_executor_.execution_plan_runtime.active_waypoint_index = 0;
  return startPlanDrivenScanLocked(reason);
}

void CoreRuntime::updatePlanProgressLocked(const RtObservedState& observed, const RtPhaseTelemetry& phase_telemetry) {
  (void)observed;
  if (procedure_executor_.execution_plan_runtime.segments.empty()) {
    return;
  }
  const auto segment_index = std::clamp(procedure_executor_.execution_plan_runtime.active_segment_index, 0, static_cast<int>(procedure_executor_.execution_plan_runtime.segments.size()) - 1);
  const auto& segment_runtime = procedure_executor_.execution_plan_runtime.segments[static_cast<std::size_t>(segment_index)];
  const auto& segment = segment_runtime.segment;
  const double segment_length_m = std::max(segment_runtime.total_length_m, std::max(0.001, state_store_.config.sample_step_mm / 1000.0 * std::max<int>(1, static_cast<int>(segment.waypoints.size()) - 1)));
  const double tangent_progress_m = std::clamp(phase_telemetry.tangent_progress_m, 0.0, segment_length_m);
  std::size_t waypoint_index = 0;
  while (waypoint_index + 1 < segment_runtime.cumulative_lengths_m.size() &&
         segment_runtime.cumulative_lengths_m[waypoint_index + 1] <= tangent_progress_m + 1e-9) {
    ++waypoint_index;
  }
  procedure_executor_.execution_plan_runtime.active_waypoint_index = static_cast<int>(waypoint_index);
  state_store_.active_waypoint_index = procedure_executor_.execution_plan_runtime.active_waypoint_index;
  procedure_executor_.execution_plan_runtime.active_checkpoint_tag = segment.waypoints[waypoint_index].checkpoint_tag;

  int completed = 0;
  for (int idx = 0; idx < segment_index; ++idx) {
    completed += static_cast<int>(procedure_executor_.execution_plan_runtime.segments[static_cast<std::size_t>(idx)].segment.waypoints.size());
  }
  completed += static_cast<int>(waypoint_index);
  procedure_executor_.execution_plan_runtime.completed_waypoints = completed;
  state_store_.path_index = completed;
  state_store_.total_points = procedure_executor_.execution_plan_runtime.total_waypoints;
  state_store_.progress_pct = state_store_.total_points > 0 ? (100.0 * static_cast<double>(completed) / static_cast<double>(state_store_.total_points)) : 0.0;
  state_store_.active_segment = segment.segment_id;
  procedure_executor_.sdk_robot.updateSessionRegisters(state_store_.active_segment, state_store_.frame_id);
}

}  // namespace robot_core
