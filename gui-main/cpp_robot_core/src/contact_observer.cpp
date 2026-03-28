#include "robot_core/contact_observer.h"
namespace robot_core {
ContactState ContactObserver::evaluate(const ContactObservationInput& input) const {
  ContactState s;
  if (input.external_pressure > 2.4 || input.cart_force_z > 2.4) {
    s.mode = "OVERPRESSURE";
    s.recommended_action = "CONTROLLED_RETRACT";
  } else if (input.quality_score < 0.65) {
    s.mode = "UNSTABLE_CONTACT";
    s.recommended_action = "PAUSE_AND_HOLD";
  } else {
    s.mode = "STABLE_CONTACT";
    s.recommended_action = "SCAN";
  }
  s.confidence = 0.8;
  return s;
}
}
