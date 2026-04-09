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
      {"connect_robot", true, "BOOT|DISCONNECTED", "hardware_lifecycle_write"},
      {"disconnect_robot", true, "BOOT|DISCONNECTED|CONNECTED|POWERED|AUTO_READY|FAULT|ESTOP", "hardware_lifecycle_write"},
      {"power_on", true, "CONNECTED|POWERED|AUTO_READY", "hardware_lifecycle_write"},
      {"power_off", true, "CONNECTED|POWERED|AUTO_READY|SESSION_LOCKED|PATH_VALIDATED", "hardware_lifecycle_write"},
      {"set_auto_mode", true, "POWERED|AUTO_READY", "hardware_lifecycle_write"},
      {"set_manual_mode", true, "CONNECTED|POWERED|AUTO_READY", "hardware_lifecycle_write"},
      {"validate_setup", true, "CONNECTED|POWERED|AUTO_READY|SESSION_LOCKED|PATH_VALIDATED", "runtime_validation"},
      {"validate_scan_plan", false, "AUTO_READY|SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE", "plan_compile"},
      {"compile_scan_plan", false, "AUTO_READY|SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE", "plan_compile"},
      {"query_final_verdict", false, "*", "runtime_read"},
      {"query_controller_log", false, "*", "runtime_read"},
      {"query_rl_projects", false, "*", "runtime_read"},
      {"query_path_lists", false, "*", "runtime_read"},
      {"get_io_snapshot", false, "*", "runtime_read"},
      {"get_register_snapshot", false, "*", "runtime_read"},
      {"get_safety_config", false, "*", "runtime_read"},
      {"get_motion_contract", false, "*", "runtime_read"},
      {"get_runtime_alignment", false, "*", "runtime_read"},
      {"get_xmate_model_summary", false, "*", "runtime_read"},
      {"get_sdk_runtime_config", false, "*", "runtime_read"},
      {"get_identity_contract", false, "*", "runtime_read"},
      {"get_robot_family_contract", false, "*", "runtime_read"},
      {"get_vendor_boundary_contract", false, "*", "runtime_read"},
      {"get_clinical_mainline_contract", false, "*", "runtime_read"},
      {"get_session_drift_contract", false, "*", "runtime_read"},
      {"get_hardware_lifecycle_contract", false, "*", "runtime_read"},
      {"get_rt_kernel_contract", false, "*", "runtime_read"},
      {"get_session_freeze", false, "*", "runtime_read"},
      {"get_authoritative_runtime_envelope", false, "*", "runtime_read"},
      {"get_control_governance_contract", false, "*", "runtime_read"},
      {"get_controller_evidence", false, "*", "runtime_read"},
      {"get_dual_state_machine_contract", false, "*", "runtime_read"},
      {"get_mainline_executor_contract", false, "*", "runtime_read"},
      {"get_recovery_contract", false, "*", "runtime_read"},
      {"get_safety_recovery_contract", false, "*", "runtime_read"},
      {"get_capability_contract", false, "*", "runtime_read"},
      {"get_model_authority_contract", false, "*", "runtime_read"},
      {"get_release_contract", false, "*", "runtime_read"},
      {"get_deployment_contract", false, "*", "runtime_read"},
      {"get_fault_injection_contract", false, "*", "runtime_read"},
      {"inject_fault", true, "*", "fault_injection_write"},
      {"clear_injected_faults", true, "*", "fault_injection_write"},
      {"lock_session", true, "AUTO_READY", "session_freeze_write"},
      {"load_scan_plan", true, "SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE", "session_freeze_write"},
      {"approach_prescan", true, "PATH_VALIDATED", "rt_motion_write"},
      {"seek_contact", true, "PATH_VALIDATED|APPROACHING|PAUSED_HOLD|RECOVERY_RETRACT", "rt_motion_write"},
      {"start_scan", true, "CONTACT_STABLE|PAUSED_HOLD", "rt_motion_write"},
      {"pause_scan", true, "SCANNING", "rt_motion_write"},
      {"resume_scan", true, "PAUSED_HOLD", "rt_motion_write"},
      {"safe_retreat", true, "PATH_VALIDATED|APPROACHING|CONTACT_SEEKING|CONTACT_STABLE|SCANNING|PAUSED_HOLD|RECOVERY_RETRACT|FAULT", "rt_motion_write"},
      {"go_home", true, "CONNECTED|POWERED|AUTO_READY|PATH_VALIDATED|SCAN_COMPLETE|SEGMENT_ABORTED|PLAN_ABORTED", "nrt_motion_write"},
      {"run_rl_project", true, "AUTO_READY|SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE", "nrt_motion_write"},
      {"pause_rl_project", true, "AUTO_READY|SCANNING|PAUSED_HOLD|SESSION_LOCKED|PATH_VALIDATED|SCAN_COMPLETE", "nrt_motion_write"},
      {"enable_drag", true, "CONNECTED", "nrt_motion_write"},
      {"disable_drag", true, "CONNECTED", "nrt_motion_write"},
      {"replay_path", true, "AUTO_READY|PATH_VALIDATED|SCAN_COMPLETE", "nrt_motion_write"},
      {"start_record_path", true, "CONNECTED", "nrt_motion_write"},
      {"stop_record_path", true, "CONNECTED", "nrt_motion_write"},
      {"cancel_record_path", true, "CONNECTED", "nrt_motion_write"},
      {"save_record_path", true, "CONNECTED", "nrt_motion_write"},
      {"clear_fault", true, "FAULT", "recovery_write"},
      {"emergency_stop", true, "*", "recovery_write"},
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
