#pragma once

#include <string>

#include "robot_core/runtime_types.h"

namespace robot_core {

class ScanPlanParser {
public:
  ScanPlan parseJsonEnvelope(const std::string& json_line) const;
};

}  // namespace robot_core
