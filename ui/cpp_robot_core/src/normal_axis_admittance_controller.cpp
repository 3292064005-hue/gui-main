#include "robot_core/normal_axis_admittance_controller.h"

#include <algorithm>
#include <cmath>

namespace robot_core {

namespace {

double mmToM(double value_mm) { return value_mm / 1000.0; }

double clampSigned(double value, double magnitude) {
  return std::max(-std::abs(magnitude), std::min(std::abs(magnitude), value));
}

}  // namespace

void NormalAxisAdmittanceController::configure(const AdmittanceControllerConfig& config) {
  state_store_.config = config;
  state_store_.config.virtual_mass = std::max(0.05, config.virtual_mass);
  state_store_.config.virtual_damping = std::max(0.0, config.virtual_damping);
  state_store_.config.virtual_stiffness = std::max(0.0, config.virtual_stiffness);
  state_store_.config.max_step_mm = std::max(0.01, config.max_step_mm);
  state_store_.config.max_velocity_mm_s = std::max(0.01, config.max_velocity_mm_s);
  state_store_.config.max_acceleration_mm_s2 = std::max(0.1, config.max_acceleration_mm_s2);
  state_store_.config.max_displacement_mm = std::max(state_store_.config.max_step_mm, config.max_displacement_mm);
  state_store_.config.force_deadband_n = std::max(0.0, config.force_deadband_n);
  state_store_.config.integrator_limit_n = std::max(0.1, config.integrator_limit_n);
  state_store_.config.integrator_leak = std::clamp(config.integrator_leak, 0.0, 1.0);
}

AdmittanceCommand NormalAxisAdmittanceController::step(double force_target_n, double force_measured_n, double dt_s) {
  AdmittanceCommand output{};
  if (dt_s <= 0.0) {
    output.delta_normal_m = state_.last_cmd_m;
    output.state = state_;
    return output;
  }

  double force_error = force_target_n - force_measured_n;
  if (std::abs(force_error) < state_store_.config.force_deadband_n) {
    force_error = 0.0;
  }

  state_.integrator_n = (1.0 - state_store_.config.integrator_leak) * state_.integrator_n + force_error * dt_s;
  state_.integrator_n = clampSigned(state_.integrator_n, state_store_.config.integrator_limit_n);

  const double damping = state_store_.config.virtual_damping * state_.v_m_s;
  const double spring = state_store_.config.virtual_stiffness * state_.x_m;
  const double accel = (force_error + state_.integrator_n - damping - spring) / state_store_.config.virtual_mass;
  const double accel_limit = mmToM(state_store_.config.max_acceleration_mm_s2);
  state_.a_m_s2 = clampSigned(accel, accel_limit);

  state_.v_m_s += state_.a_m_s2 * dt_s;
  state_.v_m_s = clampSigned(state_.v_m_s, mmToM(state_store_.config.max_velocity_mm_s));

  const double raw_step = state_.v_m_s * dt_s;
  const double step_limit = mmToM(state_store_.config.max_step_mm);
  const double cmd = clampSigned(raw_step, step_limit);
  state_.x_m += cmd;
  const double displacement_limit = mmToM(state_store_.config.max_displacement_mm);
  state_.saturated = std::abs(state_.x_m) >= displacement_limit || std::abs(cmd) >= step_limit;
  state_.x_m = clampSigned(state_.x_m, displacement_limit);
  state_.last_cmd_m = cmd;
  state_.force_error_n = force_error;
  state_.damping_term = damping;
  state_.spring_term = spring;

  output.delta_normal_m = cmd;
  output.state = state_;
  return output;
}

void NormalAxisAdmittanceController::reset() {
  state_ = {};
}

}  // namespace robot_core
