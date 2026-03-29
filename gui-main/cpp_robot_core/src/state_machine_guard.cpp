#include "robot_core/state_machine_guard.h"

#include <map>
#include <set>
#include <string>

namespace robot_core {
namespace {
struct PolicyRow { std::set<RobotCoreState> allowed; const char* reject_reason; };
const std::map<std::string, PolicyRow>& policyTable() {
  static const std::map<std::string, PolicyRow> table = {
      {"connect_robot", {{RobotCoreState::Boot, RobotCoreState::Disconnected}, "robot can only connect from BOOT or DISCONNECTED"}},
      {"power_on", {{RobotCoreState::Connected, RobotCoreState::Powered, RobotCoreState::AutoReady}, "power_on requires CONNECTED, POWERED, or AUTO_READY"}},
      {"set_auto_mode", {{RobotCoreState::Powered, RobotCoreState::AutoReady}, "set_auto_mode requires POWERED or AUTO_READY"}},
      {"validate_setup", {{RobotCoreState::Connected, RobotCoreState::Powered, RobotCoreState::AutoReady, RobotCoreState::SessionLocked, RobotCoreState::PathValidated}, "validate_setup requires a connected, powered, ready, locked, or validated state"}},
      {"lock_session", {{RobotCoreState::AutoReady}, "lock_session requires AUTO_READY"}},
      {"load_scan_plan", {{RobotCoreState::SessionLocked, RobotCoreState::PathValidated, RobotCoreState::ScanComplete}, "load_scan_plan requires SESSION_LOCKED, PATH_VALIDATED, or SCAN_COMPLETE"}},
      {"approach_prescan", {{RobotCoreState::PathValidated}, "approach_prescan requires PATH_VALIDATED"}},
      {"seek_contact", {{RobotCoreState::PathValidated, RobotCoreState::Approaching, RobotCoreState::PausedHold, RobotCoreState::RecoveryRetract}, "seek_contact requires PATH_VALIDATED, APPROACHING, PAUSED_HOLD, or RECOVERY_RETRACT"}},
      {"start_scan", {{RobotCoreState::ContactStable, RobotCoreState::PausedHold}, "cannot start scan before contact is stable"}},
      {"pause_scan", {{RobotCoreState::Scanning}, "pause_scan requires SCANNING"}},
      {"resume_scan", {{RobotCoreState::PausedHold}, "resume_scan requires PAUSED_HOLD"}},
      {"safe_retreat", {{RobotCoreState::PathValidated, RobotCoreState::Approaching, RobotCoreState::ContactSeeking, RobotCoreState::ContactStable, RobotCoreState::Scanning, RobotCoreState::PausedHold, RobotCoreState::RecoveryRetract, RobotCoreState::Fault}, "safe_retreat not allowed from current state"}},
      {"go_home", {{RobotCoreState::Connected, RobotCoreState::Powered, RobotCoreState::AutoReady, RobotCoreState::PathValidated, RobotCoreState::ScanComplete, RobotCoreState::SegmentAborted, RobotCoreState::PlanAborted}, "go_home requires an idle, validated, or completed state"}},
      {"clear_fault", {{RobotCoreState::Fault}, "clear_fault requires FAULT"}},
  };
  return table;
}
}  // namespace

bool StateMachineGuard::allow(const std::string& command, RobotCoreState state, std::string* reason) const {
  if (command == "emergency_stop") return true;
  const auto it = policyTable().find(command);
  if (it == policyTable().end()) { if (reason) *reason = "unsupported command"; return false; }
  if (it->second.allowed.count(state) > 0) return true;
  if (reason) *reason = it->second.reject_reason;
  return false;
}

}  // namespace robot_core
