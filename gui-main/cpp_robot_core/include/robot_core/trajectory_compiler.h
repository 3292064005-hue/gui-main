#pragma once
#include <vector>
#include "robot_core/runtime_types.h"
namespace robot_core {
class TrajectoryCompiler {
public:
  ScanPlan compileDemoPath(const std::string& session_id, double sample_step_mm,
                           double segment_length_mm) const;
};
}
