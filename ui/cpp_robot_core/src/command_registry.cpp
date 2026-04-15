#include "robot_core/command_registry.h"

#include <algorithm>
#include <sstream>
#include <unordered_map>

namespace robot_core {

namespace {

// Generated registry metadata carries signatures such as
// "CONTACT_STABLE|PAUSED_HOLD" for state-aware command guards.
std::vector<std::string> splitStates(const char* signature) {
  std::vector<std::string> items;
  if (signature == nullptr || *signature == '\0') return items;
  std::stringstream stream(signature);
  std::string item;
  while (std::getline(stream, item, '|')) {
    if (!item.empty()) items.push_back(item);
  }
  return items;
}

const std::unordered_map<std::string, const CommandRegistryEntry*>& commandRegistryIndex() {
  static const std::unordered_map<std::string, const CommandRegistryEntry*> kIndex = [] {
    std::unordered_map<std::string, const CommandRegistryEntry*> items;
    items.reserve(commandRegistry().size());
    for (const auto& entry : commandRegistry()) {
      items.emplace(entry.name, &entry);
    }
    return items;
  }();
  return kIndex;
}

}  // namespace

const std::vector<CommandRegistryEntry>& commandRegistry() {
  static const std::vector<CommandRegistryEntry> kRegistry = {
#include "robot_core/generated_command_manifest.inc"
  };
  return kRegistry;
}

const CommandRegistryEntry* findCommandRegistryEntry(const std::string& command) {
  const auto& index = commandRegistryIndex();
  const auto it = index.find(command);
  return it == index.end() ? nullptr : it->second;
}

std::vector<std::string> commandNames() {
  std::vector<std::string> names;
  names.reserve(commandRegistry().size());
  for (const auto& item : commandRegistry()) names.emplace_back(item.name);
  return names;
}

bool isRegisteredCommand(const std::string& command) {
  return findCommandRegistryEntry(command) != nullptr;
}

bool isWriteCommand(const std::string& command) {
  const auto* entry = findCommandRegistryEntry(command);
  return entry == nullptr ? true : entry->write_command;
}

std::vector<std::string> commandStatePreconditions(const std::string& command) {
  const auto* entry = findCommandRegistryEntry(command);
  return entry == nullptr ? std::vector<std::string>{} : splitStates(entry->state_preconditions_signature);
}

std::string commandCapabilityClaim(const std::string& command) {
  const auto* entry = findCommandRegistryEntry(command);
  return entry == nullptr || entry->capability_claim == nullptr ? std::string{} : std::string(entry->capability_claim);
}

std::string commandCanonicalName(const std::string& command) {
  const auto* entry = findCommandRegistryEntry(command);
  return entry == nullptr || entry->canonical_command == nullptr ? command : std::string(entry->canonical_command);
}

std::string commandAliasKind(const std::string& command) {
  const auto* entry = findCommandRegistryEntry(command);
  return entry == nullptr || entry->alias_kind == nullptr ? std::string{} : std::string(entry->alias_kind);
}

std::string commandHandlerGroup(const std::string& command) {
  const auto* entry = findCommandRegistryEntry(command);
  return entry == nullptr || entry->handler_group == nullptr ? std::string{} : std::string(entry->handler_group);
}

std::string commandDeprecationStage(const std::string& command) {
  const auto* entry = findCommandRegistryEntry(command);
  return entry == nullptr || entry->deprecation_stage == nullptr ? std::string{} : std::string(entry->deprecation_stage);
}

std::string commandRemovalTarget(const std::string& command) {
  const auto* entry = findCommandRegistryEntry(command);
  return entry == nullptr || entry->removal_target == nullptr ? std::string{} : std::string(entry->removal_target);
}

std::string commandReplacementCommand(const std::string& command) {
  const auto* entry = findCommandRegistryEntry(command);
  return entry == nullptr || entry->replacement_command == nullptr ? std::string{} : std::string(entry->replacement_command);
}

std::string commandCompatibilityNote(const std::string& command) {
  const auto* entry = findCommandRegistryEntry(command);
  return entry == nullptr || entry->compatibility_note == nullptr ? std::string{} : std::string(entry->compatibility_note);
}

CommandRuntimeLane commandRuntimeLane(const std::string& command) {
  const auto capability_claim = commandCapabilityClaim(command);
  if (capability_claim == "rt_motion_write") {
    return CommandRuntimeLane::RtControl;
  }
  if (capability_claim == "runtime_read" || capability_claim == "runtime_validation" || capability_claim == "plan_compile") {
    return CommandRuntimeLane::Query;
  }
  return CommandRuntimeLane::Command;
}

std::size_t commandRegistrySize() {
  return commandRegistry().size();
}

std::string commandRegistryStateName(RobotCoreState state) {
  switch (state) {
    case RobotCoreState::Boot: return "BOOT";
    case RobotCoreState::Disconnected: return "DISCONNECTED";
    case RobotCoreState::Connected: return "CONNECTED";
    case RobotCoreState::Powered: return "POWERED";
    case RobotCoreState::AutoReady: return "AUTO_READY";
    case RobotCoreState::SessionLocked: return "SESSION_LOCKED";
    case RobotCoreState::PathValidated: return "PATH_VALIDATED";
    case RobotCoreState::Approaching: return "APPROACHING";
    case RobotCoreState::ContactSeeking: return "CONTACT_SEEKING";
    case RobotCoreState::ContactStable: return "CONTACT_STABLE";
    case RobotCoreState::Scanning: return "SCANNING";
    case RobotCoreState::PausedHold: return "PAUSED_HOLD";
    case RobotCoreState::RecoveryRetract: return "RECOVERY_RETRACT";
    case RobotCoreState::SegmentAborted: return "SEGMENT_ABORTED";
    case RobotCoreState::PlanAborted: return "PLAN_ABORTED";
    case RobotCoreState::Retreating: return "RETREATING";
    case RobotCoreState::ScanComplete: return "SCAN_COMPLETE";
    case RobotCoreState::Fault: return "FAULT";
    case RobotCoreState::Estop: return "ESTOP";
  }
  return "BOOT";
}

bool commandAllowedInState(const std::string& command, RobotCoreState state, std::string* reason) {
  const auto* entry = findCommandRegistryEntry(command);
  if (entry == nullptr) {
    if (reason != nullptr) *reason = "unsupported command";
    return false;
  }
  const auto allowed_states = commandStatePreconditions(command);
  if (allowed_states.empty() || std::find(allowed_states.begin(), allowed_states.end(), "*") != allowed_states.end()) {
    return true;
  }
  const auto runtime_state_name = commandRegistryStateName(state);
  if (std::find(allowed_states.begin(), allowed_states.end(), runtime_state_name) != allowed_states.end()) {
    return true;
  }
  if (reason != nullptr) {
    *reason = command + " requires state in [" + entry->state_preconditions_signature + "] but current state is " + runtime_state_name;
  }
  return false;
}

}  // namespace robot_core
