#include "robot_core/safety_service.h"

namespace robot_core {

bool SafetyService::checkNetworkStable() const {
  return true;
}

bool SafetyService::checkNetworkStable(bool controller_online, bool pressure_fresh, bool robot_state_fresh, bool rt_jitter_ok) const {
  return controller_online && pressure_fresh && robot_state_fresh && rt_jitter_ok;
}

SafetyStatus SafetyService::evaluate(bool controller_online, bool powered, bool automatic_mode,
                                     bool session_locked, bool path_loaded, bool pressure_fresh,
                                     bool robot_state_fresh, bool pressure_safe, bool rt_jitter_ok,
                                     bool tool_ready, bool tcp_ready, bool load_ready) const {
  SafetyStatus status;
  const bool network_stable = checkNetworkStable(controller_online, pressure_fresh, robot_state_fresh, rt_jitter_ok);
  status.safe_to_arm = controller_online && powered && automatic_mode && network_stable;
  if (!controller_online) status.active_interlocks.push_back("controller_offline");
  if (!powered) status.active_interlocks.push_back("power_off");
  if (!automatic_mode) status.active_interlocks.push_back("not_in_automatic_mode");
  if (!tool_ready) status.active_interlocks.push_back("tool_unvalidated");
  if (!tcp_ready) status.active_interlocks.push_back("tcp_unvalidated");
  if (!load_ready) status.active_interlocks.push_back("load_unvalidated");
  if (!session_locked) status.active_interlocks.push_back("session_unlocked");
  if (!path_loaded) status.active_interlocks.push_back("scan_plan_missing");
  if (!pressure_fresh) status.active_interlocks.push_back("pressure_stale");
  if (!robot_state_fresh) status.active_interlocks.push_back("robot_state_stale");
  if (!pressure_safe) status.active_interlocks.push_back("pressure_over_upper_limit");
  if (!rt_jitter_ok) status.active_interlocks.push_back("rt_jitter_high");

  status.safe_to_scan = status.safe_to_arm && status.active_interlocks.empty();
  status.pressure_band_state = pressure_safe ? "WITHIN_LIMIT" : "OVER_LIMIT";
  status.sensor_freshness_ms = (!pressure_fresh || !robot_state_fresh) ? 999 : 0;
  status.recovery_reason = status.active_interlocks.empty() ? "clear" : status.active_interlocks.front();
  if (!pressure_safe) {
    status.last_recovery_action = "safe_retreat";
    status.force_excursion_count = 1;
  } else if (!pressure_fresh || !robot_state_fresh) {
    status.last_recovery_action = "pause_hold";
    status.contact_instability_count = 1;
  } else if (!rt_jitter_ok) {
    status.last_recovery_action = "warn_only";
  } else if (!session_locked || !path_loaded || !tool_ready || !tcp_ready || !load_ready) {
    status.last_recovery_action = "revalidate_setup";
  } else {
    status.last_recovery_action = "none";
  }
  return status;
}

}  // namespace robot_core
