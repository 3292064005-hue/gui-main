#include "robot_core/nrt_motion_service.h"

#include <algorithm>
#include <cmath>
#include <sstream>

#include "robot_core/sdk_robot_facade.h"

namespace robot_core {

namespace {
const std::vector<NrtProfileTemplate> kProfileCatalog{{"go_home", "MoveAbsJ", true, true, true},
                                                      {"approach_prescan", "MoveL", true, true, true},
                                                      {"align_to_entry", "MoveL", true, true, true},
                                                      {"safe_retreat", "MoveL", true, true, true},
                                                      {"recovery_retreat", "MoveL", true, true, true},
                                                      {"post_scan_home", "MoveAbsJ", true, true, true}};

std::vector<double> waypointToTcpPose(const ScanWaypoint& waypoint) {
  return {waypoint.x, waypoint.y, waypoint.z, waypoint.rx, waypoint.ry, waypoint.rz};
}

bool waypointValid(const ScanWaypoint& waypoint) {
  return std::isfinite(waypoint.x) && std::isfinite(waypoint.y) && std::isfinite(waypoint.z) &&
         std::isfinite(waypoint.rx) && std::isfinite(waypoint.ry) && std::isfinite(waypoint.rz);
}

bool fallbackPoseValid(const std::vector<double>& pose) {
  return pose.size() >= 6 && std::all_of(pose.begin(), pose.begin() + 6, [](double value) { return std::isfinite(value); });
}

ScanWaypoint fallbackPoseToWaypoint(const std::vector<double>& pose) {
  ScanWaypoint waypoint{};
  if (pose.size() >= 6) {
    waypoint.x = pose[0];
    waypoint.y = pose[1];
    waypoint.z = pose[2];
    waypoint.rx = pose[3];
    waypoint.ry = pose[4];
    waypoint.rz = pose[5];
  }
  return waypoint;
}
}  // namespace

NrtMotionService::NrtMotionService(SdkRobotFacade* sdk) : sdk_(sdk) {
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.blocking_profiles = {"go_home", "approach_prescan", "align_to_entry", "safe_retreat", "recovery_retreat", "post_scan_home"};
  snapshot_.templates = kProfileCatalog;
}

void NrtMotionService::bind(SdkRobotFacade* sdk) {
  sdk_ = sdk;
  snapshot_.degraded_without_sdk = (sdk_ == nullptr);
  snapshot_.executor_wrapped = true;
  snapshot_.sdk_delegation_only = false;
  snapshot_.templates = kProfileCatalog;
}

void NrtMotionService::configureSessionTargets(const NrtSessionTargets& targets) {
  session_targets_ = targets;
}

void NrtMotionService::configureFallbackTargets(const NrtFallbackTargets& targets) {
  fallback_targets_ = targets;
}

void NrtMotionService::clearSessionTargets() {
  session_targets_ = NrtSessionTargets{};
}

bool NrtMotionService::goHome(std::string* reason) { return dispatchProfile(profileTemplate("go_home"), reason); }
bool NrtMotionService::approachPrescan(std::string* reason) { return dispatchProfile(profileTemplate("approach_prescan"), reason); }
bool NrtMotionService::alignToEntry(std::string* reason) { return dispatchProfile(profileTemplate("align_to_entry"), reason); }
bool NrtMotionService::safeRetreat(std::string* reason) { return dispatchProfile(profileTemplate("safe_retreat"), reason); }
bool NrtMotionService::recoveryRetreat(std::string* reason) { return dispatchProfile(profileTemplate("recovery_retreat"), reason); }
bool NrtMotionService::postScanHome(std::string* reason) { return dispatchProfile(profileTemplate("post_scan_home"), reason); }

NrtMotionSnapshot NrtMotionService::snapshot() const { return snapshot_; }

NrtProfileTemplate NrtMotionService::profileTemplate(const std::string& profile) const {
  for (const auto& item : kProfileCatalog) {
    if (item.name == profile) return item;
  }
  return {profile, "MoveL", true, true, true};
}

NrtMotionPlan NrtMotionService::buildProfile(const std::string& profile_name) const {
  NrtMotionPlan plan;
  plan.profile_name = profile_name;
  plan.requires_auto_mode = true;
  plan.requires_move_reset = true;

  auto add_pose_step = [&](const ScanWaypoint& waypoint, int speed_mm_s) {
    plan.sdk_command = "MoveL";
    plan.steps.push_back({NrtCommandType::MoveL, {}, waypointToTcpPose(waypoint), speed_mm_s, 0, false, true});
  };

  if ((profile_name == "go_home" || profile_name == "post_scan_home") && !session_targets_.home_joint_rad.empty()) {
    plan.sdk_command = "MoveAbsJ";
    plan.steps.push_back({NrtCommandType::MoveAbsJ, session_targets_.home_joint_rad, {}, 180, 0, false, true});
    return plan;
  }

  if (profile_name == "approach_prescan" && session_targets_.approach_pose_valid && waypointValid(session_targets_.approach_pose)) {
    add_pose_step(session_targets_.approach_pose, 120);
    return plan;
  }
  if (profile_name == "align_to_entry" && session_targets_.entry_pose_valid && waypointValid(session_targets_.entry_pose)) {
    add_pose_step(session_targets_.entry_pose, 80);
    return plan;
  }
  if ((profile_name == "safe_retreat" || profile_name == "recovery_retreat") && session_targets_.retreat_pose_valid && waypointValid(session_targets_.retreat_pose)) {
    add_pose_step(session_targets_.retreat_pose, 200);
    return plan;
  }

  // Fallback emergency profiles stay available for bring-up / recovery only.
  if ((profile_name == "go_home" || profile_name == "post_scan_home") && !fallback_targets_.home_joint_rad.empty()) {
    plan.sdk_command = "MoveAbsJ";
    plan.steps.push_back({NrtCommandType::MoveAbsJ, fallback_targets_.home_joint_rad, {}, 180, 0, false, true});
    return plan;
  }
  plan.sdk_command = "MoveL";
  if (profile_name == "approach_prescan" && fallbackPoseValid(fallback_targets_.approach_pose_xyzabc)) {
    const auto wp = fallbackPoseToWaypoint(fallback_targets_.approach_pose_xyzabc);
    plan.steps.push_back({NrtCommandType::MoveL, {}, waypointToTcpPose(wp), 120, 0, false, true});
  } else if (profile_name == "align_to_entry" && fallbackPoseValid(fallback_targets_.entry_pose_xyzabc)) {
    const auto wp = fallbackPoseToWaypoint(fallback_targets_.entry_pose_xyzabc);
    plan.steps.push_back({NrtCommandType::MoveL, {}, waypointToTcpPose(wp), 80, 0, false, true});
  } else if ((profile_name == "safe_retreat" || profile_name == "recovery_retreat") && fallbackPoseValid(fallback_targets_.retreat_pose_xyzabc)) {
    const auto wp = fallbackPoseToWaypoint(fallback_targets_.retreat_pose_xyzabc);
    plan.steps.push_back({NrtCommandType::MoveL, {}, waypointToTcpPose(wp), 200, 0, false, true});
  } else if (profile_name == "go_home" || profile_name == "post_scan_home") {
    plan.sdk_command = "MoveAbsJ";
    plan.steps.push_back({NrtCommandType::MoveAbsJ, {0.0, 0.30, 0.60, 0.0, 1.20, 0.0}, {}, 180, 0, false, true});
    return plan;
  } else if (profile_name == "approach_prescan") {
    plan.steps.push_back({NrtCommandType::MoveL, {}, {0.118, 0.015, 0.205, 3.1415926535, 0.0, 1.5707963267}, 120, 0, false, true});
  } else if (profile_name == "align_to_entry") {
    plan.steps.push_back({NrtCommandType::MoveL, {}, {0.118, 0.015, 0.190, 3.1415926535, 0.0, 1.5707963267}, 80, 0, false, true});
  } else if (profile_name == "safe_retreat" || profile_name == "recovery_retreat") {
    plan.steps.push_back({NrtCommandType::MoveL, {}, {0.118, 0.015, 0.230, 3.1415926535, 0.0, 1.5707963267}, 200, 0, false, true});
  } else {
    plan.steps.push_back({NrtCommandType::MoveL, {}, {0.118, 0.015, 0.205, 3.1415926535, 0.0, 1.5707963267}, 120, 0, false, true});
  }
  return plan;
}

bool NrtMotionService::executeProfile(const NrtMotionPlan& plan, std::string* reason) {
  if (sdk_ == nullptr) {
    if (reason) *reason = "sdk_facade_unavailable";
    return false;
  }
  if (!sdk_->nrtExecutionPort().beginProfile(plan.profile_name, plan.sdk_command, plan.requires_auto_mode, reason)) {
    return false;
  }
  bool ok = true;
  std::string local_reason;
  for (const auto& step : plan.steps) {
    switch (step.command_type) {
      case NrtCommandType::MoveAbsJ:
        ok = sdk_->nrtExecutionPort().executeMoveAbsJ(step.target_joint_rad, step.speed_mm_s, step.zone_mm, &local_reason);
        break;
      case NrtCommandType::MoveL:
        ok = sdk_->nrtExecutionPort().executeMoveL(step.target_tcp_xyzabc_m_rad, step.speed_mm_s, step.zone_mm, &local_reason);
        break;
      default:
        ok = false;
        local_reason = "unsupported_nrt_command";
        break;
    }
    if (!ok) break;
  }
  sdk_->nrtExecutionPort().finishProfile(plan.profile_name, ok, ok ? "executed" : local_reason);
  if (reason != nullptr) *reason = local_reason;
  return ok;
}

bool NrtMotionService::dispatchProfile(const NrtProfileTemplate& profile, std::string* reason) {
  snapshot_.active_profile = profile.name;
  snapshot_.last_command = profile.sdk_command;
  snapshot_.last_command_id = profile.name + "::" + std::to_string(snapshot_.command_count + 1);
  snapshot_.degraded_without_sdk = (sdk_ == nullptr) || !sdk_->queryPort().liveBindingEstablished();
  snapshot_.ready = true;
  snapshot_.requires_move_reset = profile.requires_move_reset;
  snapshot_.requires_single_control_source = sdk_ != nullptr ? sdk_->queryPort().controlSourceExclusive() : true;

  std::ostringstream oss;
  oss << "nrt profile=" << profile.name << " sdk_command=" << profile.sdk_command
      << " policy=delegate_path_planning_to_sdk moveReset_before_batch=" << (profile.requires_move_reset ? "true" : "false");

  std::string profile_reason;
  const auto plan = buildProfile(profile.name);
  const bool used_session_targets =
      (profile.name == "go_home" || profile.name == "post_scan_home") ? !session_targets_.home_joint_rad.empty()
      : (profile.name == "approach_prescan") ? session_targets_.approach_pose_valid
      : (profile.name == "align_to_entry") ? session_targets_.entry_pose_valid
      : (profile.name == "safe_retreat" || profile.name == "recovery_retreat") ? session_targets_.retreat_pose_valid
      : false;
  const bool ok = executeProfile(plan, &profile_reason);
  const bool used_config_fallback = !used_session_targets && ((profile.name == "go_home" || profile.name == "post_scan_home") ? !fallback_targets_.home_joint_rad.empty() : (profile.name == "approach_prescan") ? fallbackPoseValid(fallback_targets_.approach_pose_xyzabc) : (profile.name == "align_to_entry") ? fallbackPoseValid(fallback_targets_.entry_pose_xyzabc) : (profile.name == "safe_retreat" || profile.name == "recovery_retreat") ? fallbackPoseValid(fallback_targets_.retreat_pose_xyzabc) : false);
  snapshot_.last_result = ok ? (used_session_targets ? "executed:session_frozen_targets" : (used_config_fallback ? "executed:config_fallback_targets" : "executed:built_in_emergency_profile"))
                             : (profile_reason.empty() ? "blocked" : "blocked:" + profile_reason);
  if (reason != nullptr) {
    *reason = profile_reason.empty() ? snapshot_.last_result : profile_reason;
  }
  record(oss.str() + " result=" + snapshot_.last_result);
  return ok;
}

void NrtMotionService::record(const std::string& message) {
  snapshot_.command_count += 1;
  snapshot_.command_log.push_back(message);
  if (snapshot_.command_log.size() > 24) {
    snapshot_.command_log.erase(snapshot_.command_log.begin(), snapshot_.command_log.begin() + static_cast<long>(snapshot_.command_log.size() - 24));
  }
}

}  // namespace robot_core
