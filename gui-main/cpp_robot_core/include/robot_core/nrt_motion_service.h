#pragma once

#include <string>
#include <vector>

namespace robot_core {

class SdkRobotFacade;

struct NrtProfileTemplate {
  std::string name;
  std::string sdk_command;
  bool requires_auto_mode{false};
  bool requires_move_reset{true};
  bool delegates_to_sdk{true};
};

struct NrtMotionSnapshot {
  bool ready{false};
  bool degraded_without_sdk{true};
  bool executor_wrapped{true};
  bool sdk_delegation_only{true};
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
  bool goHome();
  bool approachPrescan();
  bool alignToEntry();
  bool safeRetreat();
  bool recoveryRetreat();
  bool postScanHome();
  NrtMotionSnapshot snapshot() const;

private:
  bool dispatchProfile(const NrtProfileTemplate& profile);
  NrtProfileTemplate profileTemplate(const std::string& profile) const;
  void record(const std::string& message);

  SdkRobotFacade* sdk_{nullptr};
  NrtMotionSnapshot snapshot_{};
};

}  // namespace robot_core
