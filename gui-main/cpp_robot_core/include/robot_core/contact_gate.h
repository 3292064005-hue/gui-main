#pragma once

#include <cstdint>
#include <string>

namespace robot_core {

struct ContactGateDecision {
  std::string mode{"NO_CONTACT"};
  bool contact_stable{false};
};

class ContactGate {
public:
  ContactGateDecision evaluate(double pressure_current, double target_pressure, int64_t stable_since_ns, int64_t now_ns) const;
};

}  // namespace robot_core
