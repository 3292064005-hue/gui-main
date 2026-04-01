#include "robot_core/robot_family_descriptor.h"

namespace robot_core {

RobotFamilyDescriptor resolveRobotFamilyDescriptor(const std::string& robot_model,
                                                  const std::string& sdk_robot_class,
                                                  int axis_count) {
  const auto identity = resolveRobotIdentity(robot_model, sdk_robot_class, axis_count);
  RobotFamilyDescriptor descriptor;
  descriptor.robot_model = identity.robot_model;
  descriptor.sdk_robot_class = identity.sdk_robot_class;
  descriptor.axis_count = identity.axis_count;
  descriptor.supports_xmate_model = identity.supports_xmate_model;
  descriptor.supports_planner = identity.supports_planner;
  descriptor.supports_drag = identity.supports_drag;
  descriptor.supports_path_replay = identity.supports_path_replay;
  descriptor.supports_direct_torque = false;
  for (const auto& mode : identity.supported_rt_modes) {
    if (mode == "directTorque") {
      descriptor.supports_direct_torque = true;
      break;
    }
  }
  descriptor.requires_single_control_source = identity.requires_single_control_source;
  descriptor.preferred_link = identity.preferred_link;
  descriptor.clinical_rt_mode = identity.clinical_mainline_mode;
  descriptor.collaborative = identity.supports_drag || identity.supports_path_replay;
  descriptor.supported_nrt_profiles = {"go_home", "approach_prescan", "align_to_entry", "safe_retreat", "recovery_retreat", "post_scan_home"};
  descriptor.supported_rt_phases = {"idle", "seek_contact", "contact_stabilize", "scan_follow", "pause_hold", "controlled_retract", "fault_latched"};
  if (identity.axis_count == 7) {
    descriptor.family_key = "xmate_7_collaborative";
    descriptor.family_label = "xMate collaborative 7-axis";
  } else if (identity.sdk_robot_class == "StandardRobot") {
    descriptor.family_key = "standard_6_industrial";
    descriptor.family_label = "Standard industrial 6-axis";
  } else {
    descriptor.family_key = "xmate_6_collaborative";
    descriptor.family_label = "xMate collaborative 6-axis";
  }
  descriptor.safe_defaults = {
      {"preferred_link", descriptor.preferred_link},
      {"clinical_rt_mode", descriptor.clinical_rt_mode},
      {"single_control_source", descriptor.requires_single_control_source ? "true" : "false"},
  };
  return descriptor;
}

}  // namespace robot_core
