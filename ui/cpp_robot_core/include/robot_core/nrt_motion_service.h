#pragma once

#include <string>
#include <vector>

#include "robot_core/runtime_types.h"

namespace robot_core {

class SdkRobotFacade;

enum class NrtCommandType {
  MoveAbsJ,
  MoveJ,
  MoveL,
  MoveC,
};

struct NrtMotionPlanStep {
  NrtCommandType command_type{NrtCommandType::MoveL};
  std::vector<double> target_joint_rad;
  std::vector<double> target_tcp_xyzabc_m_rad;
  int speed_mm_s{200};
  int zone_mm{0};
  bool forced_conf{false};
  bool requires_move_reset{true};
};

struct NrtMotionPlan {
  std::string profile_name;
  std::string sdk_command;
  bool requires_auto_mode{false};
  bool requires_move_reset{true};
  std::vector<NrtMotionPlanStep> steps;
};

struct NrtProfileTemplate {
  std::string name;
  std::string sdk_command;
  bool requires_auto_mode{false};
  bool requires_move_reset{true};
  bool delegates_to_sdk{true};
};

struct NrtFallbackTargets {
  std::vector<double> home_joint_rad;
  std::vector<double> approach_pose_xyzabc;
  std::vector<double> entry_pose_xyzabc;
  std::vector<double> retreat_pose_xyzabc;
};

struct NrtSessionTargets {
  std::vector<double> home_joint_rad;
  ScanWaypoint approach_pose{};
  ScanWaypoint entry_pose{};
  ScanWaypoint retreat_pose{};
  bool approach_pose_valid{false};
  bool entry_pose_valid{false};
  bool retreat_pose_valid{false};
};

struct NrtMotionSnapshot {
  bool ready{false};
  bool degraded_without_sdk{true};
  bool executor_wrapped{true};
  bool sdk_delegation_only{false};
  bool requires_move_reset{true};
  bool requires_single_control_source{true};
  int command_count{0};
  std::string active_profile{"idle"};
  std::string last_command{""};
  std::string last_command_id{""};
  std::string last_result{"boot"};
  std::vector<std::string> blocking_profiles;
  std::vector<NrtProfileTemplate> templates;
  std::vector<std::string> command_log;
};

class NrtMotionService {
public:
  explicit NrtMotionService(SdkRobotFacade* sdk = nullptr);

  void bind(SdkRobotFacade* sdk);
  /**
   * @brief Configure session-frozen NRT targets used by bring-up/retreat profiles.
   * @param targets Session-owned home/approach/entry/retreat targets.
   * @return void
   * @throws No exceptions are thrown.
   * @boundary Replaces hard-coded NRT business poses with session-frozen plan/profile targets.
   */
  void configureSessionTargets(const NrtSessionTargets& targets);
  void configureFallbackTargets(const NrtFallbackTargets& targets);
  /**
   * @brief Clear any previously bound session-frozen NRT targets.
   * @return void
   * @throws No exceptions are thrown.
   * @boundary Forces subsequent NRT profile execution to use only emergency fallback profiles.
   */
  void clearSessionTargets();
  bool goHome(std::string* reason = nullptr);
  bool approachPrescan(std::string* reason = nullptr);
  bool alignToEntry(std::string* reason = nullptr);
  bool safeRetreat(std::string* reason = nullptr);
  bool recoveryRetreat(std::string* reason = nullptr);
  bool postScanHome(std::string* reason = nullptr);
  NrtMotionSnapshot snapshot() const;

private:
  NrtMotionPlan buildProfile(const std::string& profile_name) const;
  bool executeProfile(const NrtMotionPlan& plan, std::string* reason = nullptr);
  bool dispatchProfile(const NrtProfileTemplate& profile, std::string* reason = nullptr);
  NrtProfileTemplate profileTemplate(const std::string& profile) const;
  void record(const std::string& message);

  SdkRobotFacade* sdk_{nullptr};
  NrtMotionSnapshot snapshot_{};
  NrtSessionTargets session_targets_{};
  NrtFallbackTargets fallback_targets_{};
};

}  // namespace robot_core
