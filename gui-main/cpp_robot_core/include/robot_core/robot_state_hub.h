#pragma once
#include "robot_core/runtime_types.h"
namespace robot_core {
class RobotStateHub {
public:
  void update(const RobotStateSnapshot& s);
  RobotStateSnapshot latest() const;
private:
  RobotStateSnapshot latest_{};
};
}
