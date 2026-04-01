#include "robot_core/rt_motion_service.h"

#include <cassert>

int main() {
  robot_core::RtMotionService service(nullptr, nullptr);
  service.recordLoopSample(2.0, 0.45, 0.12, false);
  service.stop();
  const auto snapshot = service.snapshot();
  assert(snapshot.current_period_ms == 2.0);
  assert(snapshot.max_cycle_ms >= 0.45);
  assert(snapshot.last_wake_jitter_ms == 0.12);
  return 0;
}
