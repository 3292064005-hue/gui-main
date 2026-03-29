#include "robot_core/contact_gate.h"

#include <cmath>

namespace robot_core {

ContactGateDecision ContactGate::evaluate(double pressure_current, double target_pressure, int64_t stable_since_ns, int64_t now_ns) const {
  ContactGateDecision decision;
  const bool in_band = std::fabs(pressure_current - target_pressure) <= 0.05;
  if (!in_band) {
    decision.mode = "SEEKING_CONTACT";
    decision.contact_stable = false;
    return decision;
  }
  const int64_t elapsed_ns = stable_since_ns > 0 ? (now_ns - stable_since_ns) : 0;
  decision.mode = elapsed_ns >= 150000000 ? "STABLE_CONTACT" : "CONTACT_UNSTABLE";
  decision.contact_stable = elapsed_ns >= 150000000;
  return decision;
}

}  // namespace robot_core
