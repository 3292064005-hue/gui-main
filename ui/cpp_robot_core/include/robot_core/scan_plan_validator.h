#pragma once

#include <string>

#include "robot_core/runtime_types.h"

namespace robot_core {

class ScanPlanValidator {
public:
  bool validate(const ScanPlan& plan, const RuntimeConfig* config, std::string* error) const;
  bool validate(const ScanPlan& plan, std::string* error) const { return validate(plan, nullptr, error); }
};

}  // namespace robot_core
