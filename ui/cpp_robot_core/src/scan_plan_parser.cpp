#include "robot_core/scan_plan_parser.h"

#include "json_utils.h"

namespace robot_core {

namespace {
ScanWaypoint parseWaypoint(const std::string& object_json) {
  ScanWaypoint point;
  point.x = json::extractDouble(object_json, "x", 0.0);
  point.y = json::extractDouble(object_json, "y", 0.0);
  point.z = json::extractDouble(object_json, "z", 0.0);
  point.rx = json::extractDouble(object_json, "rx", 0.0);
  point.ry = json::extractDouble(object_json, "ry", 0.0);
  point.rz = json::extractDouble(object_json, "rz", 0.0);
  point.sequence_index = json::extractInt(object_json, "sequence_index", 0);
  point.dwell_ms = json::extractInt(object_json, "dwell_ms", 0);
  point.probe_required = json::extractBool(object_json, "probe_required", false);
  point.checkpoint_tag = json::extractString(object_json, "checkpoint_tag");
  point.transition_hint = json::extractString(object_json, "transition_hint");
  return point;
}
}  // namespace

ScanPlan ScanPlanParser::parseJsonEnvelope(const std::string& json_line) const {
  ScanPlan plan;
  plan.session_id = json::extractString(json_line, "session_id");
  plan.plan_id = json::extractString(json_line, "plan_id");
  plan.planner_version = json::extractString(json_line, "planner_version");
  plan.registration_hash = json::extractString(json_line, "registration_hash");
  plan.plan_kind = json::extractString(json_line, "plan_kind", "preview");
  plan.plan_hash = json::extractString(json_line, "plan_hash", json::extractString(json_line, "scan_plan_hash"));
  plan.validation_summary = json::extractObject(json_line, "validation_summary", "{}");
  plan.score_summary = json::extractObject(json_line, "score_summary", "{}");
  plan.surface_model_hash = json::extractString(json_line, "surface_model_hash");
  plan.created_ts_ns = static_cast<int64_t>(json::extractInt(json_line, "created_ts_ns", 0));
  plan.approach_pose = parseWaypoint(json::extractObject(json_line, "approach_pose", "{}"));
  plan.retreat_pose = parseWaypoint(json::extractObject(json_line, "retreat_pose", "{}"));

  const auto constraints = json::extractObject(json_line, "execution_constraints", "{}");
  plan.execution_constraints.max_segment_duration_ms = json::extractInt(constraints, "max_segment_duration_ms", 0);
  plan.execution_constraints.transition_smoothing = json::extractString(constraints, "transition_smoothing", "standard");
  plan.execution_constraints.recovery_checkpoint_policy = json::extractString(constraints, "recovery_checkpoint_policy", "segment_boundary");
  plan.execution_constraints.probe_spacing_mm = json::extractDouble(constraints, "probe_spacing_mm", 0.0);
  plan.execution_constraints.probe_depth_mm = json::extractDouble(constraints, "probe_depth_mm", 0.0);
  const auto allowed_contact_band = json::extractObject(constraints, "allowed_contact_band", "{}");
  plan.execution_constraints.allowed_contact_band["lower_n"] = json::extractDouble(allowed_contact_band, "lower_n", 0.0);
  plan.execution_constraints.allowed_contact_band["upper_n"] = json::extractDouble(allowed_contact_band, "upper_n", 0.0);

  const auto segments_json = json::extractArray(json_line, "segments", "[]");
  for (const auto& segment_json : json::splitTopLevelObjects(segments_json)) {
    ScanSegment segment;
    segment.segment_id = json::extractInt(segment_json, "segment_id", 0);
    if (segment.segment_id <= 0) {
      continue;
    }
    segment.segment_priority = json::extractInt(segment_json, "segment_priority", segment.segment_id);
    segment.requires_contact_probe = json::extractBool(segment_json, "requires_contact_probe", true);
    segment.needs_resample = json::extractBool(segment_json, "needs_resample", false);
    segment.target_pressure = json::extractDouble(segment_json, "target_pressure", 1.5);
    segment.estimated_duration_ms = json::extractInt(segment_json, "estimated_duration_ms", 0);
    segment.quality_target = json::extractDouble(segment_json, "quality_target", 0.0);
    segment.coverage_target = json::extractDouble(segment_json, "coverage_target", 0.0);
    segment.segment_hash = json::extractString(segment_json, "segment_hash");
    segment.transition_policy = json::extractString(segment_json, "transition_policy", "serpentine");
    segment.scan_direction = json::extractString(segment_json, "scan_direction", "caudal_to_cranial");
    segment.rescan_origin_segment = json::extractInt(segment_json, "rescan_origin_segment", 0);
    const auto contact_band = json::extractObject(segment_json, "contact_band", "{}");
    segment.contact_band["lower_n"] = json::extractDouble(contact_band, "lower_n", 0.0);
    segment.contact_band["upper_n"] = json::extractDouble(contact_band, "upper_n", 0.0);

    const auto waypoints_json = json::extractArray(segment_json, "waypoints", "[]");
    for (const auto& waypoint_json : json::splitTopLevelObjects(waypoints_json)) {
      segment.waypoints.push_back(parseWaypoint(waypoint_json));
    }
    plan.segments.push_back(segment);
  }
  return plan;
}

}  // namespace robot_core
