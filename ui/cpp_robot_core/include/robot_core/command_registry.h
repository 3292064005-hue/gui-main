#pragma once

#include <string>
#include <vector>

#include <cstddef>

#include "robot_core/runtime_types.h"

namespace robot_core {

struct CommandRegistryEntry {
  const char* name;
  bool write_command;
  const char* state_preconditions_signature;
};

const std::vector<CommandRegistryEntry>& commandRegistry();
const CommandRegistryEntry* findCommandRegistryEntry(const std::string& command);
std::vector<std::string> commandNames();
bool isRegisteredCommand(const std::string& command);
bool isWriteCommand(const std::string& command);
std::vector<std::string> commandStatePreconditions(const std::string& command);
std::size_t commandRegistrySize();

/**
 * @brief Resolve the contract-facing state name for a runtime state value.
 *
 * @param state Runtime state enum value.
 * @return std::string Upper-case contract state token.
 * @throws No exceptions are thrown.
 */
std::string commandRegistryStateName(RobotCoreState state);

/**
 * @brief Check whether a command is allowed for the provided runtime state.
 *
 * @param command Command name.
 * @param state Current runtime state.
 * @param reason Optional rejection reason output.
 * @return true when the command registry allows the state, otherwise false.
 * @throws No exceptions are thrown.
 */
bool commandAllowedInState(const std::string& command, RobotCoreState state, std::string* reason = nullptr);

}  // namespace robot_core
