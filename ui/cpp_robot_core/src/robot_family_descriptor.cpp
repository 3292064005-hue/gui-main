#include "robot_core/robot_family_descriptor.h"

#include "robot_core/robot_identity_contract.h"

namespace robot_core {

RobotFamilyDescriptor resolveRobotFamilyDescriptor(const std::string& robot_model,
                                                  const std::string& sdk_robot_class,
                                                  int axis_count) {
  const auto& identity = resolveRobotIdentity(robot_model, sdk_robot_class, axis_count);
  RobotFamilyDescriptor descriptor;
  descriptor.robot_model = identity.robot_model;
  descriptor.sdk_robot_class = identity.sdk_robot_class;
  descriptor.axis_count = identity.axis_count;
  descriptor.supports_xmate_model = identity.supports_xmate_model;
  descriptor.supports_planner = identity.supports_planner;
  descriptor.supports_drag = identity.supports_drag;
  descriptor.supports_path_replay = identity.supports_path_replay;
  descriptor.supports_direct_torque = true;
  descriptor.requires_single_control_source = identity.requires_single_control_source;
  descriptor.preferred_link = identity.preferred_link;
  descriptor.clinical_rt_mode = identity.clinical_mainline_mode;
  descriptor.safe_defaults = {
      {"preferred_link", descriptor.preferred_link},
      {"clinical_rt_mode", descriptor.clinical_rt_mode},
      {"single_control_source", descriptor.requires_single_control_source ? "true" : "false"},
      {"sdk_robot_class", descriptor.sdk_robot_class},
  };
  return descriptor;
}

}  // namespace robot_core
