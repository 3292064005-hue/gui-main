#include "robot_core/normal_force_estimator.h"

#include <algorithm>
#include <cmath>

namespace robot_core {

namespace {

double clamp01(double value) {
  return std::max(0.0, std::min(1.0, value));
}

bool sourceFresh(bool valid, double age_ms, double stale_timeout_ms, double timeout_ms) {
  return valid && age_ms >= 0.0 && age_ms <= timeout_ms && age_ms <= stale_timeout_ms;
}

}  // namespace

void NormalForceEstimator::configure(const NormalForceEstimatorConfig& config) {
  state_store_.config = config;
  state_store_.config.pressure_weight = clamp01(config.pressure_weight);
  state_store_.config.wrench_weight = clamp01(config.wrench_weight);
  if (state_store_.config.pressure_weight == 0.0 && state_store_.config.wrench_weight == 0.0) {
    state_store_.config.pressure_weight = 0.7;
    state_store_.config.wrench_weight = 0.3;
  }
  state_store_.config.stale_timeout_ms = std::max(1.0, config.stale_timeout_ms);
  state_store_.config.timeout_ms = std::max(state_store_.config.stale_timeout_ms, config.timeout_ms);
  state_store_.config.min_confidence = clamp01(config.min_confidence);
}

NormalForceEstimate NormalForceEstimator::estimate(const NormalForceEstimatorInput& input) {
  NormalForceEstimate out{};
  out.pressure_force_n = input.pressure_force_n;
  out.wrench_force_n = input.wrench_force_n;

  const bool pressure_fresh = sourceFresh(input.pressure_valid, input.pressure_age_ms, state_store_.config.stale_timeout_ms, state_store_.config.timeout_ms);
  const bool wrench_fresh = sourceFresh(input.wrench_valid, input.wrench_age_ms, state_store_.config.stale_timeout_ms, state_store_.config.timeout_ms);

  if (state_store_.config.auto_bias_zero && pressure_fresh && std::abs(input.pressure_force_n) < 0.25) {
    bias_n_ = input.pressure_force_n;
  }

  const double pressure_force = input.pressure_force_n - bias_n_;
  const double wrench_force = input.wrench_force_n * (input.contact_direction_sign == 0.0 ? 1.0 : input.contact_direction_sign);
  const std::string preferred = state_store_.config.preferred_source.empty() ? std::string("fused") : state_store_.config.preferred_source;

  const auto set_pressure = [&]() {
    out.estimated_force_n = pressure_force;
    out.source = "pressure";
    out.confidence = 0.7;
    out.valid = true;
  };
  const auto set_wrench = [&]() {
    out.estimated_force_n = wrench_force;
    out.source = "wrench";
    out.confidence = 0.55;
    out.valid = true;
  };
  const auto set_fused = [&]() {
    const double total = std::max(1e-9, state_store_.config.pressure_weight + state_store_.config.wrench_weight);
    out.estimated_force_n = (state_store_.config.pressure_weight * pressure_force + state_store_.config.wrench_weight * wrench_force) / total;
    out.source = "fused";
    out.confidence = 1.0;
    out.valid = true;
  };

  if (preferred == "pressure") {
    if (pressure_fresh) {
      set_pressure();
    } else if (wrench_fresh) {
      set_wrench();
    }
  } else if (preferred == "wrench") {
    if (wrench_fresh) {
      set_wrench();
    } else if (pressure_fresh) {
      set_pressure();
    }
  } else {
    if (pressure_fresh && wrench_fresh) {
      set_fused();
    } else if (pressure_fresh) {
      set_pressure();
    } else if (wrench_fresh) {
      set_wrench();
    }
  }

  if (!out.valid) {
    out.source = "invalid";
    out.confidence = 0.0;
  }

  out.bias_compensated_force_n = out.estimated_force_n;
  out.stale = !out.valid;
  if (out.confidence < state_store_.config.min_confidence) {
    out.valid = false;
    out.stale = true;
    out.source = "invalid";
    out.estimated_force_n = 0.0;
    out.bias_compensated_force_n = 0.0;
  }
  last_estimate_ = out;
  return out;
}

void NormalForceEstimator::reset() {
  bias_n_ = 0.0;
  last_estimate_ = {};
}

}  // namespace robot_core
