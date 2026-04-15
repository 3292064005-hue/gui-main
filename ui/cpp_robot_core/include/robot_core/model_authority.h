#pragma once

#include <string>
#include <vector>

#include "robot_core/runtime_types.h"

#ifndef ROBOT_CORE_MAINLINE_FAMILY_KEY
#define ROBOT_CORE_MAINLINE_FAMILY_KEY "xmate3_cobot_6"
#endif
#ifndef ROBOT_CORE_DEFAULT_ROBOT_LABEL
#define ROBOT_CORE_DEFAULT_ROBOT_LABEL "xMate3"
#endif

namespace robot_core {

class SdkRobotFacade;

struct ModelAuthoritySnapshot {
  std::string authority_source{"cpp_robot_core"};
  std::string runtime_source{"simulated_contract"};
  std::string family_key{ROBOT_CORE_MAINLINE_FAMILY_KEY};
  std::string family_label{ROBOT_CORE_DEFAULT_ROBOT_LABEL " collaborative 6-axis"};
  std::string robot_model{ROBOT_CORE_DEFAULT_ROBOT_MODEL};
  std::string sdk_robot_class{ROBOT_CORE_DEFAULT_SDK_CLASS};
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
  bool validateRtPhaseTargetDelta(const RuntimeConfig& config, const SdkRobotFacade& sdk, std::string* reason = nullptr) const;
  bool validateRtPhaseWorkspace(const RuntimeConfig& config, const SdkRobotFacade& sdk, std::string* reason = nullptr) const;
  bool validateRtPhaseSingularityMargin(const RuntimeConfig& config, const SdkRobotFacade& sdk, std::string* reason = nullptr) const;
};

}  // namespace robot_core
