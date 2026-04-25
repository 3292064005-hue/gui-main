#pragma once

#include <string>

namespace robot_core {

/**
 * @brief Input bundle for normal-force estimation.
 *
 * The estimator fuses the pressure channel and the wrench-derived normal force
 * into one contact-force value used by the project-side admittance loop.
 */
struct NormalForceEstimatorInput {
  double pressure_force_n{0.0};
  bool pressure_valid{false};
  double pressure_age_ms{0.0};
  double wrench_force_n{0.0};
  bool wrench_valid{false};
  double wrench_age_ms{0.0};
  double contact_direction_sign{1.0};
};

/**
 * @brief Configuration of the normal-force estimator.
 */
struct NormalForceEstimatorConfig {
  std::string preferred_source{"fused"};
  double pressure_weight{0.7};
  double wrench_weight{0.3};
  double stale_timeout_ms{100.0};
  double timeout_ms{250.0};
  bool auto_bias_zero{true};
  double min_confidence{0.4};
};

/**
 * @brief Estimated normal-force state exported to controllers and telemetry.
 */
struct NormalForceEstimate {
  double estimated_force_n{0.0};
  double bias_compensated_force_n{0.0};
  double pressure_force_n{0.0};
  double wrench_force_n{0.0};
  std::string source{"invalid"};
  double confidence{0.0};
  bool stale{true};
  bool valid{false};
};

/**
 * @brief Project-side normal-force estimator used by the admittance loop.
 *
 * The estimator never writes robot commands. It only fuses sensor observations
 * and reports a single force estimate with explicit source/confidence labels.
 */
class NormalForceEstimator {
public:
  NormalForceEstimator() = default;

  /**
   * @brief Update estimator configuration.
   * @param config New estimator configuration.
   * @return None.
   * @throws No exceptions are thrown.
   * @boundary Non-physical weights are clamped to safe defaults.
   */
  void configure(const NormalForceEstimatorConfig& config);

  /**
   * @brief Estimate the current normal force.
   * @param input Pressure/wrench input bundle.
   * @return Estimated normal-force state.
   * @throws No exceptions are thrown.
   * @boundary Invalid or stale sources yield valid=false and source="invalid".
   */
  NormalForceEstimate estimate(const NormalForceEstimatorInput& input);

  /**
   * @brief Reset the estimator bias and last estimate.
   * @return None.
   * @throws No exceptions are thrown.
   * @boundary Safe to call between RT phases.
   */
  void reset();

  const NormalForceEstimatorConfig& config() const { return state_store_.config; }
  const NormalForceEstimate& lastEstimate() const { return last_estimate_; }

private:
  struct LocalStateStore {
    NormalForceEstimatorConfig config{};
  };
  LocalStateStore state_store_{};
  double bias_n_{0.0};
  NormalForceEstimate last_estimate_{};
};

}  // namespace robot_core
