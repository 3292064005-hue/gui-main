#include "robot_core/tangential_scan_controller.h"

#include <cassert>
#include <cmath>

int main() {
  robot_core::TangentialScanController controller;
  robot_core::TangentialScanConfig cfg;
  cfg.tangent_speed_min_mm_s = 2.0;
  cfg.tangent_speed_max_mm_s = 10.0;
  cfg.max_travel_mm = 5.0;
  cfg.enable_lateral_modulation = true;
  cfg.lateral_amplitude_mm = 0.5;
  cfg.modulation_frequency_hz = 0.5;
  controller.configure(cfg);

  const auto step1 = controller.advance(8.0, 0.25);
  assert(step1.progress_m > 0.0);
  assert(std::abs(step1.lateral_offset_m) <= 0.0005 + 1e-9);

  auto state = step1;
  for (int i = 0; i < 10 && !state.saturated; ++i) {
    state = controller.advance(8.0, 0.25);
  }
  assert(state.saturated);
  assert(state.progress_m <= 0.005 + 1e-9);

  controller.reset();
  const auto reset = controller.state();
  assert(reset.progress_m == 0.0);
  assert(reset.lateral_offset_m == 0.0);
  return 0;
}
