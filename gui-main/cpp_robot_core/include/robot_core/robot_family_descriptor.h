#pragma once

#include <map>
#include <string>
#include <vector>

#include "robot_core/robot_identity_contract.h"

namespace robot_core {

struct RobotFamilyDescriptor {
  std::string family_key{"xmate_6_collaborative"};
  std::string family_label{"xMate collaborative 6-axis"};
  std::string robot_model{"xmate3"};
  std::string sdk_robot_class{"xMateRobot"};
  int axis_count{6};
  bool collaborative{true};
  bool supports_xmate_model{true};
  bool supports_planner{true};
  bool supports_drag{true};
  bool supports_path_replay{true};
  bool supports_direct_torque{true};
  bool requires_single_control_source{true};
  std::string preferred_link{"wired_direct"};
  std::string clinical_rt_mode{"cartesianImpedance"};
  std::vector<std::string> supported_nrt_profiles{"go_home", "approach_prescan", "align_to_entry", "safe_retreat", "recovery_retreat", "post_scan_home"};
  std::vector<std::string> supported_rt_phases{"idle", "seek_contact", "contact_stabilize", "scan_follow", "pause_hold", "controlled_retract", "fault_latched"};
  std::map<std::string, std::string> safe_defaults{{"preferred_link", "wired_direct"}, {"clinical_rt_mode", "cartesianImpedance"}};
};

RobotFamilyDescriptor resolveRobotFamilyDescriptor(const std::string& robot_model,
                                                  const std::string& sdk_robot_class,
                                                  int axis_count);

}  // namespace robot_core
