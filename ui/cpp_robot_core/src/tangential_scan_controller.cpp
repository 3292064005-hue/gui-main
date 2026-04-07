#include "robot_core/tangential_scan_controller.h"

#include <algorithm>
#include <cmath>

namespace robot_core {

namespace { double mmToM(double mm) { return mm / 1000.0; } }

void TangentialScanController::configure(const TangentialScanConfig& config) {
  config_ = config;
  config_.tangent_speed_min_mm_s = std::max(0.1, config.tangent_speed_min_mm_s);
  config_.tangent_speed_max_mm_s = std::max(config_.tangent_speed_min_mm_s, config.tangent_speed_max_mm_s);
  config_.max_travel_mm = std::max(1.0, config.max_travel_mm);
  config_.lateral_amplitude_mm = std::max(0.0, config.lateral_amplitude_mm);
  config_.modulation_frequency_hz = std::max(0.01, config.modulation_frequency_hz);
}

TangentialScanState TangentialScanController::advance(double requested_speed_mm_s, double dt_s) {
  const double speed_mm_s = std::clamp(requested_speed_mm_s, config_.tangent_speed_min_mm_s, config_.tangent_speed_max_mm_s);
  state_.progress_m += mmToM(speed_mm_s) * std::max(0.0, dt_s);
  state_.saturated = state_.progress_m >= mmToM(config_.max_travel_mm);
  if (state_.saturated) {
    state_.progress_m = mmToM(config_.max_travel_mm);
  }
  if (config_.enable_lateral_modulation) {
    state_.lateral_offset_m = mmToM(config_.lateral_amplitude_mm) * std::sin(2.0 * M_PI * config_.modulation_frequency_hz * state_.progress_m / std::max(1e-6, mmToM(speed_mm_s)));
  } else {
    state_.lateral_offset_m = 0.0;
  }
  return state_;
}

void TangentialScanController::reset() { state_ = {}; }

}  // namespace robot_core
