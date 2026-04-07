#include "robot_core/orientation_trim_controller.h"

#include <cassert>
#include <cmath>

int main() {
  robot_core::OrientationTrimController controller;
  robot_core::OrientationTrimConfig cfg;
  cfg.gain = 0.1;
  cfg.max_trim_deg = 1.0;
  cfg.lowpass_hz = 10.0;
  controller.configure(cfg);

  const auto zero = controller.step(0.0, 0.01);
  assert(std::abs(zero.trim_rad) < 1e-12);
  assert(!zero.saturated);

  auto saturated = controller.step(100.0, 0.1);
  const double max_trim = 1.0 * M_PI / 180.0;
  assert(std::abs(saturated.trim_rad) <= max_trim + 1e-9);
  assert(saturated.saturated);

  controller.reset();
  const auto reset = controller.state();
  assert(reset.trim_rad == 0.0);
  assert(!reset.saturated);
  return 0;
}
