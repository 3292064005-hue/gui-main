#include "robot_core/state_machine_guard.h"

#include "robot_core/command_registry.h"

namespace robot_core {

bool StateMachineGuard::allow(const std::string& command, RobotCoreState state, std::string* reason) const {
  return commandAllowedInState(command, state, reason);
}

}  // namespace robot_core
