#pragma once

#include <string>
#include <vector>

#include "robot_core/runtime_types.h"

namespace robot_core {

class SdkRobotFacade;

struct ModelAuthoritySnapshot {
  std::string authority_source{"cpp_robot_core"};
  std::string runtime_source{"simulated_contract"};
  std::string family_key{"xmate_6_collaborative"};
  std::string family_label{"xMate collaborative 6-axis"};
  std::string robot_model{"xmate3"};
  std::string sdk_robot_class{"xMateRobot"};
  bool planner_supported{true};
  bool xmate_model_supported{true};
  bool authoritative_precheck{false};
  bool authoritative_runtime{false};
  bool approximate_advisory_allowed{true};
  std::vector<std::string> planner_primitives{"JointMotionGenerator", "CartMotionGenerator", "FollowPosition"};
  std::vector<std::string> model_methods{"robot.model()", "getCartPose", "getJointPos", "jacobian", "getTorque"};
  std::vector<std::string> warnings;
};

class ModelAuthority {
public:
  ModelAuthority() = default;
  ModelAuthoritySnapshot snapshot(const RuntimeConfig& config, const SdkRobotFacade& sdk) const;
};

}  // namespace robot_core
