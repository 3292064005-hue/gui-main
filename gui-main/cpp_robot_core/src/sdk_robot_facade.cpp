#include "robot_core/sdk_robot_facade.h"

#ifdef ROBOT_CORE_WITH_XCORE_SDK
#include "rokae/robot.h"
#endif

#include <algorithm>
#include <sstream>

namespace robot_core {

SdkRobotFacade::SdkRobotFacade()
    : joint_pos_(zeroVector(6)),
      joint_vel_(zeroVector(6)),
      joint_torque_(zeroVector(6)),
      tcp_pose_(zeroVector(6)) {}

SdkRobotFacade::~SdkRobotFacade() = default;

bool SdkRobotFacade::connect(const std::string& remote_ip, const std::string& local_ip) {
  connected_ = !remote_ip.empty() && !local_ip.empty();
  rt_config_.remote_ip = remote_ip;
  rt_config_.local_ip = local_ip;
  configuration_log_.push_back("connectToRobot(" + remote_ip + "," + local_ip + ")");
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  // Real SDK integration is expected to instantiate rokae::xMateRobot here.
#endif
  return connected_;
}

void SdkRobotFacade::disconnect() {
  connected_ = false;
  powered_ = false;
  auto_mode_ = false;
  joint_pos_ = zeroVector(6);
  joint_vel_ = zeroVector(6);
  joint_torque_ = zeroVector(6);
  tcp_pose_ = zeroVector(6);
  configuration_log_.push_back("disconnectFromRobot()");
}

bool SdkRobotFacade::setPower(bool on) {
  if (!connected_) {
    return false;
  }
  powered_ = on;
  configuration_log_.push_back(std::string("setPowerState(") + (on ? "on" : "off") + ")");
  return true;
}

bool SdkRobotFacade::setAutoMode() {
  if (!connected_) {
    return false;
  }
  auto_mode_ = true;
  configuration_log_.push_back("setOperateMode(auto)");
  return true;
}

bool SdkRobotFacade::setManualMode() {
  if (!connected_) {
    return false;
  }
  auto_mode_ = false;
  configuration_log_.push_back("setOperateMode(manual)");
  return true;
}

bool SdkRobotFacade::configureRtMainline(const SdkRobotRuntimeConfig& config) {
  if (!connected_ || !powered_ || !auto_mode_) {
    return false;
  }
  rt_config_ = config;
  std::ostringstream oss;
  oss << "configureRtMainline(rt_network_tolerance=" << config.rt_network_tolerance_percent
      << ", joint_filter_hz=" << config.joint_filter_hz
      << ", cart_filter_hz=" << config.cart_filter_hz
      << ", torque_filter_hz=" << config.torque_filter_hz
      << ", axis_count=" << config.axis_count << ")";
  configuration_log_.push_back(oss.str());
  joint_pos_ = zeroVector(static_cast<std::size_t>(std::max(1, config.axis_count)));
  joint_vel_ = zeroVector(joint_pos_.size());
  joint_torque_ = zeroVector(joint_pos_.size());
  tcp_pose_ = {0.0, 0.0, 240.0, 180.0, 0.0, 90.0};
  return config.axis_count == 6;
}

bool SdkRobotFacade::connected() const { return connected_; }

std::vector<double> SdkRobotFacade::jointPos() const { return joint_pos_; }
std::vector<double> SdkRobotFacade::jointVel() const { return joint_vel_; }
std::vector<double> SdkRobotFacade::jointTorque() const { return joint_torque_; }
std::vector<double> SdkRobotFacade::tcpPose() const { return tcp_pose_; }
std::vector<std::string> SdkRobotFacade::configurationLog() const { return configuration_log_; }

std::vector<double> SdkRobotFacade::zeroVector(std::size_t count) {
  return std::vector<double>(count, 0.0);
}

}  // namespace robot_core
