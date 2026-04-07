#include "robot_core/normal_force_estimator.h"

#include <cassert>

int main() {
  robot_core::NormalForceEstimator estimator;
  robot_core::NormalForceEstimatorConfig cfg;
  cfg.pressure_weight = 0.7;
  cfg.wrench_weight = 0.3;
  cfg.stale_timeout_ms = 100.0;
  cfg.timeout_ms = 250.0;
  estimator.configure(cfg);

  robot_core::NormalForceEstimatorInput fused{};
  fused.pressure_force_n = 9.0;
  fused.pressure_valid = true;
  fused.pressure_age_ms = 5.0;
  fused.wrench_force_n = 7.0;
  fused.wrench_valid = true;
  fused.wrench_age_ms = 5.0;
  const auto estimate = estimator.estimate(fused);
  assert(estimate.valid);
  assert(estimate.source == "fused");
  assert(estimate.estimated_force_n > 7.5 && estimate.estimated_force_n < 8.5);

  robot_core::NormalForceEstimatorInput pressure_only{};
  pressure_only.pressure_force_n = 6.0;
  pressure_only.pressure_valid = true;
  pressure_only.pressure_age_ms = 10.0;
  const auto pressure_est = estimator.estimate(pressure_only);
  assert(pressure_est.valid);
  assert(pressure_est.source == "pressure");

  robot_core::NormalForceEstimatorConfig prefer_wrench_cfg = cfg;
  prefer_wrench_cfg.preferred_source = "wrench";
  estimator.configure(prefer_wrench_cfg);
  const auto prefer_wrench = estimator.estimate(fused);
  assert(prefer_wrench.valid);
  assert(prefer_wrench.source == "wrench");
  assert(prefer_wrench.estimated_force_n == fused.wrench_force_n);

  robot_core::NormalForceEstimatorConfig prefer_pressure_cfg = cfg;
  prefer_pressure_cfg.preferred_source = "pressure";
  estimator.configure(prefer_pressure_cfg);
  const auto prefer_pressure = estimator.estimate(fused);
  assert(prefer_pressure.valid);
  assert(prefer_pressure.source == "pressure");

  estimator.configure(cfg);
  robot_core::NormalForceEstimatorInput stale{};
  stale.pressure_force_n = 6.0;
  stale.pressure_valid = true;
  stale.pressure_age_ms = 500.0;
  const auto stale_est = estimator.estimate(stale);
  assert(!stale_est.valid);
  assert(stale_est.source == "invalid");

  estimator.reset();
  const auto reset_est = estimator.lastEstimate();
  assert(reset_est.source == "invalid");
  return 0;
}
