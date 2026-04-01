#include "robot_core/recovery_policy.h"

#include <cmath>

namespace robot_core {

RecoveryDecision RecoveryPolicy::evaluate(double pressure_current, double pressure_target, double pressure_upper, double sensor_age_ms) const {
  const double lower_resume_band = pressure_target * 0.6;
  const double lower_hold_band = pressure_target * 0.4;
  const double hard_upper_abort = pressure_upper + 0.5;
  const double segment_abort_upper = pressure_upper + 0.2;
  const double stable_delta = std::max(0.05, pressure_target * 0.05);

  if (sensor_age_ms > 1000.0) return {"ESTOP_LATCHED", "sensor_timeout", "estop", "LEVEL_5_ESTOP"};
  if (sensor_age_ms > 500.0) return {"PLAN_ABORTED", "stale_sensor", "abort_plan", "LEVEL_4_ABORT_PLAN"};
  if (pressure_current > hard_upper_abort) return {"PLAN_ABORTED", "plan_integrity_mismatch", "abort_plan", "LEVEL_4_ABORT_PLAN"};
  if (pressure_current > segment_abort_upper) return {"SEGMENT_ABORTED", "over_force_escalated", "abort_segment", "LEVEL_3_ABORT_SEGMENT"};
  if (pressure_current > pressure_upper) return {"RECOVERY_RETRACT", "over_force", "controlled_retract", "LEVEL_2_RETRACT"};
  if (pressure_current <= 0.0) return {"PAUSED_HOLD", "contact_lost", "hold", "LEVEL_1_HOLD"};
  if (pressure_current < lower_hold_band) return {"PAUSED_HOLD", "under_contact", "hold", "LEVEL_1_HOLD"};
  if (pressure_current < lower_resume_band) return {"PAUSED_HOLD", "unstable_contact", "hold", "LEVEL_1_HOLD"};
  if (std::fabs(pressure_current - pressure_target) <= stable_delta) return {"RETRY_READY", "within_resume_band", "resume_allowed", "LEVEL_0_MONITOR"};
  return {"PAUSED_HOLD", "pressure_not_stable", "hold", "LEVEL_1_HOLD"};
}

}  // namespace robot_core
