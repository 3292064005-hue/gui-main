#include "robot_core/sdk_robot_facade.h"
#ifdef ROBOT_CORE_WITH_XCORE_SDK
#include "rokae/robot.h"
#endif
namespace robot_core {
bool SdkRobotFacade::connect(const std::string&, const std::string&) { return true; }
void SdkRobotFacade::disconnect() {}
bool SdkRobotFacade::setPower(bool) { return true; }
bool SdkRobotFacade::setAutoMode() { return true; }
bool SdkRobotFacade::setManualMode() { return true; }
std::vector<double> SdkRobotFacade::jointPos() const { return std::vector<double>(7, 0.0); }
std::vector<double> SdkRobotFacade::jointVel() const { return std::vector<double>(7, 0.0); }
std::vector<double> SdkRobotFacade::jointTorque() const { return std::vector<double>(7, 0.0); }
std::vector<double> SdkRobotFacade::tcpPose() const { return std::vector<double>(6, 0.0); }
}
