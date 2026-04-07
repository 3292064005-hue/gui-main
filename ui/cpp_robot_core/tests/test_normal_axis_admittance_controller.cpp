#include "robot_core/normal_axis_admittance_controller.h"

#include <cassert>

int main() {
  robot_core::NormalAxisAdmittanceController controller;
  robot_core::AdmittanceControllerConfig cfg;
  cfg.virtual_mass = 0.8;
  cfg.virtual_damping = 120.0;
  cfg.virtual_stiffness = 40.0;
  cfg.max_step_mm = 0.08;
  cfg.max_velocity_mm_s = 2.0;
  cfg.max_acceleration_mm_s2 = 30.0;
  cfg.max_displacement_mm = 8.0;
  controller.configure(cfg);

  const auto idle = controller.step(8.0, 8.0, 0.001);
  assert(idle.delta_normal_m == 0.0);
  assert(idle.state.force_error_n == 0.0);

  const auto step = controller.step(8.0, 6.0, 0.001);
  assert(step.state.force_error_n > 0.0);
  assert(step.delta_normal_m >= 0.0);

  robot_core::AdmittanceControllerConfig limited = cfg;
  limited.max_step_mm = 0.01;
  controller.configure(limited);
  controller.reset();
  const auto saturated = controller.step(20.0, 0.0, 0.001);
  assert(saturated.delta_normal_m <= 0.00001 + 1e-9);

  controller.reset();
  const auto reset = controller.state();
  assert(reset.x_m == 0.0);
  assert(reset.v_m_s == 0.0);
  return 0;
}
