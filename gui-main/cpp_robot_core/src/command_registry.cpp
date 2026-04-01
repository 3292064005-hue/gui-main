#include "robot_core/command_registry.h"

#include <algorithm>
#include <sstream>
#include <unordered_map>

namespace robot_core {

namespace {

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
      {"connect_robot", true, "BOOT|DISCONNECTED"},
      {"disconnect_robot", true, "BOOT|DISCONNECTED|CONNECTED|POWERED|AUTO_READY|FAULT|ESTOP"},
      {"power_on", true, "CONNECTED|POWERED|AUTO_READY"},
      {"power_off", true, "CONNECTED|POWERED|AUTO_READY|SESSION_LOCKED|PATH_VALIDATED"},
      {"set_auto_mode", true, "POWERED|AUTO_READY"},
      {"set_manual_mode", true, "CONNECTED|POWERED|AUTO_READY"},
      {"validate_setup", true, "CONNECTED|POWERED|AUTO_READY|SESSION_LOCKED|PATH_VALIDATED"},
      {"compile_scan_plan", false, "AUTO_READY|SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE"},
      {"query_final_verdict", false, "*"},
      {"query_controller_log", false, "*"},
      {"query_rl_projects", false, "*"},
      {"query_path_lists", false, "*"},
      {"get_io_snapshot", false, "*"},
      {"get_register_snapshot", false, "*"},
      {"get_safety_config", false, "*"},
      {"get_motion_contract", false, "*"},
      {"get_runtime_alignment", false, "*"},
      {"get_xmate_model_summary", false, "*"},
      {"get_sdk_runtime_config", false, "*"},
      {"get_identity_contract", false, "*"},
      {"get_robot_family_contract", false, "*"},
      {"get_vendor_boundary_contract", false, "*"},
      {"get_clinical_mainline_contract", false, "*"},
      {"get_session_drift_contract", false, "*"},
      {"get_hardware_lifecycle_contract", false, "*"},
      {"get_rt_kernel_contract", false, "*"},
      {"get_session_freeze", false, "*"},
      {"get_authoritative_runtime_envelope", false, "*"},
      {"get_control_governance_contract", false, "*"},
      {"get_controller_evidence", false, "*"},
      {"get_dual_state_machine_contract", false, "*"},
      {"get_mainline_executor_contract", false, "*"},
      {"get_recovery_contract", false, "*"},
      {"get_safety_recovery_contract", false, "*"},
      {"get_capability_contract", false, "*"},
      {"get_model_authority_contract", false, "*"},
      {"get_release_contract", false, "*"},
      {"get_deployment_contract", false, "*"},
      {"get_fault_injection_contract", false, "*"},
      {"inject_fault", true, "*"},
      {"clear_injected_faults", true, "*"},
      {"lock_session", true, "AUTO_READY"},
      {"load_scan_plan", true, "SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE"},
      {"approach_prescan", true, "PATH_VALIDATED"},
      {"seek_contact", true, "PATH_VALIDATED|APPROACHING|PAUSED_HOLD|RECOVERY_RETRACT"},
      {"start_scan", true, "CONTACT_STABLE|PAUSED_HOLD"},
      {"pause_scan", true, "SCANNING"},
      {"resume_scan", true, "PAUSED_HOLD"},
      {"safe_retreat", true, "PATH_VALIDATED|APPROACHING|CONTACT_SEEKING|CONTACT_STABLE|SCANNING|PAUSED_HOLD|RECOVERY_RETRACT|FAULT"},
      {"go_home", true, "CONNECTED|POWERED|AUTO_READY|PATH_VALIDATED|SCAN_COMPLETE|SEGMENT_ABORTED|PLAN_ABORTED"},
      {"clear_fault", true, "FAULT"},
      {"emergency_stop", true, "*"},
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
    if (reason != nullptr) {
      *reason = "unsupported command";
    }
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
