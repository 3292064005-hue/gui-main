#include "robot_core/scan_plan_validator.h"

#include <cmath>
#include <set>

namespace robot_core {
namespace {
bool isFiniteWaypoint(const ScanWaypoint& point) {
  return std::isfinite(point.x) && std::isfinite(point.y) && std::isfinite(point.z) &&
         std::isfinite(point.rx) && std::isfinite(point.ry) && std::isfinite(point.rz);
}
bool hasLegalTransitionPolicy(const std::string& policy) {
  return policy == "serpentine" || policy == "step_over" || policy == "return_home" || policy == "overlap_patch";
}
}  // namespace

bool ScanPlanValidator::validate(const ScanPlan& plan, const RuntimeConfig* config, std::string* error) const {
  if (plan.plan_id.empty()) { if (error) *error = "scan plan missing plan_id"; return false; }
  if (plan.plan_hash.empty()) { if (error) *error = "scan plan missing plan_hash"; return false; }
  if (plan.planner_version.empty() || plan.registration_hash.empty()) { if (error) *error = "scan plan missing planner_version or registration_hash"; return false; }
  if (!isFiniteWaypoint(plan.approach_pose) || !isFiniteWaypoint(plan.retreat_pose)) { if (error) *error = "approach/retreat pose contains non-finite values"; return false; }
  if (plan.segments.empty()) { if (error) *error = "scan plan missing segments"; return false; }
  if (plan.execution_constraints.max_segment_duration_ms < 0) { if (error) *error = "execution constraint max_segment_duration_ms must be non-negative"; return false; }
  const auto allowed_lower = plan.execution_constraints.allowed_contact_band.count("lower_n") ? plan.execution_constraints.allowed_contact_band.at("lower_n") : 0.0;
  const auto allowed_upper = plan.execution_constraints.allowed_contact_band.count("upper_n") ? plan.execution_constraints.allowed_contact_band.at("upper_n") : 0.0;
  if (allowed_upper > 0.0 && allowed_lower > allowed_upper) { if (error) *error = "allowed_contact_band lower_n cannot exceed upper_n"; return false; }

  std::set<int> seen_ids;
  int previous_id = 0;
  for (const auto& segment : plan.segments) {
    if (segment.segment_id <= 0) { if (error) *error = "segment_id must be positive"; return false; }
    if (!seen_ids.insert(segment.segment_id).second) { if (error) *error = "segment ids must be unique"; return false; }
    if (previous_id != 0 && segment.segment_id != previous_id + 1) { if (error) *error = "segment ids must be contiguous"; return false; }
    previous_id = segment.segment_id;
    if (segment.waypoints.empty()) { if (error) *error = "every segment must contain at least one waypoint"; return false; }
    if (!segment.segment_hash.empty() && segment.segment_hash.size() < 8) { if (error) *error = "segment_hash is malformed"; return false; }
    if (!hasLegalTransitionPolicy(segment.transition_policy)) { if (error) *error = "transition_policy is not supported"; return false; }
    const auto lower = segment.contact_band.count("lower_n") ? segment.contact_band.at("lower_n") : 0.0;
    const auto upper = segment.contact_band.count("upper_n") ? segment.contact_band.at("upper_n") : 0.0;
    if (upper > 0.0 && lower > upper) { if (error) *error = "contact band lower_n cannot exceed upper_n"; return false; }
    if (allowed_upper > 0.0 && upper > allowed_upper + 1e-6) { if (error) *error = "segment contact band exceeds execution constraint"; return false; }
    if (segment.estimated_duration_ms < 0) { if (error) *error = "estimated_duration_ms must be non-negative"; return false; }
    if (plan.execution_constraints.max_segment_duration_ms > 0 && segment.estimated_duration_ms > plan.execution_constraints.max_segment_duration_ms) { if (error) *error = "segment estimated_duration_ms exceeds execution constraint"; return false; }
    if (segment.quality_target < 0.0 || segment.quality_target > 1.0 || segment.coverage_target < 0.0 || segment.coverage_target > 1.0) { if (error) *error = "segment quality/coverage target must be between 0 and 1"; return false; }
    int waypoint_index = 0;
    for (const auto& waypoint : segment.waypoints) {
      ++waypoint_index;
      if (!isFiniteWaypoint(waypoint)) { if (error) *error = "waypoint contains non-finite values"; return false; }
      if (std::fabs(waypoint.z - plan.approach_pose.z) > 500.0) { if (error) *error = "waypoint z is outside expected execution bounds"; return false; }
      if (waypoint.sequence_index < 0 || waypoint.dwell_ms < 0) { if (error) *error = "waypoint metadata must be non-negative"; return false; }
      if (waypoint_index > 1) {
        const auto& prev = segment.waypoints[static_cast<std::size_t>(waypoint_index - 2)];
        const double delta = std::fabs(waypoint.x - prev.x) + std::fabs(waypoint.y - prev.y) + std::fabs(waypoint.z - prev.z);
        if (delta == 0.0) { if (error) *error = "schema_valid: consecutive waypoints must not be identical"; return false; }
        if (waypoint.sequence_index != 0 && prev.sequence_index != 0 && waypoint.sequence_index <= prev.sequence_index) { if (error) *error = "schema_valid: waypoint sequence_index must be strictly increasing"; return false; }
      }
      if (config != nullptr && waypoint_index > 1) {
        const auto& prev = segment.waypoints[static_cast<std::size_t>(waypoint_index - 2)];
        const double dx = waypoint.x - prev.x;
        const double dy = waypoint.y - prev.y;
        const double dz = waypoint.z - prev.z;
        const double translation_delta_mm = std::sqrt(dx * dx + dy * dy + dz * dz);
        const double rotation_delta = std::fabs(waypoint.rx - prev.rx) + std::fabs(waypoint.ry - prev.ry) + std::fabs(waypoint.rz - prev.rz);
        const double max_step_mm = std::max(config->sample_step_mm * 16.0, std::max(10.0, config->segment_length_mm));
        if (translation_delta_mm > max_step_mm) { if (error) *error = "runtime_feasible: waypoint translation delta exceeds configured execution envelope"; return false; }
        if (!std::isfinite(rotation_delta) || rotation_delta > (4.0 * M_PI)) { if (error) *error = "runtime_feasible: waypoint rotation delta is not executable"; return false; }
      }
    }
  }
  if (config != nullptr && plan.execution_constraints.max_segment_duration_ms > 0 && config->scan_tangent_speed_max_mm_s > 0.0) {
    const double longest_segment_ms = static_cast<double>(plan.execution_constraints.max_segment_duration_ms);
    if (longest_segment_ms <= 0.0) { if (error) *error = "profile_compatible: max_segment_duration_ms must be positive when constraints are present"; return false; }
  }
  return true;
}

}  // namespace robot_core
