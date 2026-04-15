#pragma once

#include <map>
#include <string>
#include <vector>

#ifndef ROBOT_CORE_MAINLINE_FAMILY_KEY
#define ROBOT_CORE_MAINLINE_FAMILY_KEY "xmate3_cobot_6"
#endif
#ifndef ROBOT_CORE_DEFAULT_ROBOT_MODEL
#define ROBOT_CORE_DEFAULT_ROBOT_MODEL "xmate3"
#endif
#ifndef ROBOT_CORE_DEFAULT_ROBOT_LABEL
#define ROBOT_CORE_DEFAULT_ROBOT_LABEL "xMate3"
#endif
#ifndef ROBOT_CORE_DEFAULT_SDK_CLASS
#define ROBOT_CORE_DEFAULT_SDK_CLASS "xMateRobot"
#endif
#ifndef ROBOT_CORE_DEFAULT_AXIS_COUNT
#define ROBOT_CORE_DEFAULT_AXIS_COUNT 6
#endif
#ifndef ROBOT_CORE_DEFAULT_PREFERRED_LINK
#define ROBOT_CORE_DEFAULT_PREFERRED_LINK "wired_direct"
#endif
#ifndef ROBOT_CORE_DEFAULT_CLINICAL_MAINLINE_MODE
#define ROBOT_CORE_DEFAULT_CLINICAL_MAINLINE_MODE "cartesianImpedance"
#endif

namespace robot_core {

struct RobotFamilyDescriptor {
  std::string family_key{ROBOT_CORE_MAINLINE_FAMILY_KEY};
  std::string family_label{ROBOT_CORE_DEFAULT_ROBOT_LABEL " Clinical Mainline"};
  std::string robot_model{ROBOT_CORE_DEFAULT_ROBOT_MODEL};
  std::string sdk_robot_class{ROBOT_CORE_DEFAULT_SDK_CLASS};
  int axis_count{ROBOT_CORE_DEFAULT_AXIS_COUNT};
  bool collaborative{true};
  bool supports_xmate_model{true};
  bool supports_planner{true};
  bool supports_drag{true};
  bool supports_path_replay{true};
  bool supports_direct_torque{true};
  bool requires_single_control_source{true};
  std::string preferred_link{ROBOT_CORE_DEFAULT_PREFERRED_LINK};
  std::string clinical_rt_mode{ROBOT_CORE_DEFAULT_CLINICAL_MAINLINE_MODE};
  std::vector<std::string> supported_nrt_profiles{"go_home", "approach_prescan", "align_to_entry", "safe_retreat", "recovery_retreat", "post_scan_home"};
  std::vector<std::string> supported_rt_phases{"idle", "seek_contact", "scan_follow", "pause_hold", "controlled_retract", "fault_latched"};
  std::map<std::string, std::string> safe_defaults{{"preferred_link", ROBOT_CORE_DEFAULT_PREFERRED_LINK}, {"clinical_rt_mode", ROBOT_CORE_DEFAULT_CLINICAL_MAINLINE_MODE}, {"sdk_robot_class", ROBOT_CORE_DEFAULT_SDK_CLASS}};
};

RobotFamilyDescriptor resolveRobotFamilyDescriptor(const std::string& robot_model,
                                                  const std::string& sdk_robot_class,
                                                  int axis_count);

}  // namespace robot_core
