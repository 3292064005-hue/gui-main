#include "robot_core/nrt_motion_service.h"

#include <sstream>

#include "robot_core/sdk_robot_facade.h"

namespace robot_core {

namespace {
const std::vector<NrtProfileTemplate> kProfileCatalog{{"go_home", "MoveAbsJ", false, true, true},
                                                      {"approach_prescan", "MoveL", true, true, true},
                                                      {"align_to_entry", "MoveL", true, true, true},
                                                      {"safe_retreat", "MoveL", false, true, true},
                                                      {"recovery_retreat", "MoveL", false, true, true},
                                                      {"post_scan_home", "MoveAbsJ", false, true, true}};
}

NrtMotionService::NrtMotionService(SdkRobotFacade* sdk) : sdk_(sdk) {
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.blocking_profiles = {"go_home", "approach_prescan", "align_to_entry", "safe_retreat", "recovery_retreat", "post_scan_home"};
  snapshot_.templates = kProfileCatalog;
}

void NrtMotionService::bind(SdkRobotFacade* sdk) {
  sdk_ = sdk;
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.executor_wrapped = true;
  snapshot_.sdk_delegation_only = true;
  snapshot_.templates = kProfileCatalog;
}

bool NrtMotionService::goHome() { return dispatchProfile(profileTemplate("go_home")); }
bool NrtMotionService::approachPrescan() { return dispatchProfile(profileTemplate("approach_prescan")); }
bool NrtMotionService::alignToEntry() { return dispatchProfile(profileTemplate("align_to_entry")); }
bool NrtMotionService::safeRetreat() { return dispatchProfile(profileTemplate("safe_retreat")); }
bool NrtMotionService::recoveryRetreat() { return dispatchProfile(profileTemplate("recovery_retreat")); }
bool NrtMotionService::postScanHome() { return dispatchProfile(profileTemplate("post_scan_home")); }

NrtMotionSnapshot NrtMotionService::snapshot() const { return snapshot_; }

NrtProfileTemplate NrtMotionService::profileTemplate(const std::string& profile) const {
  for (const auto& item : kProfileCatalog) {
    if (item.name == profile) {
      return item;
    }
  }
  return {profile, "MoveL", false, true, true};
}

bool NrtMotionService::dispatchProfile(const NrtProfileTemplate& profile) {
  snapshot_.active_profile = profile.name;
  snapshot_.last_command = profile.sdk_command;
  snapshot_.last_command_id = profile.name + "::" + std::to_string(snapshot_.command_count + 1);
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.ready = true;
  snapshot_.requires_move_reset = profile.requires_move_reset;
  snapshot_.requires_single_control_source = sdk_ != nullptr ? sdk_->controlSourceExclusive() : true;

  std::ostringstream oss;
  oss << "nrt profile=" << profile.name << " sdk_command=" << profile.sdk_command
      << " policy=delegate_path_planning_to_sdk moveReset_before_batch=" << (profile.requires_move_reset ? "true" : "false");

  if (sdk_ != nullptr) {
    std::string reason;
    if (!sdk_->beginNrtProfile(profile.name, profile.sdk_command, profile.requires_auto_mode, &reason)) {
      snapshot_.ready = false;
      snapshot_.last_result = "blocked:" + reason;
      record(oss.str() + " result=blocked reason=" + reason);
      return false;
    }
    snapshot_.last_result = "accepted";
    record(oss.str() + " result=accepted command_sequence=" + std::to_string(sdk_->commandSequence()));
    sdk_->finishNrtProfile(profile.name, true, "executor_contract_accepted");
    return true;
  }

  snapshot_.last_result = "contract_only";
  record(oss.str() + " result=contract_only reason=no_sdk_binding");
  return true;
}

void NrtMotionService::record(const std::string& message) {
  snapshot_.command_count += 1;
  snapshot_.command_log.push_back(message);
  if (snapshot_.command_log.size() > 24) {
    snapshot_.command_log.erase(snapshot_.command_log.begin(), snapshot_.command_log.begin() + static_cast<long>(snapshot_.command_log.size() - 24));
  }
}

}  // namespace robot_core
