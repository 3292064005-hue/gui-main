#pragma once

#include <cmath>
#include <string>
#include <stdexcept>
#include <vector>

namespace robot_core {

struct OfficialDhParameter {
  int joint{};
  double a_mm{};
  double alpha_rad{};
  double d_mm{};
  double theta_rad{};
};

struct RobotIdentityContract {
  std::string robot_model{"xmate3"};
  std::string label{"xMate3"};
  std::string sdk_robot_class{"xMateRobot"};
  int axis_count{6};
  std::string controller_series{"xCore"};
  std::string controller_version{"v2.1+"};
  std::string preferred_link{"wired_direct"};
  std::string clinical_mainline_mode{"cartesianImpedance"};
  std::vector<std::string> supported_rt_modes{"jointPosition", "cartesianPosition", "jointImpedance", "cartesianImpedance", "directTorque"};
  std::vector<std::string> clinical_allowed_modes{"MoveAbsJ", "MoveJ", "MoveL", "cartesianImpedance"};
  bool supports_xmate_model{true};
  bool supports_planner{true};
  bool supports_drag{true};
  bool supports_path_replay{true};
  bool requires_single_control_source{true};
  std::vector<double> cartesian_impedance_limits{1500.0, 1500.0, 1500.0, 100.0, 100.0, 100.0};
  std::vector<double> desired_wrench_limits{60.0, 60.0, 60.0, 30.0, 30.0, 30.0};
  std::vector<double> joint_filter_range_hz{1.0, 1000.0};
  std::vector<int> rt_network_tolerance_range{0, 100};
  std::vector<int> rt_network_tolerance_recommended{10, 20};
  std::vector<OfficialDhParameter> official_dh_parameters{};
};

inline const RobotIdentityContract& resolveRobotIdentity(
    const std::string& robot_model,
    const std::string& sdk_robot_class,
    int axis_count) {
  constexpr double kPiOver2 = 1.57079632679;
  static const RobotIdentityContract xmate3{
      "xmate3", "xMate3", "xMateRobot", 6, "xCore", "v2.1+", "wired_direct", "cartesianImpedance",
      {"jointPosition", "cartesianPosition", "jointImpedance", "cartesianImpedance", "directTorque"},
      {"MoveAbsJ", "MoveJ", "MoveL", "cartesianImpedance"},
      true, true, true, true, true,
      {1500.0, 1500.0, 1500.0, 100.0, 100.0, 100.0},
      {60.0, 60.0, 60.0, 30.0, 30.0, 30.0},
      {1.0, 1000.0}, {0, 100}, {10, 20},
      {{1, 0.0, -kPiOver2, 341.5, 0.0}, {2, 394.0, 0.0, 0.0, 0.0}, {3, 0.0, kPiOver2, 0.0, 0.0},
       {4, 0.0, -kPiOver2, 366.0, 0.0}, {5, 0.0, kPiOver2, 0.0, 0.0}, {6, 0.0, 0.0, 250.3, 0.0}}};
  if ((!robot_model.empty() && robot_model != xmate3.robot_model) ||
      (!sdk_robot_class.empty() && sdk_robot_class != xmate3.sdk_robot_class) ||
      (axis_count > 0 && axis_count != xmate3.axis_count)) {
    throw std::invalid_argument("xMateRobot-only mainline requires xmate3/xMateRobot/6");
  }
  return xmate3;
}

inline bool vectorWithinLimits(const std::vector<double>& values, const std::vector<double>& limits) {
  if (values.size() != limits.size()) {
    return false;
  }
  for (std::size_t idx = 0; idx < values.size(); ++idx) {
    if (std::abs(values[idx]) > limits[idx]) {
      return false;
    }
  }
  return true;
}

}  // namespace robot_core
