#pragma once

#include <string>

#include "robot_core/runtime_types.h"

namespace robot_core {

class StateMachineGuard {
public:
  bool allow(const std::string& command, RobotCoreState state, std::string* reason) const;
};

}  // namespace robot_core
