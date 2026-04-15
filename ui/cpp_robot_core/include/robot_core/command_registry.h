#pragma once

#include <string>
#include <vector>

#include <cstddef>

#include "robot_core/runtime_types.h"

namespace robot_core {

enum class CommandRuntimeLane {
  Command,
  Query,
  RtControl,
};

struct CommandRegistryEntry {
  const char* name;
  bool write_command;
  const char* state_preconditions_signature;
  const char* capability_claim;
  const char* canonical_command;
  const char* alias_kind;
  const char* handler_group;
  const char* deprecation_stage;
  const char* removal_target;
  const char* replacement_command;
  const char* compatibility_note;
};

const std::vector<CommandRegistryEntry>& commandRegistry();
const CommandRegistryEntry* findCommandRegistryEntry(const std::string& command);
std::vector<std::string> commandNames();
bool isRegisteredCommand(const std::string& command);
bool isWriteCommand(const std::string& command);
std::vector<std::string> commandStatePreconditions(const std::string& command);
std::string commandCapabilityClaim(const std::string& command);
std::string commandCanonicalName(const std::string& command);
std::string commandAliasKind(const std::string& command);
std::string commandHandlerGroup(const std::string& command);

/**
 * @brief Return manifest-driven deprecation state for a command.
 *
 * @param command Runtime command name.
 * @return std::string Deprecation stage token, empty when the command is not in retirement.
 * @throws No exceptions are thrown.
 */
std::string commandDeprecationStage(const std::string& command);

/**
 * @brief Return the target removal window for a deprecated command alias.
 *
 * @param command Runtime command name.
 * @return std::string Removal target label such as a quarter or release identifier.
 * @throws No exceptions are thrown.
 */
std::string commandRemovalTarget(const std::string& command);

/**
 * @brief Return the canonical replacement command for a deprecated alias.
 *
 * @param command Runtime command name.
 * @return std::string Canonical replacement command name, or empty when not applicable.
 * @throws No exceptions are thrown.
 */
std::string commandReplacementCommand(const std::string& command);

/**
 * @brief Return the manifest compatibility note for a command.
 *
 * @param command Runtime command name.
 * @return std::string Human-readable compatibility guidance.
 * @throws No exceptions are thrown.
 */
std::string commandCompatibilityNote(const std::string& command);

/**
 * @brief Classify which runtime lane owns a command.
 *
 * @param command Runtime command name.
 * @return CommandRuntimeLane Command lane classification used by the dispatcher.
 * @throws No exceptions are thrown.
 *
 * Boundary behaviour:
 * - Query commands resolve to CommandRuntimeLane::Query.
 * - RT control commands resolve to CommandRuntimeLane::RtControl.
 * - All remaining registered commands resolve to CommandRuntimeLane::Command.
 */
CommandRuntimeLane commandRuntimeLane(const std::string& command);
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
