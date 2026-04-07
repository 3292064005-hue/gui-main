#pragma once

#include <string>

#include "robot_core/runtime_types.h"

namespace robot_core {

class ScanPlanValidator {
public:
  bool validate(const ScanPlan& plan, std::string* error) const;
};

}  // namespace robot_core
