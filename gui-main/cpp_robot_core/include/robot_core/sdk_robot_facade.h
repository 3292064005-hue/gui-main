#pragma once

#include <array>
#include <cstddef>
#include <string>
#include <vector>

namespace robot_core {

struct SdkRobotRuntimeConfig {
  std::string remote_ip{"192.168.0.160"};
  std::string local_ip{"192.168.0.100"};
  int axis_count{6};
  int rt_network_tolerance_percent{15};
  double joint_filter_hz{40.0};
  double cart_filter_hz{30.0};
  double torque_filter_hz{25.0};
  std::array<double, 6> cartesian_impedance{{2200.0, 2200.0, 1400.0, 45.0, 45.0, 35.0}};
  std::array<double, 6> desired_wrench_n{{0.0, 0.0, 8.0, 0.0, 0.0, 0.0}};
  std::array<double, 16> fc_frame_matrix{{1.0, 0.0, 0.0, 0.0,
                                          0.0, 1.0, 0.0, 0.0,
                                          0.0, 0.0, 1.0, 0.0,
                                          0.0, 0.0, 0.0, 1.0}};
  std::array<double, 16> tcp_frame_matrix{{1.0, 0.0, 0.0, 0.0,
                                           0.0, 1.0, 0.0, 0.0,
                                           0.0, 0.0, 1.0, 62.0,
                                           0.0, 0.0, 0.0, 1.0}};
  std::array<double, 3> load_com_mm{{0.0, 0.0, 62.0}};
  std::array<double, 6> load_inertia{{0.0012, 0.0012, 0.0008, 0.0, 0.0, 0.0}};
};

class SdkRobotFacade {
public:
  SdkRobotFacade();
  ~SdkRobotFacade();

  bool connect(const std::string& remote_ip, const std::string& local_ip);
  void disconnect();
  bool setPower(bool on);
  bool setAutoMode();
  bool setManualMode();
  bool configureRtMainline(const SdkRobotRuntimeConfig& config);
  bool connected() const;
  std::vector<double> jointPos() const;
  std::vector<double> jointVel() const;
  std::vector<double> jointTorque() const;
  std::vector<double> tcpPose() const;
  std::vector<std::string> configurationLog() const;

private:
  static std::vector<double> zeroVector(std::size_t count);

  bool connected_{false};
  bool powered_{false};
  bool auto_mode_{false};
  SdkRobotRuntimeConfig rt_config_{};
  std::vector<double> joint_pos_;
  std::vector<double> joint_vel_;
  std::vector<double> joint_torque_;
  std::vector<double> tcp_pose_;
  std::vector<std::string> configuration_log_;
};

}  // namespace robot_core
