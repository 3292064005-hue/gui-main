#include "robot_core/core_runtime.h"

#include <algorithm>
#include <cmath>
#include <filesystem>

#include "json_utils.h"
#include "robot_core/force_state.h"
#include "robot_core/robot_identity_contract.h"
#include "robot_core/robot_family_descriptor.h"
#include "robot_core/safety_decision.h"

namespace robot_core {

namespace {

constexpr int kProtocolVersion = 1;

std::string stateName(RobotCoreState state) {
  switch (state) {
    case RobotCoreState::Boot: return "BOOT";
    case RobotCoreState::Disconnected: return "DISCONNECTED";
    case RobotCoreState::Connected: return "CONNECTED";
    case RobotCoreState::Powered: return "POWERED";
    case RobotCoreState::AutoReady: return "AUTO_READY";
    case RobotCoreState::SessionLocked: return "SESSION_LOCKED";
    case RobotCoreState::PathValidated: return "PATH_VALIDATED";
    case RobotCoreState::Approaching: return "APPROACHING";
    case RobotCoreState::ContactSeeking: return "CONTACT_SEEKING";
    case RobotCoreState::ContactStable: return "CONTACT_STABLE";
    case RobotCoreState::Scanning: return "SCANNING";
    case RobotCoreState::PausedHold: return "PAUSED_HOLD";
    case RobotCoreState::RecoveryRetract: return "RECOVERY_RETRACT";
    case RobotCoreState::SegmentAborted: return "SEGMENT_ABORTED";
    case RobotCoreState::PlanAborted: return "PLAN_ABORTED";
    case RobotCoreState::Retreating: return "RETREATING";
    case RobotCoreState::ScanComplete: return "SCAN_COMPLETE";
    case RobotCoreState::Fault: return "FAULT";
    case RobotCoreState::Estop: return "ESTOP";
  }
  return "BOOT";
}

std::string objectArray(const std::vector<std::string>& entries) {
  std::string out = "[";
  for (size_t idx = 0; idx < entries.size(); ++idx) {
    if (idx > 0) {
      out += ",";
    }
    out += entries[idx];
  }
  out += "]";
  return out;
}

std::string summaryEntry(const std::string& name, const std::string& detail) {
  return json::object({json::field("name", json::quote(name)), json::field("detail", json::quote(detail))});
}

std::string logEntryJson(const std::string& level, const std::string& source, const std::string& message) {
  return json::object({
      json::field("level", json::quote(level)),
      json::field("source", json::quote(source)),
      json::field("message", json::quote(message)),
  });
}

std::string boolMapJson(const std::map<std::string, bool>& items) {
  std::vector<std::string> fields;
  for (const auto& [key, value] : items) {
    fields.push_back(json::field(key, json::boolLiteral(value)));
  }
  return json::object(fields);
}

std::string doubleMapJson(const std::map<std::string, double>& items) {
  std::vector<std::string> fields;
  for (const auto& [key, value] : items) {
    fields.push_back(json::field(key, json::formatDouble(value)));
  }
  return json::object(fields);
}

std::string intMapJson(const std::map<std::string, int>& items) {
  std::vector<std::string> fields;
  for (const auto& [key, value] : items) {
    fields.push_back(json::field(key, std::to_string(value)));
  }
  return json::object(fields);
}

std::string projectArrayJson(const std::vector<SdkRobotProjectInfo>& projects) {
  std::vector<std::string> entries;
  for (const auto& project : projects) {
    entries.push_back(json::object({
        json::field("name", json::quote(project.name)),
        json::field("tasks", json::stringArray(project.tasks)),
    }));
  }
  return objectArray(entries);
}

std::string pathArrayJson(const std::vector<SdkRobotPathInfo>& paths) {
  std::vector<std::string> entries;
  for (const auto& path : paths) {
    entries.push_back(json::object({
        json::field("name", json::quote(path.name)),
        json::field("rate", json::formatDouble(path.rate)),
        json::field("points", std::to_string(path.points)),
    }));
  }
  return objectArray(entries);
}

std::string vectorJson(const std::vector<double>& values) { return json::array(values); }

std::string dhArrayJson(const std::vector<OfficialDhParameter>& params) {
  std::vector<std::string> entries;
  for (const auto& item : params) {
    entries.push_back(json::object({
        json::field("joint", std::to_string(item.joint)),
        json::field("a_mm", json::formatDouble(item.a_mm)),
        json::field("alpha_rad", json::formatDouble(item.alpha_rad, 4)),
        json::field("d_mm", json::formatDouble(item.d_mm)),
        json::field("theta_rad", json::formatDouble(item.theta_rad, 4)),
    }));
  }
  return objectArray(entries);
}

std::vector<double> array6ToVector(const std::array<double, 6>& values) {
  return std::vector<double>(values.begin(), values.end());
}

std::vector<double> array16ToVector(const std::array<double, 16>& values) {
  return std::vector<double>(values.begin(), values.end());
}

std::vector<double> array3ToVector(const std::array<double, 3>& values) {
  return std::vector<double>(values.begin(), values.end());
}

}  // namespace

std::string CoreRuntime::robotFamilyContractJsonLocked() const {
  using namespace json;
  const auto family = resolveRobotFamilyDescriptor(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
  return object({
      field("summary_state", quote("ready")),
      field("summary_label", quote(family.family_label)),
      field("detail", quote("Robot family capabilities are derived from the frozen family descriptor matrix.")),
      field("family_key", quote(family.family_key)),
      field("family_label", quote(family.family_label)),
      field("robot_model", quote(family.robot_model)),
      field("sdk_robot_class", quote(family.sdk_robot_class)),
      field("axis_count", std::to_string(family.axis_count)),
      field("clinical_rt_mode", quote(family.clinical_rt_mode)),
      field("supports_xmate_model", boolLiteral(family.supports_xmate_model)),
      field("supports_planner", boolLiteral(family.supports_planner)),
      field("supports_drag", boolLiteral(family.supports_drag)),
      field("supports_path_replay", boolLiteral(family.supports_path_replay)),
      field("requires_single_control_source", boolLiteral(family.requires_single_control_source)),
      field("preferred_link", quote(family.preferred_link)),
      field("supported_nrt_profiles", stringArray(family.supported_nrt_profiles)),
      field("supported_rt_phases", stringArray(family.supported_rt_phases))
  });
}

std::string CoreRuntime::vendorBoundaryContractJsonLocked() const {
  using namespace json;
  const bool sdk_detected = sdk_robot_.sdkAvailable();
  const bool live_binding = sdk_robot_.liveBindingEstablished();
  const std::string summary_state = live_binding ? std::string("ready") : (sdk_detected ? std::string("warning") : std::string("blocked"));
  return object({
      field("summary_state", quote(summary_state)),
      field("summary_label", quote(live_binding ? std::string("vendor boundary live") : std::string("vendor boundary contract"))),
      field("detail", quote(live_binding ? std::string("Vendor boundary owns a live SDK binding with exclusive-control and fixed-period RT semantics.") : std::string("Vendor boundary contract is present, but real live binding/lifecycle readiness/exclusive-control evidence is not yet established."))),
      field("binding_mode", quote(sdk_robot_.sdkBindingMode())),
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("single_control_source_required", boolLiteral(config_.requires_single_control_source)),
      field("control_source_exclusive", boolLiteral(sdk_robot_.controlSourceExclusive())),
      field("fixed_period_enforced", boolLiteral(true)),
      field("network_healthy", boolLiteral(sdk_robot_.networkHealthy())),
      field("active_nrt_profile", quote(sdk_robot_.activeNrtProfile())),
      field("active_rt_phase", quote(sdk_robot_.activeRtPhase())),
      field("nominal_rt_loop_hz", std::to_string(sdk_robot_.nominalRtLoopHz()))
  });
}

std::string CoreRuntime::capabilityContractJsonLocked() const {
  const auto& identity = resolveRobotIdentity("xmate3", "xMateRobot", 6);
  using namespace json;
  const bool live_binding = sdk_robot_.liveBindingEstablished();
  auto module_entry = [&](const std::string& module, bool enabled, const std::string& status, const std::string& purpose, bool vendor_supported = true, bool runtime_implemented = true, bool live_required = false) {
    return object({field("module", quote(module)), field("enabled", boolLiteral(enabled)), field("status", quote(status)), field("purpose", quote(purpose)), field("vendor_supported", boolLiteral(vendor_supported)), field("runtime_implemented", boolLiteral(runtime_implemented)), field("live_binding_established", boolLiteral(live_required ? live_binding : false))});
  };
  std::vector<std::string> modules;
  modules.push_back(module_entry("rokae::Robot", true, "ready", "连接、上电、模式切换、姿态/关节/日志/工具工件查询", true, true, true));
  modules.push_back(module_entry("rokae::RtMotionControl", config_.rt_mode == identity.clinical_mainline_mode && config_.rt_mode != "directTorque", config_.rt_mode == identity.clinical_mainline_mode && config_.rt_mode != "directTorque" ? "ready" : "policy_blocked", "1 kHz 实时阻抗/位置控制主线", true, true, true));
  modules.push_back(module_entry("rokae::Planner", identity.supports_planner, identity.supports_planner ? "ready" : "unsupported", "S 曲线/点位跟随的上位机路径规划", true, true, false));
  modules.push_back(module_entry("rokae::xMateModel", identity.supports_xmate_model, identity.supports_xmate_model ? (sdk_robot_.xmateModelAvailable() ? "ready" : "degraded") : "unsupported", "正逆解、雅可比、动力学前向计算", true, true, true));
  modules.push_back(module_entry("通信 I/O", true, "ready", "DI/DO/AI/AO、寄存器、xPanel 供电配置", true, true, true));
  modules.push_back(module_entry("RL 工程", true, "ready", "projectsInfo / loadProject / runProject / pauseProject", true, true, true));
  modules.push_back(module_entry("协作功能", identity.supports_drag || identity.supports_path_replay, identity.supports_drag || identity.supports_path_replay ? "ready" : "unsupported", "拖动示教、路径录制/回放、奇异规避", true, true, true));
  std::vector<std::string> blockers; std::vector<std::string> warnings; appendMainlineContractIssuesLocked(&blockers, &warnings);
  return object({
      field("robot_model", quote(identity.robot_model)),
      field("sdk_robot_class", quote(identity.sdk_robot_class)),
      field("controller_version", quote(identity.controller_version)),
      field("preferred_link", quote(config_.preferred_link)),
      field("rt_loop_hz", std::to_string(1000)),
      field("scan_rt_mode", quote(config_.rt_mode)),
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("live_binding_established", boolLiteral(live_binding)),
      field("modules", objectArray(modules)),
      field("blockers", objectArray([&](){ std::vector<std::string> items; for (const auto& b: blockers) items.push_back(summaryEntry("capability", b)); return items; }())),
      field("warnings", objectArray([&](){ std::vector<std::string> items; for (const auto& w: warnings) items.push_back(summaryEntry("capability", w)); return items; }())),
      field("clinical_policy", object({field("mainline_scan_mode", quote(identity.clinical_mainline_mode)), field("direct_torque_allowed", boolLiteral(false)), field("single_control_source_required", boolLiteral(identity.requires_single_control_source))}))
  });
}

std::string CoreRuntime::modelAuthorityContractJsonLocked() const {
  using namespace json;
  const auto snapshot = model_authority_.snapshot(config_, sdk_robot_);
  std::vector<std::string> warnings;
  warnings.reserve(snapshot.warnings.size());
  for (const auto& item : snapshot.warnings) {
    warnings.push_back(summaryEntry("model_authority", item));
  }
  return object({
      field("authoritative_kernel", quote(snapshot.authority_source)),
      field("runtime_source", quote(snapshot.runtime_source)),
      field("family_key", quote(snapshot.family_key)),
      field("family_label", quote(snapshot.family_label)),
      field("robot_model", quote(snapshot.robot_model)),
      field("sdk_robot_class", quote(snapshot.sdk_robot_class)),
      field("planner_supported", boolLiteral(snapshot.planner_supported)),
      field("xmate_model_supported", boolLiteral(snapshot.xmate_model_supported)),
      field("authoritative_precheck", boolLiteral(snapshot.authoritative_precheck)),
      field("authoritative_runtime", boolLiteral(snapshot.authoritative_runtime)),
      field("approximate_advisory_allowed", boolLiteral(snapshot.approximate_advisory_allowed)),
      field("planner_primitives", stringArray(snapshot.planner_primitives)),
      field("model_methods", stringArray(snapshot.model_methods)),
      field("warnings", objectArray(warnings))
  });
}

std::string CoreRuntime::safetyRecoveryContractJsonLocked() const {
  using namespace json;
  const auto snapshot = recovery_kernel_.snapshot(config_, force_limits_, recovery_manager_);
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
  const std::string lifecycle = sdk_robot_.hardwareLifecycleState();
  const bool live_takeover_ready = sdk_robot_.liveTakeoverReady();
  const std::string summary_state = live_takeover_ready ? "ready" : (controller_online_ ? "warning" : "blocked");
  return object({
      field("summary_state", quote(summary_state)),
      field("summary_label", quote(live_takeover_ready ? std::string("hardware lifecycle ready") : std::string("hardware lifecycle contract"))),
      field("detail", quote("Hardware layer owns SDK channels and exposes read/update/write style lifecycle readiness.")),
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("sdk_binding_mode", quote(sdk_robot_.sdkBindingMode())),
      field("lifecycle_state", quote(lifecycle)),
      field("controller_manager_model", quote("hardware_layer__read_update_write")),
      field("transport_ready", boolLiteral(controller_online_)),
      field("motion_channel_ready", boolLiteral(sdk_robot_.motionChannelReady())),
      field("state_channel_ready", boolLiteral(sdk_robot_.stateChannelReady())),
      field("aux_channel_ready", boolLiteral(sdk_robot_.auxChannelReady())),
      field("network_healthy", boolLiteral(sdk_robot_.networkHealthy())),
      field("control_source_exclusive", boolLiteral(sdk_robot_.controlSourceExclusive())),
      field("active_nrt_profile", quote(sdk_robot_.activeNrtProfile())),
      field("active_rt_phase", quote(sdk_robot_.activeRtPhase())),
      field("command_sequence", std::to_string(sdk_robot_.commandSequence())),
      field("live_takeover_ready", boolLiteral(live_takeover_ready)),
      field("single_control_source_required", boolLiteral(config_.requires_single_control_source))
  });
}

std::string CoreRuntime::rtKernelContractJsonLocked() const {
  using namespace json;
  const auto rt = rt_motion_service_.snapshot();
  const std::string summary_state = rt.degraded_without_sdk ? "warning" : "ready";
  return object({
      field("summary_state", quote(summary_state)),
      field("summary_label", quote(rt.degraded_without_sdk ? std::string("rt kernel contract shell") : std::string("rt kernel measured"))),
      field("detail", quote("RT kernel follows read/update/write staging around the official SDK controller callback.")),
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
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
      field("max_cycle_ms", formatDouble(rt.max_cycle_ms)),
      field("last_wake_jitter_ms", formatDouble(rt.last_wake_jitter_ms)),
      field("last_sensor_decision", quote(rt.last_sensor_decision)),
      field("jitter_budget_ms", formatDouble(rt.jitter_budget_ms)),
      field("freshness_budget_ms", std::to_string(config_.pressure_stale_ms)),
      field("reference_limits", object({field("max_cart_step_mm", formatDouble(2.5)), field("max_force_delta_n", formatDouble(1.0))})),
      field("degraded_without_sdk", boolLiteral(rt.degraded_without_sdk))
  });
}

std::string CoreRuntime::sessionDriftContractJsonLocked() const {
  using namespace json;
  const bool session_locked = !session_id_.empty();
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
      field("locked_scan_plan_hash", quote(locked_scan_plan_hash_)),
      field("active_plan_hash", quote(plan_hash_)),
      field("drifts", objectArray(drifts))
  });
}

std::string CoreRuntime::controlGovernanceContractJsonLocked() const {
  using namespace json;
  const bool session_locked = !session_id_.empty();
  const bool session_binding_valid = sessionFreezeConsistentLocked();
  const bool rt_ready = controller_online_ && powered_ && automatic_mode_ && config_.rt_mode == "cartesianImpedance";
  const auto rt_snapshot = rt_motion_service_.snapshot();
  const auto nrt_snapshot = nrt_motion_service_.snapshot();
  return object({
      field("single_control_source_required", boolLiteral(config_.requires_single_control_source)),
      field("control_authority_expected_source", quote("cpp_robot_core")),
      field("write_surface", quote("core_runtime_only")),
      field("current_execution_state", quote(stateName(execution_state_))),
      field("controller_online", boolLiteral(controller_online_)),
      field("powered", boolLiteral(powered_)),
      field("automatic_mode", boolLiteral(automatic_mode_)),
      field("session_binding_valid", boolLiteral(session_binding_valid)),
      field("runtime_config_bound", boolLiteral(session_locked)),
      field("session_id", quote(session_id_)),
      field("active_plan_hash", quote(plan_hash_)),
      field("locked_scan_plan_hash", quote(locked_scan_plan_hash_)),
      field("tool_ready", boolLiteral(tool_ready_)),
      field("tcp_ready", boolLiteral(tcp_ready_)),
      field("load_ready", boolLiteral(load_ready_)),
      field("nrt_ready", boolLiteral(controller_online_ && powered_)),
      field("rt_ready", boolLiteral(rt_ready)),
      field("lifecycle_state", quote(sdk_robot_.hardwareLifecycleState())),
      field("rt_loop_active", boolLiteral(rt_snapshot.loop_active)),
      field("rt_move_active", boolLiteral(rt_snapshot.move_active)),
      field("nrt_last_command", quote(nrt_snapshot.last_command)),
      field("detail", quote("single control source contract requires session freeze + AUTO + powered + cartesianImpedance mainline"))
  });
}

std::string CoreRuntime::controllerEvidenceJsonLocked() const {
  using namespace json;
  const auto logs = sdk_robot_.controllerLogs();
  const auto cfg_logs = sdk_robot_.configurationLog();
  std::vector<std::string> log_tail;
  for (const auto& item : logs) {
    log_tail.push_back(object({field("level", quote("INFO")), field("source", quote("sdk")), field("message", quote(item))}));
  }
  std::vector<std::string> cfg_tail;
  for (const auto& item : cfg_logs) {
    cfg_tail.push_back(quote(item));
  }
  const auto rl_status = sdk_robot_.rlStatus();
  const auto drag = sdk_robot_.dragState();
  return object({
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("last_event", quote(stateName(execution_state_))),
      field("last_transition", quote(last_transition_)),
      field("state_reason", quote(state_reason_)),
      field("last_controller_log", quote(logs.empty() ? std::string("") : logs.back())),
      field("controller_log_tail", objectArray(log_tail)),
      field("configuration_log_tail", stringArray(cfg_logs)),
      field("rl_status", object({field("loaded_project", quote(rl_status.loaded_project)), field("loaded_task", quote(rl_status.loaded_task)), field("running", boolLiteral(rl_status.running)), field("rate", formatDouble(rl_status.rate)), field("loop", boolLiteral(rl_status.loop))})),
      field("drag_state", object({field("enabled", boolLiteral(drag.enabled)), field("space", quote(drag.space)), field("type", quote(drag.type))})),
      field("registers", object({field("segment", std::to_string(active_segment_)), field("frame", std::to_string(frame_id_)), field("command_sequence", std::to_string(sdk_robot_.commandSequence()))})),
      field("fault_code", quote(fault_code_)),
      field("pending_alarm_count", std::to_string(static_cast<int>(pending_alarms_.size()))),
      field("last_nrt_profile", quote(nrt_motion_service_.snapshot().active_profile)),
      field("last_rt_phase", quote(rt_motion_service_.snapshot().phase)),
      field("reason_chain", stringArray({stateName(execution_state_), state_reason_, last_transition_, fault_code_}))
  });
}


std::string CoreRuntime::dualStateMachineContractJsonLocked() const {
  using namespace json;
  const std::string runtime_state = stateName(execution_state_);
  std::string clinical_state = "boot";
  if (runtime_state == "CONNECTED" || runtime_state == "POWERED" || runtime_state == "AUTO_READY") clinical_state = "startup";
  else if (runtime_state == "SESSION_LOCKED") clinical_state = "session_locked";
  else if (runtime_state == "PATH_VALIDATED") clinical_state = "plan_validated";
  else if (runtime_state == "APPROACHING") clinical_state = "approaching";
  else if (runtime_state == "CONTACT_SEEKING") clinical_state = "seek_contact";
  else if (runtime_state == "CONTACT_STABLE") clinical_state = "contact_stable";
  else if (runtime_state == "SCANNING") clinical_state = "scan_follow";
  else if (runtime_state == "PAUSED_HOLD") clinical_state = "paused_hold";
  else if (runtime_state == "RETREATING" || runtime_state == "RECOVERY_RETRACT") clinical_state = "controlled_retract";
  else if (runtime_state == "SCAN_COMPLETE") clinical_state = "completed";
  else if (runtime_state == "FAULT") clinical_state = "fault";
  else if (runtime_state == "ESTOP") clinical_state = "estop";
  const bool aligned = !(runtime_state == "SCANNING" && clinical_state != "scan_follow");
  return object({
      field("summary_state", quote(aligned ? std::string("ready") : std::string("blocked"))),
      field("summary_label", quote(aligned ? std::string("双层状态机已对齐") : std::string("双层状态机冲突"))),
      field("detail", quote(aligned ? std::string("执行状态机与临床任务状态机已通过映射规则对齐。") : std::string("runtime 与 clinical task state 不一致。"))),
      field("runtime_state", quote(runtime_state)),
      field("clinical_task_state", quote(clinical_state)),
      field("execution_and_clinical_aligned", boolLiteral(aligned)),
      field("execution_permissions", object({
          field("allow_nrt", boolLiteral(execution_state_ == RobotCoreState::AutoReady || execution_state_ == RobotCoreState::SessionLocked || execution_state_ == RobotCoreState::PathValidated || execution_state_ == RobotCoreState::ScanComplete)),
          field("allow_rt_seek", boolLiteral(execution_state_ == RobotCoreState::PathValidated || execution_state_ == RobotCoreState::Approaching || execution_state_ == RobotCoreState::ContactSeeking)),
          field("allow_rt_scan", boolLiteral(execution_state_ == RobotCoreState::ContactStable || execution_state_ == RobotCoreState::Scanning || execution_state_ == RobotCoreState::PausedHold)),
          field("allow_retract", boolLiteral(execution_state_ != RobotCoreState::Boot && execution_state_ != RobotCoreState::Disconnected && execution_state_ != RobotCoreState::Estop))
      }))
  });
}

std::string CoreRuntime::mainlineExecutorContractJsonLocked() const {
  using namespace json;
  const auto rt = rt_motion_service_.snapshot();
  const auto nrt = nrt_motion_service_.snapshot();
  std::vector<std::string> templates;
  for (const auto& profile : nrt.templates) {
    templates.push_back(object({field("name", quote(profile.name)), field("sdk_command", quote(profile.sdk_command)), field("blocking", boolLiteral(true)), field("requires_auto_mode", boolLiteral(profile.requires_auto_mode)), field("requires_move_reset", boolLiteral(profile.requires_move_reset)), field("delegates_to_sdk", boolLiteral(profile.delegates_to_sdk))}));
  }
  const bool task_tree_aligned = !(stateName(execution_state_) == "SCANNING" && rt.phase != "scan_follow");
  return object({
      field("summary_state", quote(task_tree_aligned ? std::string("ready") : std::string("blocked"))),
      field("summary_label", quote(task_tree_aligned ? std::string("主线执行器已对齐") : std::string("主线执行器未对齐"))),
      field("detail", quote("NRT/RT executor 只表达意图、阶段与监测器；真实执行委托给官方 SDK。")),
      field("task_tree_aligned", boolLiteral(task_tree_aligned)),
      field("nrt_executor", object({
          field("summary_state", quote(nrt.degraded_without_sdk ? std::string("warning") : std::string("ready"))),
          field("detail", quote("NRT executor delegates MoveAbsJ/MoveL templates to the official SDK planner.")),
          field("sdk_delegation_only", boolLiteral(nrt.sdk_delegation_only)),
          field("requires_move_reset", boolLiteral(nrt.requires_move_reset)),
          field("requires_single_control_source", boolLiteral(nrt.requires_single_control_source)),
          field("last_command_id", quote(nrt.last_command_id)),
          field("last_result", quote(nrt.last_result)),
          field("templates", objectArray(templates))
      })),
      field("rt_executor", object({
          field("summary_state", quote(rt.degraded_without_sdk ? std::string("warning") : std::string("ready"))),
          field("detail", quote("RT executor wraps cartesianImpedance mainline with limiter/guard semantics.")),
          field("phase", quote(rt.phase)),
          field("phase_group", quote(rt.phase_group)),
          field("reference_limiter_enabled", boolLiteral(rt.reference_limiter_enabled)),
          field("freshness_guard_enabled", boolLiteral(rt.freshness_guard_enabled)),
          field("jitter_monitor_enabled", boolLiteral(rt.jitter_monitor_enabled)),
          field("contact_band_monitor_enabled", boolLiteral(rt.contact_band_monitor_enabled)),
          field("network_guard_enabled", boolLiteral(rt.network_guard_enabled)),
          field("fixed_period_enforced", boolLiteral(rt.fixed_period_enforced)),
          field("network_healthy", boolLiteral(rt.network_healthy)),
          field("overrun_count", std::to_string(rt.overrun_count)),
          field("nominal_loop_hz", std::to_string(rt.nominal_loop_hz))
      }))
  });
}

std::string CoreRuntime::releaseContractJsonLocked() const {
  using namespace json;
  const auto safety = evaluateSafetyLocked();
  const bool freeze_consistent = sessionFreezeConsistentLocked();
  const bool compile_ready = last_final_verdict_.accepted && freeze_consistent;
  std::vector<std::string> blockers; std::vector<std::string> warnings; appendMainlineContractIssuesLocked(&blockers, &warnings);
  for (const auto& item : last_final_verdict_.blockers) blockers.push_back(item);
  for (const auto& item : last_final_verdict_.warnings) warnings.push_back(item);
  const bool release_allowed = compile_ready && safety.active_interlocks.empty();
  return object({
      field("summary_state", quote(release_allowed ? std::string("ready") : std::string("blocked"))),
      field("session_locked", boolLiteral(!session_id_.empty())),
      field("session_freeze_consistent", boolLiteral(freeze_consistent)),
      field("locked_scan_plan_hash", quote(locked_scan_plan_hash_)),
      field("active_plan_hash", quote(plan_hash_)),
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("compile_ready", boolLiteral(compile_ready)),
      field("ready_for_approach", boolLiteral(compile_ready && execution_state_ == RobotCoreState::PathValidated)),
      field("ready_for_scan", boolLiteral(compile_ready && execution_state_ == RobotCoreState::ContactStable)),
      field("release_recommendation", quote(release_allowed ? std::string("allow") : std::string("block"))),
      field("active_interlocks", stringArray(safety.active_interlocks)),
      field("final_verdict", object({field("accepted", boolLiteral(last_final_verdict_.accepted)), field("policy_state", quote(last_final_verdict_.policy_state)), field("reason", quote(last_final_verdict_.reason)), field("evidence_id", quote(last_final_verdict_.evidence_id))})),
      field("blockers", objectArray([&](){ std::vector<std::string> items; for (const auto& b: blockers) items.push_back(summaryEntry("release", b)); return items; }())),
      field("warnings", objectArray([&](){ std::vector<std::string> items; for (const auto& w: warnings) items.push_back(summaryEntry("release", w)); return items; }())),
      field("active_injections", stringArray([&](){ std::vector<std::string> items(injected_faults_.begin(), injected_faults_.end()); return items; }()))
  });
}

std::string CoreRuntime::deploymentContractJsonLocked() const {
  using namespace json;
  const auto identity = resolveRobotIdentity(config_.robot_model, config_.sdk_robot_class, config_.axis_count);
  return object({
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("vendored_sdk_required", boolLiteral(true)),
      field("vendored_sdk_detected", boolLiteral(sdk_robot_.sdkAvailable())),
      field("live_binding_established", boolLiteral(sdk_robot_.liveBindingEstablished())),
      field("xmate_model_detected", boolLiteral(sdk_robot_.xmateModelAvailable())),
      field("preferred_link", quote(identity.preferred_link)),
      field("single_control_source_required", boolLiteral(identity.requires_single_control_source)),
      field("required_host_dependencies", stringArray({"cmake", "g++/clang++", "openssl headers", "eigen headers"})),
      field("required_runtime_materials", stringArray({"configs/tls/runtime/*", "vendored librokae include/lib/external"})),
      field("bringup_sequence", stringArray({"doctor_runtime.py", "generate_dev_tls_cert.sh", "start_real.sh", "run.py --backend core"})),
      field("systemd_units", stringArray({"spine-cpp-core.service", "spine-python-api.service", "spine-ultrasound.target"})),
      field("summary_label", quote("cpp deployment contract"))
  });
}

std::string CoreRuntime::faultInjectionContractJsonLocked() const {
  using namespace json;
  const std::vector<std::string> catalog{
      object({field("name", quote("pressure_stale")), field("effect", quote("forces stale telemetry watchdog and estop path")), field("phase_scope", stringArray({"CONTACT_SEEKING", "SCANNING", "PAUSED_HOLD"})), field("recoverable", boolLiteral(false))}),
      object({field("name", quote("rt_jitter_high")), field("effect", quote("marks RT jitter interlock active")), field("phase_scope", stringArray({"CONTACT_SEEKING", "SCANNING", "PAUSED_HOLD"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("overpressure")), field("effect", quote("forces pressure above upper bound and pause/retreat logic")), field("phase_scope", stringArray({"CONTACT_STABLE", "SCANNING"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("collision_event")), field("effect", quote("injects recoverable collision alarm and retreat")), field("phase_scope", stringArray({"APPROACHING", "CONTACT_SEEKING", "SCANNING"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("plan_hash_mismatch")), field("effect", quote("breaks locked plan hash consistency")), field("phase_scope", stringArray({"SESSION_LOCKED", "PATH_VALIDATED"})), field("recoverable", boolLiteral(true))}),
      object({field("name", quote("estop_latch")), field("effect", quote("forces ESTOP latched state")), field("phase_scope", stringArray({"*"})), field("recoverable", boolLiteral(false))}),
  };
  return object({
      field("runtime_source", quote(sdk_robot_.runtimeSource())),
      field("enabled", boolLiteral(true)),
      field("simulation_only", boolLiteral(true)),
      field("active_injections", stringArray([&](){ std::vector<std::string> items(injected_faults_.begin(), injected_faults_.end()); return items; }())),
      field("catalog", objectArray(catalog))
  });
}

bool CoreRuntime::applyFaultInjectionLocked(const std::string& fault_name, std::string* error_message) {
  if (fault_name.empty()) {
    if (error_message != nullptr) {
      *error_message = "fault_name missing";
    }
    return false;
  }

  injected_faults_.insert(fault_name);
  if (fault_name == "pressure_stale") {
    pressure_fresh_ = false;
    devices_[2].fresh = false;
    queueAlarmLocked("FAULT", "fault_injection", "压力遥测已被注入为 stale", "fault_injection");
    return true;
  }
  if (fault_name == "rt_jitter_high") {
    rt_jitter_ok_ = false;
    queueAlarmLocked("WARNING", "fault_injection", "RT jitter interlock injected", "fault_injection");
    return true;
  }
  if (fault_name == "overpressure") {
    pressure_current_ = std::max(config_.pressure_upper + 0.5, force_limits_.max_z_force_n + 0.5);
    queueAlarmLocked("WARNING", "fault_injection", "Overpressure injected", "fault_injection", "", "safe_retreat");
    return true;
  }
  if (fault_name == "collision_event") {
    execution_state_ = RobotCoreState::Retreating;
    retreat_ticks_remaining_ = std::max(retreat_ticks_remaining_, 10);
    queueAlarmLocked("RECOVERABLE_FAULT", "collision", "模拟碰撞事件", "fault_injection", "", "safe_retreat");
    return true;
  }
  if (fault_name == "plan_hash_mismatch") {
    plan_hash_ = std::string("mismatch:") + (plan_hash_.empty() ? "empty" : plan_hash_);
    return true;
  }
  if (fault_name == "estop_latch") {
    execution_state_ = RobotCoreState::Estop;
    fault_code_ = "ESTOP_INJECTED";
    queueAlarmLocked("FAULT", "fault_injection", "ESTOP latched by fault injection", "fault_injection");
    return true;
  }

  injected_faults_.erase(fault_name);
  if (error_message != nullptr) {
    *error_message = std::string("unsupported fault injection: ") + fault_name;
  }
  return false;
}

void CoreRuntime::clearInjectedFaultsLocked() {
  injected_faults_.clear();
  rt_jitter_ok_ = true;
  pressure_fresh_ = true;
  devices_[2].fresh = devices_[2].online;
  if (execution_state_ == RobotCoreState::Estop && fault_code_ == "ESTOP_INJECTED") {
    if (automatic_mode_ && powered_) {
      execution_state_ = RobotCoreState::AutoReady;
    } else if (powered_) {
      execution_state_ = RobotCoreState::Powered;
    } else if (controller_online_) {
      execution_state_ = RobotCoreState::Connected;
    } else {
      execution_state_ = RobotCoreState::Disconnected;
    }
    fault_code_.clear();
  }
  queueAlarmLocked("INFO", "fault_injection", "fault injections cleared", "fault_injection");
}


std::string CoreRuntime::authoritativeRuntimeEnvelopeJsonLocked() const {
  using namespace json;
  std::vector<std::string> blockers;
  std::vector<std::string> warnings;
  appendMainlineContractIssuesLocked(&blockers, &warnings);
  const auto runtime_cfg = sdk_robot_.runtimeConfig();
  const std::string authority_state = controller_online_ ? (blockers.empty() ? std::string("ready") : std::string("blocked")) : std::string("degraded");
  std::vector<std::string> blocker_entries;
  blocker_entries.reserve(blockers.size());
  for (const auto& item : blockers) blocker_entries.push_back(summaryEntry("runtime_authority", item));
  std::vector<std::string> warning_entries;
  warning_entries.reserve(warnings.size());
  for (const auto& item : warnings) warning_entries.push_back(summaryEntry("runtime_authority", item));
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
      field("rt_mode", quote(config_.rt_mode)),
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
  const auto control_authority = object({
      field("summary_state", quote(authority_state)),
      field("summary_label", quote(authority_state == "ready" ? std::string("runtime authority ready") : (authority_state == "blocked" ? std::string("runtime authority blocked") : std::string("runtime authority degraded")))),
      field("detail", quote("cpp_robot_core publishes the authoritative execution/control snapshot")),
      field("owner", object({
          field("actor_id", quote("cpp-runtime")),
          field("workspace", quote("runtime")),
          field("role", quote("runtime")),
          field("session_id", quote(session_id_))
      })),
      field("active_lease", object({
          field("lease_id", quote("cpp-runtime-authority")),
          field("actor_id", quote("cpp-runtime")),
          field("workspace", quote("runtime")),
          field("role", quote("runtime")),
          field("session_id", quote(session_id_)),
          field("expires_in_s", std::to_string(0)),
          field("source", quote("cpp_robot_core"))
      })),
      field("owner_provenance", object({field("source", quote("cpp_robot_core"))})),
      field("workspace_binding", quote("runtime")),
      field("session_binding", quote(session_id_)),
      field("blockers", objectArray(blocker_entries)),
      field("warnings", objectArray(warning_entries))
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
      field("runtime_config_applied", applied_runtime_config),
      field("session_freeze", session_freeze),
      field("plan_digest", plan_digest),
      field("final_verdict", finalVerdictJson(last_final_verdict_))
  });
}

std::string CoreRuntime::finalVerdictJson(const FinalVerdict& verdict) const {
  using namespace json;
  std::vector<std::string> blocker_entries;
  blocker_entries.reserve(verdict.blockers.size());
  for (const auto& item : verdict.blockers) {
    blocker_entries.push_back(summaryEntry("model_precheck", item));
  }
  std::vector<std::string> warning_entries;
  warning_entries.reserve(verdict.warnings.size());
  for (const auto& item : verdict.warnings) {
    warning_entries.push_back(summaryEntry("model_precheck", item));
  }
  return object({
      field("summary_state", quote(verdict.policy_state.empty() ? std::string("idle") : verdict.policy_state)),
      field("summary_label", quote(verdict.summary_label.empty() ? std::string("运行时前检") : verdict.summary_label)),
      field("detail", quote(verdict.detail.empty() ? verdict.reason : verdict.detail)),
      field("warnings", objectArray(warning_entries)),
      field("blockers", objectArray(blocker_entries)),
      field("authority_source", quote(verdict.source.empty() ? std::string("cpp_robot_core") : verdict.source)),
      field("verdict_kind", quote("final")),
      field("approximate", boolLiteral(false)),
      field("final_verdict", object({
          field("accepted", boolLiteral(verdict.accepted)),
          field("reason", quote(verdict.reason)),
          field("evidence_id", quote(verdict.evidence_id)),
          field("expected_state_delta", object({field("next_state", quote(verdict.next_state.empty() ? std::string("replan_required") : verdict.next_state))})),
          field("policy_state", quote(verdict.policy_state.empty() ? std::string("idle") : verdict.policy_state)),
          field("source", quote(verdict.source.empty() ? std::string("cpp_robot_core") : verdict.source)),
          field("advisory_only", boolLiteral(verdict.advisory_only)),
      })),
      field("plan_metrics", object({
          field("plan_id", quote(verdict.plan_id)),
          field("plan_hash", quote(verdict.plan_hash)),
      })),
  });
}

std::string CoreRuntime::replyJson(const std::string& request_id, bool ok, const std::string& message, const std::string& data_json) const {
  using namespace json;
  return object({
      field("ok", boolLiteral(ok)),
      field("message", quote(message)),
      field("request_id", quote(request_id)),
      field("data", data_json),
      field("protocol_version", std::to_string(kProtocolVersion)),
  });
}

}  // namespace robot_core
