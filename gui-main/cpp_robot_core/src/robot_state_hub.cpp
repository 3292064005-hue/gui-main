#include "robot_core/robot_state_hub.h"
namespace robot_core {
void RobotStateHub::update(const RobotStateSnapshot& s) { latest_ = s; }
RobotStateSnapshot RobotStateHub::latest() const { return latest_; }
}
