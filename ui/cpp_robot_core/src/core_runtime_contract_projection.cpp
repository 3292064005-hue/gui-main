#include "robot_core/core_runtime.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <cstdlib>

#include "json_utils.h"
#include "robot_core/force_state.h"

namespace robot_core {
namespace {

constexpr int kProtocolVersion = 1;

std::string objectArray(const std::vector<std::string>& entries) {
  std::string out = "[";
  for (size_t idx = 0; idx < entries.size(); ++idx) {
    if (idx > 0) out += ",";
    out += entries[idx];
  }
  out += "]";
  return out;
}

std::string vectorJson(const std::vector<double>& values) { return json::array(values); }
std::vector<double> array6ToVector(const std::array<double, 6>& values) { return std::vector<double>(values.begin(), values.end()); }
std::vector<double> array16ToVector(const std::array<double, 16>& values) { return std::vector<double>(values.begin(), values.end()); }
std::vector<double> array3ToVector(const std::array<double, 3>& values) { return std::vector<double>(values.begin(), values.end()); }


bool strictDeploymentShellWritesForbidden() {
  const char* profile = std::getenv("SPINE_DEPLOYMENT_PROFILE");
  const std::string profile_name = profile != nullptr ? std::string(profile) : std::string();
  if (profile_name == "research" || profile_name == "clinical") return true;
  const char* strict = std::getenv("SPINE_STRICT_CONTROL_AUTHORITY");
  if (strict == nullptr) return false;
  const std::string value(strict);
  return value == "1" || value == "true" || value == "TRUE" || value == "on" || value == "ON";
}

}  // namespace

std::string CoreRuntime::authoritativeRuntimeEnvelopeJsonInternal() const {
  using namespace json;
  std::vector<std::string> blockers;
  std::vector<std::string> warnings;
  appendMainlineContractIssuesLocked(&blockers, &warnings);
  const auto runtime_cfg = sdk_robot_.runtimeConfig();
  const std::string authority_state = controller_online_ ? (blockers.empty() ? std::string("ready") : std::string("blocked")) : std::string("degraded");
  const auto session_freeze = object({
      field("session_locked", boolLiteral(!session_id_.empty())),
      field("session_id", quote(session_id_)),
      field("session_dir", quote(session_dir_)),
      field("locked_at_ns", std::to_string(session_locked_ts_ns_)),
      field("plan_hash", quote(plan_hash_)),
      field("active_segment", std::to_string(active_segment_)),
      field("tool_name", quote(config_.tool_name)),
      field("tcp_name", quote(config_.tcp_name)),
      field("load_kg", formatDouble(config_.load_kg)),
      field("rt_mode", quote(config_.rt_mode)),
      field("cartesian_impedance", vectorJson(config_.cartesian_impedance)),
      field("desired_wrench_n", vectorJson(config_.desired_wrench_n)),
      field("contact_force_target_n", formatDouble(config_.contact_force_target_n)),
      field("scan_force_target_n", formatDouble(config_.scan_force_target_n)),
      field("retract_timeout_ms", formatDouble(config_.retract_timeout_ms)),
      field("freeze_version", quote("hard_freeze_v2"))
  });
  const auto applied_runtime_config = object({
      field("robot_model", quote(runtime_cfg.robot_model)),
      field("sdk_robot_class", quote(runtime_cfg.sdk_robot_class)),
      field("remote_ip", quote(runtime_cfg.remote_ip)),
      field("local_ip", quote(runtime_cfg.local_ip)),
      field("axis_count", std::to_string(runtime_cfg.axis_count)),
      field("rt_network_tolerance_percent", std::to_string(runtime_cfg.rt_network_tolerance_percent)),
      field("joint_filter_hz", formatDouble(runtime_cfg.joint_filter_hz)),
      field("cart_filter_hz", formatDouble(runtime_cfg.cart_filter_hz)),
      field("torque_filter_hz", formatDouble(runtime_cfg.torque_filter_hz)),
      field("fc_frame_type", quote(config_.fc_frame_type)),
      field("preferred_link", quote(config_.preferred_link)),
      field("requires_single_control_source", boolLiteral(config_.requires_single_control_source)),
      field("allow_contract_shell_writes", boolLiteral(config_.allow_contract_shell_writes)),
      field("rt_mode", quote(config_.rt_mode)),
      field("runtime_config_contract_digest", quote(config_.runtime_config_contract_digest)),
      field("runtime_config_schema_version", quote(config_.runtime_config_schema_version)),
      field("tool_name", quote(config_.tool_name)),
      field("tcp_name", quote(config_.tcp_name)),
      field("load_kg", formatDouble(config_.load_kg)),
      field("cartesian_impedance", vectorJson(array6ToVector(runtime_cfg.cartesian_impedance))),
      field("desired_wrench_n", vectorJson(array6ToVector(runtime_cfg.desired_wrench_n))),
      field("fc_frame_matrix", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix))),
      field("tcp_frame_matrix", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix))),
      field("load_com_mm", vectorJson(array3ToVector(runtime_cfg.load_com_mm))),
      field("fc_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix_m))),
      field("tcp_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix_m))),
      field("load_com_m", vectorJson(array3ToVector(runtime_cfg.load_com_m))),
      field("ui_length_unit", quote(runtime_cfg.ui_length_unit)),
      field("sdk_length_unit", quote(runtime_cfg.sdk_length_unit)),
      field("boundary_normalized", boolLiteral(runtime_cfg.boundary_normalized)),
      field("load_inertia", vectorJson(array6ToVector(runtime_cfg.load_inertia))),
      field("rt_stale_state_timeout_ms", formatDouble(runtime_cfg.rt_stale_state_timeout_ms)),
      field("rt_phase_transition_debounce_cycles", std::to_string(runtime_cfg.rt_phase_transition_debounce_cycles)),
      field("rt_max_cart_step_mm", formatDouble(runtime_cfg.rt_max_cart_step_mm)),
      field("contact_force_target_n", formatDouble(runtime_cfg.contact_force_target_n)),
      field("scan_force_target_n", formatDouble(runtime_cfg.scan_force_target_n)),
      field("retract_timeout_ms", formatDouble(runtime_cfg.retract_timeout_ms))
  });
  const bool shell_write_allowed = config_.allow_contract_shell_writes && !strictDeploymentShellWritesForbidden();
  const auto write_capabilities = object({
      field("hardware_lifecycle_write", object({
          field("allowed", boolLiteral(sdk_robot_.liveBindingEstablished() || shell_write_allowed)),
          field("reason", quote((sdk_robot_.liveBindingEstablished() || shell_write_allowed) ? std::string("") : (strictDeploymentShellWritesForbidden() ? std::string("deployment_profile_forbids_contract_shell_write") : std::string("live_binding_required")))),
          field("source_of_truth", quote("cpp_robot_core"))
      })),
      field("nrt_motion_write", object({
          field("allowed", boolLiteral(sdk_robot_.liveBindingEstablished() || shell_write_allowed)),
          field("reason", quote((sdk_robot_.liveBindingEstablished() || shell_write_allowed) ? std::string("") : (strictDeploymentShellWritesForbidden() ? std::string("deployment_profile_forbids_contract_shell_write") : std::string("live_binding_required")))),
          field("source_of_truth", quote("cpp_robot_core"))
      })),
      field("rt_motion_write", object({
          field("allowed", boolLiteral(sdk_robot_.liveTakeoverReady() || shell_write_allowed)),
          field("reason", quote((sdk_robot_.liveTakeoverReady() || shell_write_allowed) ? std::string("") : (strictDeploymentShellWritesForbidden() ? std::string("deployment_profile_forbids_contract_shell_write") : std::string("live_takeover_ready_required")))),
          field("source_of_truth", quote("cpp_robot_core"))
      })),
      field("recovery_write", object({
          field("allowed", boolLiteral(sdk_robot_.liveBindingEstablished() || shell_write_allowed)),
          field("reason", quote((sdk_robot_.liveBindingEstablished() || shell_write_allowed) ? std::string("") : (strictDeploymentShellWritesForbidden() ? std::string("deployment_profile_forbids_contract_shell_write") : std::string("live_binding_required")))),
          field("source_of_truth", quote("cpp_robot_core"))
      })),
      field("session_freeze_write", object({
          field("allowed", boolLiteral(controller_online_)),
          field("reason", quote(controller_online_ ? std::string("") : std::string("controller_not_connected"))),
          field("source_of_truth", quote("cpp_robot_core"))
      }))
  });

  const auto control_authority = controlAuthorityJsonLocked();
  const auto telemetry_authority = object({
      field("runtime_source", quote(sdk_robot_.queryPort().runtimeSource())),
      field("fact_policy", quote(simulatedTelemetryAllowedLocked() ? std::string("mock_profile_simulated_facts") : std::string("measured_only_or_unavailable"))),
      field("quality", object({
          field("source", quote(quality_source_)),
          field("available", boolLiteral(quality_available_)),
          field("authoritative", boolLiteral(quality_authoritative_))
      })),
      field("contact", object({
          field("pressure_source", quote(contact_state_.pressure_source)),
          field("quality_source", quote(contact_state_.quality_source)),
          field("pressure_available", boolLiteral(contact_state_.pressure_available)),
          field("quality_available", boolLiteral(contact_state_.quality_available)),
          field("authoritative", boolLiteral(contact_state_.authoritative))
      }))
  });
  const auto plan_digest = object({
      field("plan_id", quote(plan_id_)),
      field("plan_hash", quote(plan_hash_)),
      field("active_segment", std::to_string(active_segment_)),
      field("session_id", quote(session_id_))
  });
  return object({
      field("summary_state", quote(authority_state)),
      field("summary_label", quote(authority_state == "ready" ? std::string("运行时权威快照可用") : (authority_state == "blocked" ? std::string("运行时权威快照阻塞") : std::string("运行时权威快照降级")))),
      field("detail", quote("cpp_robot_core authoritative runtime envelope")),
      field("authority_source", quote("cpp_robot_core")),
      field("protocol_version", std::to_string(kProtocolVersion)),
      field("control_authority", control_authority),
      field("write_capabilities", write_capabilities),
      field("runtime_config_applied", applied_runtime_config),
      field("telemetry_authority", telemetry_authority),
      field("session_freeze", session_freeze),
      field("plan_digest", plan_digest),
      field("final_verdict", finalVerdictJson(last_final_verdict_))
  });
}

}  // namespace robot_core
