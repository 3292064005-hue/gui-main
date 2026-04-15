#pragma once

#include <string>

#include "robot_core/runtime_command_contracts.h"

namespace robot_core {

class CoreRuntime;

class CoreRuntimeDispatcher {
public:
  explicit CoreRuntimeDispatcher(CoreRuntime& owner);
  std::string handleCommandJson(const std::string& line);

private:
  using CommandHandler = std::string (CoreRuntime::*)(const RuntimeCommandInvocation&);
  CommandHandler resolveHandler(const std::string& handler_group) const;
  CoreRuntime& owner_;
};

}  // namespace robot_core
