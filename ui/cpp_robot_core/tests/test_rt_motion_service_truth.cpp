#include "robot_core/rt_motion_service.h"
#include "robot_core/sdk_robot_facade.h"

#include <cassert>

int main() {
  robot_core::RtMotionService service(nullptr, nullptr);
  service.recordLoopSample(2.0, 0.45, 0.12, false);
  service.stop();
  const auto snapshot = service.snapshot();
  assert(snapshot.current_period_ms == 2.0);
  assert(snapshot.max_cycle_ms >= 0.45);
  assert(snapshot.last_wake_jitter_ms == 0.12);

  robot_core::SdkRobotFacade facade;
  robot_core::RtPhaseControlContract contract{};
  contract.common.max_cart_step_mm = 0.25;
  contract.common.max_cart_vel_mm_s = 10.0;
  contract.common.max_cart_acc_mm_s2 = 100.0;
  contract.common.max_pose_trim_deg = 1.0;
  contract.common.stale_state_timeout_ms = 40.0;
  contract.seek_contact.establish_cycles = 3;
  contract.scan_follow.tangent_speed_min_mm_s = 1.0;
  contract.scan_follow.tangent_speed_max_mm_s = 5.0;
  contract.controlled_retract.release_cycles = 2;
  contract.controlled_retract.timeout_ms = 500.0;
  facade.setRtPhaseControlContract(contract);
  std::string reason;
  assert(facade.validateRtControlContract(&reason));
  facade.resetRtPhaseIntegrators();

  std::string complete_reason;
  assert(service.completeRtPhase("scan_follow", &complete_reason));
  assert(complete_reason == "phase_completed:scan_follow");
  const auto completed_snapshot = service.snapshot();
  assert(completed_snapshot.phase == "idle");
  assert(completed_snapshot.desired_contact_force_n == 0.0);

  assert(!service.faultRtPhase("controlled_retract", "timeout_waiting_phase_completion"));
  const auto fault_snapshot = service.snapshot();
  assert(fault_snapshot.phase == "blocked");
  assert(fault_snapshot.last_sensor_decision == "timeout_waiting_phase_completion");
  return 0;
}
