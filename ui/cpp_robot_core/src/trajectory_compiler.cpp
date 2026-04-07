#include "robot_core/trajectory_compiler.h"
namespace robot_core {
ScanPlan TrajectoryCompiler::compileDemoPath(const std::string& session_id, double sample_step_mm,
                                             double segment_length_mm) const {
  ScanPlan plan;
  plan.session_id = session_id;
  plan.plan_id = "demo_plan";
  plan.approach_pose = {118.0, 12.0, 224.0, 180.0, 0.0, 90.0};
  plan.retreat_pose = {118.0, 12.0, 238.0, 180.0, 0.0, 90.0};
  for (int segment_id = 1; segment_id <= 4; ++segment_id) {
    ScanSegment segment;
    segment.segment_id = segment_id;
    segment.target_pressure = 1.5;
    segment.scan_direction = segment_id % 2 == 0 ? "cranial_to_caudal" : "caudal_to_cranial";
    const int num_points = static_cast<int>(segment_length_mm / sample_step_mm);
    for (int idx = 0; idx < num_points; ++idx) {
      segment.waypoints.push_back({110.0 + sample_step_mm * idx, 10.0 + 4.0 * segment_id,
                                   205.0, 180.0, 0.0, 90.0});
    }
    plan.segments.push_back(segment);
  }
  return plan;
}
}
