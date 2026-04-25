#include "robot_core/orientation_trim_controller.h"

#include <algorithm>
#include <cmath>

namespace robot_core {

namespace { double degToRad(double v){ return v * M_PI / 180.0; } }

void OrientationTrimController::configure(const OrientationTrimConfig& config) {
  state_store_.config = config;
  state_store_.config.gain = std::max(0.0, config.gain);
  state_store_.config.max_trim_deg = std::max(0.1, config.max_trim_deg);
  state_store_.config.lowpass_hz = std::max(0.1, config.lowpass_hz);
}

OrientationTrimState OrientationTrimController::step(double force_error_n, double dt_s) {
  const double target = std::clamp(state_store_.config.gain * force_error_n, -degToRad(state_store_.config.max_trim_deg), degToRad(state_store_.config.max_trim_deg));
  const double alpha = std::clamp(dt_s * 2.0 * M_PI * state_store_.config.lowpass_hz, 0.0, 1.0);
  state_.trim_rad += alpha * (target - state_.trim_rad);
  const double max_trim = degToRad(state_store_.config.max_trim_deg);
  state_.saturated = std::abs(target) >= max_trim;
  state_.trim_rad = std::clamp(state_.trim_rad, -max_trim, max_trim);
  return state_;
}

void OrientationTrimController::reset() { state_ = {}; }

}  // namespace robot_core
