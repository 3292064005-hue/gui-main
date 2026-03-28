#pragma once
#include <string>
namespace robot_core {
struct ContactObservationInput {
  double cart_force_z{0.0};
  double joint_torque_trend{0.0};
  double external_pressure{0.0};
  double quality_score{0.0};
};
struct ContactState {
  std::string mode{"NO_CONTACT"};
  double confidence{0.0};
  std::string recommended_action{"IDLE"};
};
class ContactObserver {
public:
  ContactState evaluate(const ContactObservationInput& input) const;
};
}
