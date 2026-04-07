#pragma once

#include <string>

namespace robot_core {

struct RecoveryDecision {
  std::string state{"IDLE"};
  std::string reason;
  std::string action;
  std::string severity{"LEVEL_0_MONITOR"};
};

class RecoveryPolicy {
public:
  RecoveryDecision evaluate(double pressure_current, double pressure_target, double pressure_upper, double sensor_age_ms) const;
};

}  // namespace robot_core
