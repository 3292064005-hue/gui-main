#include "robot_core/core_runtime.h"

#include "core_runtime_contract_json_helpers.h"
#include "robot_core/core_runtime_contract_publisher.h"
#include "robot_core/robot_family_descriptor.h"
#include "robot_core/robot_identity_contract.h"
#include "robot_core/safety_decision.h"

namespace robot_core {

using namespace contract_json;

std::string CoreRuntime::safetyRecoveryContractJsonLocked() const {
  using namespace json;
  const auto snapshot = procedure_executor_.recovery_kernel.snapshot(state_store_.config, procedure_executor_.force_limits, procedure_executor_.recovery_manager);
  return object({
      field("summary_state", quote(snapshot.summary_state)),
      field("summary_label", quote(snapshot.summary_label)),
      field("detail", quote(snapshot.detail)),
      field("policy_layers", stringArray(snapshot.policy_layers)),
      field("supported_actions", stringArray(snapshot.supported_actions)),
      field("pause_resume_enabled", boolLiteral(snapshot.pause_resume_enabled)),
      field("safe_retreat_enabled", boolLiteral(snapshot.safe_retreat_enabled)),
      field("operator_ack_required_for_fault_latched", boolLiteral(snapshot.operator_ack_required_for_fault_latched)),
      field("runtime_guard_enforced", boolLiteral(snapshot.runtime_guard_enforced)),
      field("recovery_state", quote(snapshot.recovery_state)),
      field("collision_behavior", quote(snapshot.collision_behavior)),
      field("resume_force_band_n", formatDouble(snapshot.resume_force_band_n)),
      field("warning_z_force_n", formatDouble(snapshot.warning_z_force_n)),
      field("max_z_force_n", formatDouble(snapshot.max_z_force_n)),
      field("sensor_timeout_ms", formatDouble(snapshot.sensor_timeout_ms)),
      field("stale_telemetry_ms", formatDouble(snapshot.stale_telemetry_ms)),
      field("emergency_retract_mm", formatDouble(snapshot.emergency_retract_mm))
  });
}

std::string CoreRuntime::hardwareLifecycleContractJsonLocked() const {
  using namespace json;
  const std::string lifecycle = procedure_executor_.sdk_robot.hardwareLifecycleState();
  const bool live_takeover_ready = procedure_executor_.sdk_robot.liveTakeoverReady();
  const std::string summary_state = live_takeover_ready ? "ready" : (state_store_.controller_online ? "warning" : "blocked");
  return object({
      field("summary_state", quote(summary_state)),
      field("summary_label", quote(live_takeover_ready ? std::string("hardware lifecycle ready") : std::string("hardware lifecycle contract"))),
      field("detail", quote("Hardware layer owns SDK channels and exposes read/update/write style lifecycle readiness.")),
      field("runtime_source", quote(procedure_executor_.sdk_robot.runtimeSource())),
      field("sdk_binding_mode", quote(procedure_executor_.sdk_robot.sdkBindingMode())),
      field("lifecycle_state", quote(lifecycle)),
      field("controller_manager_model", quote("hardware_layer__read_update_write")),
      field("transport_ready", boolLiteral(state_store_.controller_online)),
      field("motion_channel_ready", boolLiteral(procedure_executor_.sdk_robot.motionChannelReady())),
      field("state_channel_ready", boolLiteral(procedure_executor_.sdk_robot.stateChannelReady())),
      field("aux_channel_ready", boolLiteral(procedure_executor_.sdk_robot.auxChannelReady())),
      field("network_healthy", boolLiteral(procedure_executor_.sdk_robot.networkHealthy())),
      field("control_source_exclusive", boolLiteral(procedure_executor_.sdk_robot.controlSourceExclusive())),
      field("active_nrt_profile", quote(procedure_executor_.sdk_robot.activeNrtProfile())),
      field("active_rt_phase", quote(procedure_executor_.sdk_robot.activeRtPhase())),
      field("command_sequence", std::to_string(procedure_executor_.sdk_robot.commandSequence())),
      field("live_takeover_ready", boolLiteral(live_takeover_ready)),
      field("single_control_source_required", boolLiteral(state_store_.config.requires_single_control_source))
  });
}

std::string CoreRuntime::rtKernelContractJsonLocked() const {
  using namespace json;
  const auto rt = procedure_executor_.rt_motion_service.snapshot();
  const std::string summary_state = rt.degraded_without_sdk ? "warning" : "ready";
  return object({
      field("summary_state", quote(summary_state)),
      field("summary_label", quote(rt.degraded_without_sdk ? std::string("rt kernel contract shell") : std::string("rt kernel measured"))),
      field("detail", quote("RT kernel follows read/update/write staging around the official SDK controller callback.")),
      field("runtime_source", quote(procedure_executor_.sdk_robot.runtimeSource())),
      field("nominal_loop_hz", std::to_string(rt.nominal_loop_hz)),
      field("read_update_write", stringArray({"read_state", "update_phase_policy", "write_command"})),
      field("phase", quote(rt.phase)),
      field("monitors", object({
          field("reference_limiter", boolLiteral(rt.reference_limiter_enabled)),
          field("freshness_guard", boolLiteral(rt.freshness_guard_enabled)),
          field("jitter_monitor", boolLiteral(rt.jitter_monitor_enabled)),
          field("contact_band_monitor", boolLiteral(rt.contact_band_monitor_enabled)),
          field("network_guard", boolLiteral(rt.network_guard_enabled))
      })),
      field("fixed_period_enforced", boolLiteral(rt.fixed_period_enforced)),
      field("network_healthy", boolLiteral(rt.network_healthy)),
      field("overrun_count", std::to_string(rt.overrun_count)),
      field("current_period_ms", formatDouble(rt.current_period_ms)),
      field("max_cycle_ms", formatDouble(rt.max_cycle_ms)),
      field("last_wake_jitter_ms", formatDouble(rt.last_wake_jitter_ms)),
      field("last_sensor_decision", quote(rt.last_sensor_decision)),
      field("rt_quality_gate_passed", boolLiteral(state_store_.rt_jitter_ok)),
      field("jitter_budget_ms", formatDouble(rt.jitter_budget_ms)),
      field("freshness_budget_ms", std::to_string(state_store_.config.pressure_stale_ms)),
      field("reference_limits", object({field("max_cart_step_mm", formatDouble(2.5)), field("max_force_delta_n", formatDouble(1.0))})),
      field("degraded_without_sdk", boolLiteral(rt.degraded_without_sdk))
  });
}

std::string CoreRuntime::sessionDriftContractJsonLocked() const {
  using namespace json;
  const bool session_locked = !state_store_.session_id.empty();
  const bool freeze_consistent = sessionFreezeConsistentLocked();
  std::vector<std::string> drifts;
  if (session_locked && !freeze_consistent) {
    drifts.push_back(object({field("name", quote("plan_hash")), field("detail", quote("locked plan hash does not match active plan hash"))}));
  }
  return object({
      field("summary_state", quote(drifts.empty() ? std::string("ready") : std::string("blocked"))),
      field("summary_label", quote(drifts.empty() ? std::string("hard freeze consistent") : std::string("hard freeze drift detected"))),
      field("detail", quote("Session hard freeze watches runtime binding and locked plan hash consistency.")),
      field("session_locked", boolLiteral(session_locked)),
      field("locked_runtime_config_hash", quote(session_locked ? std::string("locked_by_runtime_contract") : std::string(""))),
      field("active_runtime_config_hash", quote(session_locked ? std::string("active_runtime_contract") : std::string(""))),
      field("locked_sdk_boundary_hash", quote(session_locked ? std::string("locked_sdk_boundary_contract") : std::string(""))),
      field("active_sdk_boundary_hash", quote(session_locked ? std::string("active_sdk_boundary_contract") : std::string(""))),
      field("locked_executor_hash", quote(session_locked ? std::string("locked_executor_contract") : std::string(""))),
      field("active_executor_hash", quote(session_locked ? std::string("active_executor_contract") : std::string(""))),
      field("locked_scan_plan_hash", quote(state_store_.locked_scan_plan_hash)),
      field("active_plan_hash", quote(state_store_.plan_hash)),
      field("drifts", objectArray(drifts))
  });
}

}  // namespace robot_core
