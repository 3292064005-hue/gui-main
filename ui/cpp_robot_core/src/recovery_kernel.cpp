#include "robot_core/recovery_kernel.h"

#include "robot_core/recovery_manager.h"

namespace robot_core {

RecoveryKernelSnapshot RecoveryKernel::snapshot(const RuntimeConfig& config,
                                                const ForceControlLimits& limits,
                                                const RecoveryManager& recovery_manager) const {
  RecoveryKernelSnapshot out;
  out.recovery_state = recovery_manager.currentStateName();
  out.collision_behavior = config.collision_behavior;
  out.resume_force_band_n = limits.resume_force_band_n;
  out.warning_z_force_n = limits.warning_z_force_n;
  out.max_z_force_n = limits.max_z_force_n;
  out.sensor_timeout_ms = limits.sensor_timeout_ms;
  out.stale_telemetry_ms = limits.stale_telemetry_ms;
  out.emergency_retract_mm = limits.emergency_retract_mm;
  if (out.recovery_state == "EstopLatched") {
    out.summary_state = "blocked";
    out.summary_label = "safety/recovery latched";
  } else if (out.recovery_state == "ControlledRetract" || out.recovery_state == "Holding") {
    out.summary_state = "warning";
    out.summary_label = "safety/recovery active";
  }
  return out;
}

}  // namespace robot_core
