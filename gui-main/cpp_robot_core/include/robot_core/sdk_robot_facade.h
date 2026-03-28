#pragma once
#include <string>
#include <vector>
namespace robot_core {
class SdkRobotFacade {
public:
  bool connect(const std::string& remote_ip, const std::string& local_ip);
  void disconnect();
  bool setPower(bool on);
  bool setAutoMode();
  bool setManualMode();
  std::vector<double> jointPos() const;
  std::vector<double> jointVel() const;
  std::vector<double> jointTorque() const;
  std::vector<double> tcpPose() const;
};
}
