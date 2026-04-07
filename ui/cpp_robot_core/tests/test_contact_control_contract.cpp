#include "robot_core/contact_control_contract.h"
#include "robot_core/sdk_robot_facade.h"

#include <cassert>

int main() {
  robot_core::SdkRobotRuntimeConfig cfg;
  cfg.contact_force_target_n = 8.0;
  cfg.contact_force_tolerance_n = 1.0;
  cfg.scan_force_target_n = 8.0;
  cfg.scan_force_tolerance_n = 1.0;
  cfg.seek_contact_max_step_mm = 0.08;
  cfg.seek_contact_max_travel_mm = 8.0;
  cfg.rt_max_cart_step_mm = 0.25;
  cfg.rt_max_cart_vel_mm_s = 25.0;
  cfg.rt_max_cart_acc_mm_s2 = 200.0;
  cfg.rt_integrator_limit_n = 10.0;
  cfg.pause_hold_integrator_leak = 0.02;
  cfg.scan_tangent_speed_min_mm_s = 2.0;
  cfg.scan_tangent_speed_max_mm_s = 12.0;
  cfg.scan_follow_lateral_amplitude_mm = 0.5;
  cfg.scan_follow_frequency_hz = 0.25;
  cfg.scan_pose_trim_gain = 0.08;
  cfg.rt_max_pose_trim_deg = 1.5;
  cfg.force_estimator.stale_timeout_ms = 100;
  cfg.contact_control.virtual_mass = 0.9;
  cfg.contact_control.virtual_damping = 130.0;
  cfg.contact_control.virtual_stiffness = 45.0;
  cfg.force_estimator.preferred_source = "fused";
  cfg.orientation_trim.gain = 0.08;

  const auto contract = robot_core::buildContactControlContract(cfg);
  assert(contract.mode == "normal_axis_admittance");
  assert(contract.seek_contact_admittance.virtual_mass == 0.9);
  assert(contract.force_estimator.preferred_source == "fused");

  std::string reason;
  assert(robot_core::validateContactControlContract(contract, &reason));

  auto invalid = contract;
  invalid.seek_contact_admittance.virtual_mass = 0.0;
  assert(!robot_core::validateContactControlContract(invalid, &reason));
  assert(reason == "invalid_contact_control_mass");

  invalid = contract;
  invalid.force_estimator.preferred_source = "bad";
  assert(!robot_core::validateContactControlContract(invalid, &reason));
  assert(reason == "invalid_force_estimator_contract");

  invalid = contract;
  invalid.orientation_trim.max_trim_deg = 0.0;
  assert(!robot_core::validateContactControlContract(invalid, &reason));
  assert(reason == "invalid_contact_control_trim");
  return 0;
}
