#pragma once

namespace robot_core {

/**
 * @brief State of the normal-axis admittance controller.
 */
struct AdmittanceState {
  double x_m{0.0};
  double v_m_s{0.0};
  double a_m_s2{0.0};
  double force_error_n{0.0};
  double damping_term{0.0};
  double spring_term{0.0};
  double integrator_n{0.0};
  double last_cmd_m{0.0};
  bool saturated{false};
};

/**
 * @brief Configuration of the normal-axis admittance controller.
 */
struct AdmittanceControllerConfig {
  double virtual_mass{0.8};
  double virtual_damping{120.0};
  double virtual_stiffness{40.0};
  double max_step_mm{0.08};
  double max_velocity_mm_s{2.0};
  double max_acceleration_mm_s2{30.0};
  double max_displacement_mm{8.0};
  double force_deadband_n{0.3};
  double integrator_limit_n{10.0};
  double integrator_leak{0.02};
};

/**
 * @brief One-step command returned by the admittance controller.
 */
struct AdmittanceCommand {
  double delta_normal_m{0.0};
  AdmittanceState state{};
};

/**
 * @brief Project-side normal-axis admittance controller.
 */
class NormalAxisAdmittanceController {
public:
  void configure(const AdmittanceControllerConfig& config);

  /**
   * @brief Advance the admittance controller by one cycle.
   * @param force_target_n Desired normal force.
   * @param force_measured_n Estimated normal force.
   * @param dt_s Loop period in seconds.
   * @return One-step normal-axis position correction.
   * @throws No exceptions are thrown.
   * @boundary dt_s<=0 returns the previous state without advancing.
   */
  AdmittanceCommand step(double force_target_n, double force_measured_n, double dt_s);

  /**
   * @brief Reset dynamic state.
   * @return None.
   */
  void reset();

  const AdmittanceControllerConfig& config() const { return state_store_.config; }
  const AdmittanceState& state() const { return state_; }

private:
  struct LocalStateStore {
    AdmittanceControllerConfig config{};
  };
  LocalStateStore state_store_{};
  AdmittanceState state_{};
};

}  // namespace robot_core
