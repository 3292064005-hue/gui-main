#include "robot_core/core_runtime.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <unordered_map>

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

DeviceHealth makeDevice(const std::string& name, bool online, const std::string& detail) {
  DeviceHealth device;
  device.device_name = name;
  device.online = online;
  device.fresh = online;
  device.detail = detail;
  return device;
}

std::vector<double> filledVector(size_t count, double value) {
  return std::vector<double>(count, value);
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
  return json::object(std::vector<std::string>{
      json::field("name", json::quote(name)),
      json::field("detail", json::quote(detail)),
  });
}

std::string logEntryJson(const std::string& level, const std::string& source, const std::string& message) {
  return json::object(std::vector<std::string>{
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
    entries.push_back(json::object(std::vector<std::string>{
        json::field("name", json::quote(project.name)),
        json::field("tasks", json::stringArray(project.tasks)),
    }));
  }
  return objectArray(entries);
}

std::string pathArrayJson(const std::vector<SdkRobotPathInfo>& paths) {
  std::vector<std::string> entries;
  for (const auto& path : paths) {
    entries.push_back(json::object(std::vector<std::string>{
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
    entries.push_back(json::object(std::vector<std::string>{
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

CoreRuntime::CoreRuntime() {
  nrt_motion_service_.bind(&sdk_robot_);
  rt_motion_service_.bindSdkFacade(&sdk_robot_);
  devices_ = {
      makeDevice("robot", false, "机械臂控制器未连接"),
      makeDevice("camera", false, "摄像头未连接"),
      makeDevice("pressure", false, "压力传感器未连接"),
      makeDevice("ultrasound", false, "超声设备未连接"),
  };
  recovery_manager_.setRetrySettleWindow(std::chrono::milliseconds(static_cast<int>(force_limits_.force_settle_window_ms)));
}

CoreRuntime::RuntimeLane CoreRuntime::commandLaneFor(std::string_view command) const {
  static const std::unordered_map<std::string_view, RuntimeLane> command_lanes = {
      {"query_controller_log", RuntimeLane::Query},
      {"query_rl_projects", RuntimeLane::Query},
      {"query_path_lists", RuntimeLane::Query},
      {"get_io_snapshot", RuntimeLane::Query},
      {"get_register_snapshot", RuntimeLane::Query},
      {"get_safety_config", RuntimeLane::Query},
      {"get_motion_contract", RuntimeLane::Query},
      {"get_runtime_alignment", RuntimeLane::Query},
      {"get_xmate_model_summary", RuntimeLane::Query},
      {"get_sdk_runtime_config", RuntimeLane::Query},
      {"get_identity_contract", RuntimeLane::Query},
      {"get_robot_family_contract", RuntimeLane::Query},
      {"get_vendor_boundary_contract", RuntimeLane::Query},
      {"get_clinical_mainline_contract", RuntimeLane::Query},
      {"get_session_drift_contract", RuntimeLane::Query},
      {"get_hardware_lifecycle_contract", RuntimeLane::Query},
      {"get_rt_kernel_contract", RuntimeLane::Query},
      {"get_session_freeze", RuntimeLane::Query},
      {"get_authoritative_runtime_envelope", RuntimeLane::Query},
      {"get_control_governance_contract", RuntimeLane::Query},
      {"get_controller_evidence", RuntimeLane::Query},
      {"get_dual_state_machine_contract", RuntimeLane::Query},
      {"get_mainline_executor_contract", RuntimeLane::Query},
      {"get_recovery_contract", RuntimeLane::Query},
      {"get_safety_recovery_contract", RuntimeLane::Query},
      {"get_capability_contract", RuntimeLane::Query},
      {"get_model_authority_contract", RuntimeLane::Query},
      {"get_release_contract", RuntimeLane::Query},
      {"get_deployment_contract", RuntimeLane::Query},
      {"get_fault_injection_contract", RuntimeLane::Query},
      {"validate_setup", RuntimeLane::Query},
      {"query_final_verdict", RuntimeLane::Query},
      {"seek_contact", RuntimeLane::RtControl},
      {"start_scan", RuntimeLane::RtControl},
      {"pause_scan", RuntimeLane::RtControl},
      {"resume_scan", RuntimeLane::RtControl},
      {"safe_retreat", RuntimeLane::RtControl},
  };
  const auto it = command_lanes.find(command);
  return it == command_lanes.end() ? RuntimeLane::Command : it->second;
}

std::string CoreRuntime::handleCommandJson(const std::string& line) {
  const auto request_id = json::extractString(line, "request_id");
  const auto command = json::extractString(line, "command");
  using CommandHandler = std::string (CoreRuntime::*)(const std::string&, const std::string&);
  static const std::unordered_map<std::string, CommandHandler> command_handlers = {
      {"connect_robot", &CoreRuntime::handleConnectionCommand},
      {"disconnect_robot", &CoreRuntime::handleConnectionCommand},
      {"power_on", &CoreRuntime::handlePowerModeCommand},
      {"power_off", &CoreRuntime::handlePowerModeCommand},
      {"set_auto_mode", &CoreRuntime::handlePowerModeCommand},
      {"set_manual_mode", &CoreRuntime::handlePowerModeCommand},
      {"validate_setup", &CoreRuntime::handleValidationCommand},
      {"compile_scan_plan", &CoreRuntime::handleValidationCommand},
      {"query_final_verdict", &CoreRuntime::handleValidationCommand},
      {"query_controller_log", &CoreRuntime::handleQueryCommand},
      {"query_rl_projects", &CoreRuntime::handleQueryCommand},
      {"query_path_lists", &CoreRuntime::handleQueryCommand},
      {"get_io_snapshot", &CoreRuntime::handleQueryCommand},
      {"get_register_snapshot", &CoreRuntime::handleQueryCommand},
      {"get_safety_config", &CoreRuntime::handleQueryCommand},
      {"get_motion_contract", &CoreRuntime::handleQueryCommand},
      {"get_runtime_alignment", &CoreRuntime::handleQueryCommand},
      {"get_xmate_model_summary", &CoreRuntime::handleQueryCommand},
      {"get_sdk_runtime_config", &CoreRuntime::handleQueryCommand},
      {"get_identity_contract", &CoreRuntime::handleQueryCommand},
      {"get_robot_family_contract", &CoreRuntime::handleQueryCommand},
      {"get_vendor_boundary_contract", &CoreRuntime::handleQueryCommand},
      {"get_clinical_mainline_contract", &CoreRuntime::handleQueryCommand},
      {"get_session_drift_contract", &CoreRuntime::handleQueryCommand},
      {"get_hardware_lifecycle_contract", &CoreRuntime::handleQueryCommand},
      {"get_rt_kernel_contract", &CoreRuntime::handleQueryCommand},
      {"get_session_freeze", &CoreRuntime::handleQueryCommand},
      {"get_authoritative_runtime_envelope", &CoreRuntime::handleQueryCommand},
      {"get_control_governance_contract", &CoreRuntime::handleQueryCommand},
      {"get_controller_evidence", &CoreRuntime::handleQueryCommand},
      {"get_dual_state_machine_contract", &CoreRuntime::handleQueryCommand},
      {"get_mainline_executor_contract", &CoreRuntime::handleQueryCommand},
      {"get_recovery_contract", &CoreRuntime::handleQueryCommand},
      {"get_safety_recovery_contract", &CoreRuntime::handleQueryCommand},
      {"get_capability_contract", &CoreRuntime::handleQueryCommand},
      {"get_model_authority_contract", &CoreRuntime::handleQueryCommand},
      {"get_release_contract", &CoreRuntime::handleQueryCommand},
      {"get_deployment_contract", &CoreRuntime::handleQueryCommand},
      {"get_fault_injection_contract", &CoreRuntime::handleQueryCommand},
      {"inject_fault", &CoreRuntime::handleFaultInjectionCommand},
      {"clear_injected_faults", &CoreRuntime::handleFaultInjectionCommand},
      {"lock_session", &CoreRuntime::handleSessionCommand},
      {"load_scan_plan", &CoreRuntime::handleSessionCommand},
      {"approach_prescan", &CoreRuntime::handleExecutionCommand},
      {"seek_contact", &CoreRuntime::handleExecutionCommand},
      {"start_scan", &CoreRuntime::handleExecutionCommand},
      {"pause_scan", &CoreRuntime::handleExecutionCommand},
      {"resume_scan", &CoreRuntime::handleExecutionCommand},
      {"safe_retreat", &CoreRuntime::handleExecutionCommand},
      {"go_home", &CoreRuntime::handleExecutionCommand},
      {"run_rl_project", &CoreRuntime::handleExecutionCommand},
      {"pause_rl_project", &CoreRuntime::handleExecutionCommand},
      {"enable_drag", &CoreRuntime::handleExecutionCommand},
      {"disable_drag", &CoreRuntime::handleExecutionCommand},
      {"replay_path", &CoreRuntime::handleExecutionCommand},
      {"start_record_path", &CoreRuntime::handleExecutionCommand},
      {"stop_record_path", &CoreRuntime::handleExecutionCommand},
      {"cancel_record_path", &CoreRuntime::handleExecutionCommand},
      {"save_record_path", &CoreRuntime::handleExecutionCommand},
      {"clear_fault", &CoreRuntime::handleExecutionCommand},
      {"emergency_stop", &CoreRuntime::handleExecutionCommand},
  };
  const auto handler_it = command_handlers.find(command);
  if (handler_it == command_handlers.end()) {
    return replyJson(request_id, false, "unsupported command: " + command);
  }
  const auto lane = commandLaneFor(command);
  if (lane == RuntimeLane::Query) {
    std::lock_guard<std::mutex> lane_lock(query_lane_mutex_);
    return (this->*(handler_it->second))(request_id, line);
  }
  if (lane == RuntimeLane::RtControl) {
    std::lock_guard<std::mutex> lane_lock(rt_lane_mutex_);
    return (this->*(handler_it->second))(request_id, line);
  }
  std::lock_guard<std::mutex> lane_lock(command_lane_mutex_);
  return (this->*(handler_it->second))(request_id, line);
}

std::string CoreRuntime::handleConnectionCommand(const std::string& request_id, const std::string& line) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto command = json::extractString(line, "command");
  if (command == "connect_robot") {
    if (execution_state_ != RobotCoreState::Boot && execution_state_ != RobotCoreState::Disconnected) {
      return replyJson(request_id, false, "robot already connected");
    }
    const auto remote_ip = json::extractString(line, "remote_ip", sdk_robot_.queryPort().runtimeConfig().remote_ip);
    const auto local_ip = json::extractString(line, "local_ip", sdk_robot_.queryPort().runtimeConfig().local_ip);
    if (!sdk_robot_.lifecyclePort().connect(remote_ip, local_ip)) {
      return replyJson(request_id, false, "connect_robot failed");
    }
    controller_online_ = true;
    execution_state_ = RobotCoreState::Connected;
    devices_[0] = makeDevice("robot", true, std::string("robot_core 已连接 / source=") + sdk_robot_.queryPort().runtimeSource());
    devices_[1] = makeDevice("camera", true, "摄像头在线");
    devices_[2] = makeDevice("pressure", true, "压力传感器在线");
    devices_[3] = makeDevice("ultrasound", true, "超声设备在线");
    return replyJson(request_id, true, "connect_robot accepted");
  }
  if (command == "disconnect_robot") {
    recording_service_.closeSession();
    sdk_robot_.lifecyclePort().disconnect();
    execution_state_ = RobotCoreState::Disconnected;
    controller_online_ = false;
    powered_ = false;
    automatic_mode_ = false;
    tool_ready_ = false;
    tcp_ready_ = false;
    load_ready_ = false;
    pressure_fresh_ = false;
    robot_state_fresh_ = false;
    rt_jitter_ok_ = true;
    fault_code_.clear();
    session_id_.clear();
    session_dir_.clear();
    plan_id_.clear();
    plan_hash_.clear();
    locked_scan_plan_hash_.clear();
    plan_loaded_ = false;
    total_points_ = 0;
    total_segments_ = 0;
    path_index_ = 0;
    frame_id_ = 0;
    active_segment_ = 0;
    active_waypoint_index_ = 0;
    retreat_ticks_remaining_ = 0;
    progress_pct_ = 0.0;
    pressure_current_ = 0.0;
    contact_stable_since_ns_ = 0;
    last_transition_.clear();
    state_reason_.clear();
    contact_state_ = ContactTelemetry{};
    pending_alarms_.clear();
    recovery_manager_.resetToIdle();
    last_final_verdict_ = FinalVerdict{};
    injected_faults_.clear();
    devices_ = {
        makeDevice("robot", false, "机械臂控制器未连接"),
        makeDevice("camera", false, "摄像头未连接"),
        makeDevice("pressure", false, "压力传感器未连接"),
        makeDevice("ultrasound", false, "超声设备未连接"),
    };
    return replyJson(request_id, true, "disconnect_robot accepted");
  }
  return replyJson(request_id, false, "unsupported command: " + command);
}

std::string CoreRuntime::handleQueryCommand(const std::string& request_id, const std::string& line) {
  std::lock_guard<std::mutex> state_lock(state_mutex_);
  const auto command = json::extractString(line, "command");
  if (command == "query_controller_log") {
    std::vector<std::string> entries;
    for (const auto& item : sdk_robot_.queryPort().controllerLogs()) {
      entries.push_back(logEntryJson("INFO", "sdk", item));
    }
    return replyJson(request_id, true, "query_controller_log accepted", json::object(std::vector<std::string>{json::field("logs", objectArray(entries))}));
  }
  if (command == "query_rl_projects") {
    const auto projects = projectArrayJson(sdk_robot_.queryPort().rlProjects());
    const auto rl_status = sdk_robot_.queryPort().rlStatus();
    const auto status = json::object(std::vector<std::string>{
        json::field("loaded_project", json::quote(rl_status.loaded_project)),
        json::field("loaded_task", json::quote(rl_status.loaded_task)),
        json::field("running", json::boolLiteral(rl_status.running)),
        json::field("rate", json::formatDouble(rl_status.rate)),
        json::field("loop", json::boolLiteral(rl_status.loop)),
    });
    return replyJson(request_id, true, "query_rl_projects accepted", json::object(std::vector<std::string>{json::field("projects", projects), json::field("status", status)}));
  }
  if (command == "query_path_lists") {
    const auto paths = pathArrayJson(sdk_robot_.queryPort().pathLibrary());
    const auto drag_state = sdk_robot_.queryPort().dragState();
    const auto drag = json::object(std::vector<std::string>{
        json::field("enabled", json::boolLiteral(drag_state.enabled)),
        json::field("space", json::quote(drag_state.space)),
        json::field("type", json::quote(drag_state.type)),
    });
    return replyJson(request_id, true, "query_path_lists accepted", json::object(std::vector<std::string>{json::field("paths", paths), json::field("drag", drag)}));
  }
  if (command == "get_io_snapshot") {
    const auto data = json::object(std::vector<std::string>{
        json::field("di", boolMapJson(sdk_robot_.queryPort().di())),
        json::field("do", boolMapJson(sdk_robot_.queryPort().doState())),
        json::field("ai", doubleMapJson(sdk_robot_.queryPort().ai())),
        json::field("ao", doubleMapJson(sdk_robot_.queryPort().ao())),
        json::field("registers", intMapJson(sdk_robot_.queryPort().registers())),
        json::field("xpanel_vout_mode", json::quote(config_.xpanel_vout_mode)),
    });
    return replyJson(request_id, true, "get_io_snapshot accepted", data);
  }
  if (command == "get_register_snapshot") {
    const auto data = json::object(std::vector<std::string>{
        json::field("registers", intMapJson(sdk_robot_.queryPort().registers())),
        json::field("session_id", json::quote(session_id_)),
        json::field("plan_hash", json::quote(plan_hash_))
    });
    return replyJson(request_id, true, "get_register_snapshot accepted", data);
  }
  if (command == "get_safety_config") {
    const auto data = json::object(std::vector<std::string>{
        json::field("collision_detection_enabled", json::boolLiteral(config_.collision_detection_enabled)),
        json::field("collision_sensitivity", std::to_string(config_.collision_sensitivity)),
        json::field("collision_behavior", json::quote(config_.collision_behavior)),
        json::field("collision_fallback_mm", json::formatDouble(config_.collision_fallback_mm)),
        json::field("soft_limit_enabled", json::boolLiteral(config_.soft_limit_enabled)),
        json::field("joint_soft_limit_margin_deg", json::formatDouble(config_.joint_soft_limit_margin_deg)),
        json::field("singularity_avoidance_enabled", json::boolLiteral(config_.singularity_avoidance_enabled))
    });
    return replyJson(request_id, true, "get_safety_config accepted", data);
  }
  if (command == "get_motion_contract") {
    const auto runtime_cfg = sdk_robot_.queryPort().runtimeConfig();
    const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
    const auto data = json::object(std::vector<std::string>{
        json::field("rt_mode", json::quote(config_.rt_mode)),
        json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
        json::field("network_tolerance_percent", std::to_string(runtime_cfg.rt_network_tolerance_percent)),
        json::field("preferred_link", json::quote(runtime_cfg.preferred_link)),
        json::field("collision_behavior", json::quote(config_.collision_behavior)),
        json::field("collision_detection_enabled", json::boolLiteral(config_.collision_detection_enabled)),
        json::field("soft_limit_enabled", json::boolLiteral(config_.soft_limit_enabled)),
        json::field("single_control_source_required", json::boolLiteral(runtime_cfg.requires_single_control_source)),
        json::field("clinical_allowed_modes", json::stringArray(identity.clinical_allowed_modes)),
        json::field("contact_force_target_n", json::formatDouble(runtime_cfg.contact_force_target_n)),
        json::field("scan_force_target_n", json::formatDouble(runtime_cfg.scan_force_target_n)),
        json::field("retract_timeout_ms", json::formatDouble(runtime_cfg.retract_timeout_ms)),
        json::field("cartesian_impedance", vectorJson(config_.cartesian_impedance)),
        json::field("desired_wrench_n", vectorJson(config_.desired_wrench_n)),
        json::field("sdk_boundary_units", json::object(std::vector<std::string>{
            json::field("ui_length_unit", json::quote(runtime_cfg.ui_length_unit)),
            json::field("sdk_length_unit", json::quote(runtime_cfg.sdk_length_unit)),
            json::field("boundary_normalized", json::boolLiteral(runtime_cfg.boundary_normalized)),
            json::field("fc_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix_m))),
            json::field("tcp_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix_m))),
            json::field("load_com_m", vectorJson(array3ToVector(runtime_cfg.load_com_m)))
        })),
        json::field("nrt_contract", json::object(std::vector<std::string>{
            json::field("active_profile", json::quote(nrt_motion_service_.snapshot().active_profile)),
            json::field("last_command", json::quote(nrt_motion_service_.snapshot().last_command)),
            json::field("command_count", std::to_string(nrt_motion_service_.snapshot().command_count)),
            json::field("degraded_without_sdk", json::boolLiteral(nrt_motion_service_.snapshot().degraded_without_sdk))
        })),
        json::field("rt_contract", json::object(std::vector<std::string>{
            json::field("phase", json::quote(rt_motion_service_.snapshot().phase)),
            json::field("last_event", json::quote(rt_motion_service_.snapshot().last_event)),
            json::field("loop_active", json::boolLiteral(rt_motion_service_.snapshot().loop_active)),
            json::field("move_active", json::boolLiteral(rt_motion_service_.snapshot().move_active)),
            json::field("pause_hold", json::boolLiteral(rt_motion_service_.snapshot().pause_hold)),
            json::field("degraded_without_sdk", json::boolLiteral(rt_motion_service_.snapshot().degraded_without_sdk)),
            json::field("desired_contact_force_n", json::formatDouble(rt_motion_service_.snapshot().desired_contact_force_n)),
            json::field("current_period_ms", json::formatDouble(rt_motion_service_.snapshot().current_period_ms))
        })),
        json::field("filters", json::object(std::vector<std::string>{
            json::field("joint_hz", json::formatDouble(runtime_cfg.joint_filter_hz)),
            json::field("cart_hz", json::formatDouble(runtime_cfg.cart_filter_hz)),
            json::field("torque_hz", json::formatDouble(runtime_cfg.torque_filter_hz))
        }))
    });
    return replyJson(request_id, true, "get_motion_contract accepted", data);
  }
  if (command == "get_runtime_alignment") {
    const auto runtime_cfg = sdk_robot_.queryPort().runtimeConfig();
    const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
    const auto data = json::object(std::vector<std::string>{
        json::field("sdk_family", json::quote("ROKAE xCore SDK (C++)")),
        json::field("robot_model", json::quote(identity.robot_model)),
        json::field("sdk_robot_class", json::quote(identity.sdk_robot_class)),
        json::field("axis_count", std::to_string(identity.axis_count)),
        json::field("controller_series", json::quote(identity.controller_series)),
        json::field("controller_version", json::quote(identity.controller_version)),
        json::field("remote_ip", json::quote(runtime_cfg.remote_ip)),
        json::field("local_ip", json::quote(runtime_cfg.local_ip)),
        json::field("preferred_link", json::quote(runtime_cfg.preferred_link)),
        json::field("rt_mode", json::quote(config_.rt_mode)),
        json::field("single_control_source", json::boolLiteral(runtime_cfg.requires_single_control_source)),
        json::field("sdk_available", json::boolLiteral(sdk_robot_.queryPort().sdkAvailable())),
        json::field("sdk_binding_mode", json::quote(sdk_robot_.queryPort().sdkBindingMode())),
        json::field("control_source_exclusive", json::boolLiteral(sdk_robot_.queryPort().controlSourceExclusive())),
        json::field("network_healthy", json::boolLiteral(sdk_robot_.queryPort().networkHealthy())),
        json::field("motion_channel_ready", json::boolLiteral(sdk_robot_.queryPort().motionChannelReady())),
        json::field("state_channel_ready", json::boolLiteral(sdk_robot_.queryPort().stateChannelReady())),
        json::field("aux_channel_ready", json::boolLiteral(sdk_robot_.queryPort().auxChannelReady())),
        json::field("nominal_rt_loop_hz", std::to_string(sdk_robot_.queryPort().nominalRtLoopHz())),
        json::field("source", json::quote(sdk_robot_.queryPort().runtimeSource()))
    });
    return replyJson(request_id, true, "get_runtime_alignment accepted", data);
  }
  if (command == "get_xmate_model_summary") {
    const auto runtime_cfg = sdk_robot_.queryPort().runtimeConfig();
    const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
    const auto data = json::object(std::vector<std::string>{
        json::field("robot_model", json::quote(identity.robot_model)),
        json::field("label", json::quote(identity.label)),
        json::field("sdk_robot_class", json::quote(identity.sdk_robot_class)),
        json::field("axis_count", std::to_string(identity.axis_count)),
        json::field("supported_rt_modes", json::stringArray(identity.supported_rt_modes)),
        json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
        json::field("supports_planner", json::boolLiteral(identity.supports_planner)),
        json::field("supports_xmate_model", json::boolLiteral(identity.supports_xmate_model)),
        json::field("approximate", json::boolLiteral(!(sdk_robot_.queryPort().xmateModelAvailable() && identity.supports_xmate_model))),
        json::field("source", json::quote(sdk_robot_.queryPort().runtimeSource())),
        json::field("dh_parameters", dhArrayJson(identity.official_dh_parameters))
    });
    return replyJson(request_id, true, "get_xmate_model_summary accepted", data);
  }
  if (command == "get_sdk_runtime_config") {
    const auto runtime_cfg = sdk_robot_.queryPort().runtimeConfig();

    std::vector<std::string> common_fields;
    common_fields.emplace_back(json::field("rt_stale_state_timeout_ms", json::formatDouble(runtime_cfg.rt_stale_state_timeout_ms)));
    common_fields.emplace_back(json::field("rt_phase_transition_debounce_cycles", std::to_string(runtime_cfg.rt_phase_transition_debounce_cycles)));
    common_fields.emplace_back(json::field("rt_max_cart_step_mm", json::formatDouble(runtime_cfg.rt_max_cart_step_mm)));
    common_fields.emplace_back(json::field("rt_max_cart_vel_mm_s", json::formatDouble(runtime_cfg.rt_max_cart_vel_mm_s)));
    common_fields.emplace_back(json::field("rt_max_cart_acc_mm_s2", json::formatDouble(runtime_cfg.rt_max_cart_acc_mm_s2)));
    common_fields.emplace_back(json::field("rt_max_pose_trim_deg", json::formatDouble(runtime_cfg.rt_max_pose_trim_deg)));
    common_fields.emplace_back(json::field("rt_max_force_error_n", json::formatDouble(runtime_cfg.rt_max_force_error_n)));
    common_fields.emplace_back(json::field("rt_integrator_limit_n", json::formatDouble(runtime_cfg.rt_integrator_limit_n)));
    const auto common_obj = json::object(common_fields);

    std::vector<std::string> contact_control_fields;
    contact_control_fields.emplace_back(json::field("mode", json::quote(runtime_cfg.contact_control.mode)));
    contact_control_fields.emplace_back(json::field("virtual_mass", json::formatDouble(runtime_cfg.contact_control.virtual_mass)));
    contact_control_fields.emplace_back(json::field("virtual_damping", json::formatDouble(runtime_cfg.contact_control.virtual_damping)));
    contact_control_fields.emplace_back(json::field("virtual_stiffness", json::formatDouble(runtime_cfg.contact_control.virtual_stiffness)));
    contact_control_fields.emplace_back(json::field("force_deadband_n", json::formatDouble(runtime_cfg.contact_control.force_deadband_n)));
    contact_control_fields.emplace_back(json::field("max_normal_step_mm", json::formatDouble(runtime_cfg.contact_control.max_normal_step_mm)));
    contact_control_fields.emplace_back(json::field("max_normal_velocity_mm_s", json::formatDouble(runtime_cfg.contact_control.max_normal_velocity_mm_s)));
    contact_control_fields.emplace_back(json::field("max_normal_acc_mm_s2", json::formatDouble(runtime_cfg.contact_control.max_normal_acc_mm_s2)));
    contact_control_fields.emplace_back(json::field("max_normal_travel_mm", json::formatDouble(runtime_cfg.contact_control.max_normal_travel_mm)));
    contact_control_fields.emplace_back(json::field("anti_windup_limit_n", json::formatDouble(runtime_cfg.contact_control.anti_windup_limit_n)));
    contact_control_fields.emplace_back(json::field("integrator_leak", json::formatDouble(runtime_cfg.contact_control.integrator_leak)));
    const auto contact_control_obj = json::object(contact_control_fields);

    std::vector<std::string> force_estimator_fields;
    force_estimator_fields.emplace_back(json::field("preferred_source", json::quote(runtime_cfg.force_estimator.preferred_source)));
    force_estimator_fields.emplace_back(json::field("pressure_weight", json::formatDouble(runtime_cfg.force_estimator.pressure_weight)));
    force_estimator_fields.emplace_back(json::field("wrench_weight", json::formatDouble(runtime_cfg.force_estimator.wrench_weight)));
    force_estimator_fields.emplace_back(json::field("stale_timeout_ms", std::to_string(runtime_cfg.force_estimator.stale_timeout_ms)));
    force_estimator_fields.emplace_back(json::field("timeout_ms", std::to_string(runtime_cfg.force_estimator.timeout_ms)));
    force_estimator_fields.emplace_back(json::field("auto_bias_zero", json::boolLiteral(runtime_cfg.force_estimator.auto_bias_zero)));
    force_estimator_fields.emplace_back(json::field("min_confidence", json::formatDouble(runtime_cfg.force_estimator.min_confidence)));
    const auto force_estimator_obj = json::object(force_estimator_fields);

    std::vector<std::string> orientation_trim_fields;
    orientation_trim_fields.emplace_back(json::field("gain", json::formatDouble(runtime_cfg.orientation_trim.gain)));
    orientation_trim_fields.emplace_back(json::field("max_trim_deg", json::formatDouble(runtime_cfg.orientation_trim.max_trim_deg)));
    orientation_trim_fields.emplace_back(json::field("lowpass_hz", json::formatDouble(runtime_cfg.orientation_trim.lowpass_hz)));
    const auto orientation_trim_obj = json::object(orientation_trim_fields);

    std::vector<std::string> seek_contact_fields;
    seek_contact_fields.emplace_back(json::field("contact_force_target_n", json::formatDouble(runtime_cfg.contact_force_target_n)));
    seek_contact_fields.emplace_back(json::field("contact_force_tolerance_n", json::formatDouble(runtime_cfg.contact_force_tolerance_n)));
    seek_contact_fields.emplace_back(json::field("contact_establish_cycles", std::to_string(runtime_cfg.contact_establish_cycles)));
    seek_contact_fields.emplace_back(json::field("normal_admittance_gain", json::formatDouble(runtime_cfg.normal_admittance_gain)));
    seek_contact_fields.emplace_back(json::field("normal_damping_gain", json::formatDouble(runtime_cfg.normal_damping_gain)));
    seek_contact_fields.emplace_back(json::field("seek_contact_max_step_mm", json::formatDouble(runtime_cfg.seek_contact_max_step_mm)));
    seek_contact_fields.emplace_back(json::field("seek_contact_max_travel_mm", json::formatDouble(runtime_cfg.seek_contact_max_travel_mm)));
    seek_contact_fields.emplace_back(json::field("normal_velocity_quiet_threshold_mm_s", json::formatDouble(runtime_cfg.normal_velocity_quiet_threshold_mm_s)));
    seek_contact_fields.emplace_back(json::field("contact_control", contact_control_obj));
    seek_contact_fields.emplace_back(json::field("force_estimator", force_estimator_obj));
    const auto seek_contact_obj = json::object(seek_contact_fields);

    std::vector<std::string> scan_follow_fields;
    scan_follow_fields.emplace_back(json::field("scan_force_target_n", json::formatDouble(runtime_cfg.scan_force_target_n)));
    scan_follow_fields.emplace_back(json::field("scan_force_tolerance_n", json::formatDouble(runtime_cfg.scan_force_tolerance_n)));
    scan_follow_fields.emplace_back(json::field("scan_normal_pi_kp", json::formatDouble(runtime_cfg.scan_normal_pi_kp)));
    scan_follow_fields.emplace_back(json::field("scan_normal_pi_ki", json::formatDouble(runtime_cfg.scan_normal_pi_ki)));
    scan_follow_fields.emplace_back(json::field("scan_tangent_speed_min_mm_s", json::formatDouble(runtime_cfg.scan_tangent_speed_min_mm_s)));
    scan_follow_fields.emplace_back(json::field("scan_tangent_speed_max_mm_s", json::formatDouble(runtime_cfg.scan_tangent_speed_max_mm_s)));
    scan_follow_fields.emplace_back(json::field("scan_pose_trim_gain", json::formatDouble(runtime_cfg.scan_pose_trim_gain)));
    scan_follow_fields.emplace_back(json::field("scan_follow_enable_lateral_modulation", json::boolLiteral(runtime_cfg.scan_follow_enable_lateral_modulation)));
    scan_follow_fields.emplace_back(json::field("scan_follow_max_travel_mm", json::formatDouble(runtime_cfg.scan_follow_max_travel_mm)));
    scan_follow_fields.emplace_back(json::field("scan_follow_lateral_amplitude_mm", json::formatDouble(runtime_cfg.scan_follow_lateral_amplitude_mm)));
    scan_follow_fields.emplace_back(json::field("scan_follow_frequency_hz", json::formatDouble(runtime_cfg.scan_follow_frequency_hz)));
    scan_follow_fields.emplace_back(json::field("orientation_trim", orientation_trim_obj));
    const auto scan_follow_obj = json::object(scan_follow_fields);

    std::vector<std::string> pause_hold_fields;
    pause_hold_fields.emplace_back(json::field("pause_hold_position_guard_mm", json::formatDouble(runtime_cfg.pause_hold_position_guard_mm)));
    pause_hold_fields.emplace_back(json::field("pause_hold_force_guard_n", json::formatDouble(runtime_cfg.pause_hold_force_guard_n)));
    pause_hold_fields.emplace_back(json::field("pause_hold_drift_kp", json::formatDouble(runtime_cfg.pause_hold_drift_kp)));
    pause_hold_fields.emplace_back(json::field("pause_hold_drift_ki", json::formatDouble(runtime_cfg.pause_hold_drift_ki)));
    pause_hold_fields.emplace_back(json::field("pause_hold_integrator_leak", json::formatDouble(runtime_cfg.pause_hold_integrator_leak)));
    const auto pause_hold_obj = json::object(pause_hold_fields);

    std::vector<std::string> retract_fields;
    retract_fields.emplace_back(json::field("retract_release_force_n", json::formatDouble(runtime_cfg.retract_release_force_n)));
    retract_fields.emplace_back(json::field("retract_release_cycles", std::to_string(runtime_cfg.retract_release_cycles)));
    retract_fields.emplace_back(json::field("retract_safe_gap_mm", json::formatDouble(runtime_cfg.retract_safe_gap_mm)));
    retract_fields.emplace_back(json::field("retract_max_travel_mm", json::formatDouble(runtime_cfg.retract_max_travel_mm)));
    retract_fields.emplace_back(json::field("retract_jerk_limit_mm_s3", json::formatDouble(runtime_cfg.retract_jerk_limit_mm_s3)));
    retract_fields.emplace_back(json::field("retract_timeout_ms", json::formatDouble(runtime_cfg.retract_timeout_ms)));
    retract_fields.emplace_back(json::field("retract_travel_mm", json::formatDouble(runtime_cfg.retract_travel_mm)));
    const auto retract_obj = json::object(retract_fields);

    std::vector<std::string> rt_phase_fields;
    rt_phase_fields.emplace_back(json::field("common", common_obj));
    rt_phase_fields.emplace_back(json::field("seek_contact", seek_contact_obj));
    rt_phase_fields.emplace_back(json::field("scan_follow", scan_follow_obj));
    rt_phase_fields.emplace_back(json::field("pause_hold", pause_hold_obj));
    rt_phase_fields.emplace_back(json::field("controlled_retract", retract_obj));
    const auto rt_phase_contract = json::object(rt_phase_fields);

    std::vector<std::string> data_fields;
    data_fields.emplace_back(json::field("robot_model", json::quote(runtime_cfg.robot_model)));
    data_fields.emplace_back(json::field("sdk_robot_class", json::quote(runtime_cfg.sdk_robot_class)));
    data_fields.emplace_back(json::field("remote_ip", json::quote(runtime_cfg.remote_ip)));
    data_fields.emplace_back(json::field("local_ip", json::quote(runtime_cfg.local_ip)));
    data_fields.emplace_back(json::field("axis_count", std::to_string(runtime_cfg.axis_count)));
    data_fields.emplace_back(json::field("rt_network_tolerance_percent", std::to_string(runtime_cfg.rt_network_tolerance_percent)));
    data_fields.emplace_back(json::field("joint_filter_hz", json::formatDouble(runtime_cfg.joint_filter_hz)));
    data_fields.emplace_back(json::field("cart_filter_hz", json::formatDouble(runtime_cfg.cart_filter_hz)));
    data_fields.emplace_back(json::field("torque_filter_hz", json::formatDouble(runtime_cfg.torque_filter_hz)));
    data_fields.emplace_back(json::field("fc_frame_type", json::quote(config_.fc_frame_type)));
    data_fields.emplace_back(json::field("cartesian_impedance", vectorJson(array6ToVector(runtime_cfg.cartesian_impedance))));
    data_fields.emplace_back(json::field("desired_wrench_n", vectorJson(array6ToVector(runtime_cfg.desired_wrench_n))));
    data_fields.emplace_back(json::field("fc_frame_matrix", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix))));
    data_fields.emplace_back(json::field("tcp_frame_matrix", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix))));
    data_fields.emplace_back(json::field("load_com_mm", vectorJson(array3ToVector(runtime_cfg.load_com_mm))));
    data_fields.emplace_back(json::field("fc_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix_m))));
    data_fields.emplace_back(json::field("tcp_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix_m))));
    data_fields.emplace_back(json::field("load_com_m", vectorJson(array3ToVector(runtime_cfg.load_com_m))));
    data_fields.emplace_back(json::field("rt_stale_state_timeout_ms", json::formatDouble(runtime_cfg.rt_stale_state_timeout_ms)));
    data_fields.emplace_back(json::field("rt_phase_transition_debounce_cycles", std::to_string(runtime_cfg.rt_phase_transition_debounce_cycles)));
    data_fields.emplace_back(json::field("rt_max_cart_step_mm", json::formatDouble(runtime_cfg.rt_max_cart_step_mm)));
    data_fields.emplace_back(json::field("contact_force_target_n", json::formatDouble(runtime_cfg.contact_force_target_n)));
    data_fields.emplace_back(json::field("scan_force_target_n", json::formatDouble(runtime_cfg.scan_force_target_n)));
    data_fields.emplace_back(json::field("retract_timeout_ms", json::formatDouble(runtime_cfg.retract_timeout_ms)));
    data_fields.emplace_back(json::field("ui_length_unit", json::quote(runtime_cfg.ui_length_unit)));
    data_fields.emplace_back(json::field("sdk_length_unit", json::quote(runtime_cfg.sdk_length_unit)));
    data_fields.emplace_back(json::field("boundary_normalized", json::boolLiteral(runtime_cfg.boundary_normalized)));
    data_fields.emplace_back(json::field("load_inertia", vectorJson(array6ToVector(runtime_cfg.load_inertia))));
    data_fields.emplace_back(json::field("contact_control", contact_control_obj));
    data_fields.emplace_back(json::field("force_estimator", force_estimator_obj));
    data_fields.emplace_back(json::field("orientation_trim", orientation_trim_obj));
    data_fields.emplace_back(json::field("rt_phase_contract", rt_phase_contract));
    const auto data = json::object(data_fields);
    return replyJson(request_id, true, "get_sdk_runtime_config accepted", data);
  }
  if (command == "get_identity_contract") {
    const auto runtime_cfg = sdk_robot_.queryPort().runtimeConfig();
    const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
    const auto data = json::object(std::vector<std::string>{
        json::field("robot_model", json::quote(identity.robot_model)),
        json::field("label", json::quote(identity.label)),
        json::field("sdk_robot_class", json::quote(identity.sdk_robot_class)),
        json::field("axis_count", std::to_string(identity.axis_count)),
        json::field("controller_series", json::quote(identity.controller_series)),
        json::field("controller_version", json::quote(identity.controller_version)),
        json::field("preferred_link", json::quote(identity.preferred_link)),
        json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
        json::field("supported_rt_modes", json::stringArray(identity.supported_rt_modes)),
        json::field("clinical_allowed_modes", json::stringArray(identity.clinical_allowed_modes)),
        json::field("contact_force_target_n", json::formatDouble(runtime_cfg.contact_force_target_n)),
        json::field("scan_force_target_n", json::formatDouble(runtime_cfg.scan_force_target_n)),
        json::field("retract_timeout_ms", json::formatDouble(runtime_cfg.retract_timeout_ms)),
        json::field("cartesian_impedance_limits", vectorJson(identity.cartesian_impedance_limits)),
        json::field("desired_wrench_limits", vectorJson(identity.desired_wrench_limits)),
        json::field("official_dh_parameters", dhArrayJson(identity.official_dh_parameters))
    });
    return replyJson(request_id, true, "get_identity_contract accepted", data);
  }
  if (command == "get_robot_family_contract") {
    return replyJson(request_id, true, "get_robot_family_contract accepted", robotFamilyContractJsonLocked());
  }
  if (command == "get_vendor_boundary_contract") {
    return replyJson(request_id, true, "get_vendor_boundary_contract accepted", vendorBoundaryContractJsonLocked());
  }
  if (command == "get_clinical_mainline_contract") {
    const auto runtime_cfg = sdk_robot_.queryPort().runtimeConfig();
    const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
    const auto data = json::object(std::vector<std::string>{
        json::field("robot_model", json::quote(identity.robot_model)),
        json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
        json::field("required_sequence", json::stringArray({"connect_robot", "power_on", "set_auto_mode", "lock_session", "load_scan_plan", "approach_prescan", "seek_contact", "start_scan", "safe_retreat"})),
        json::field("single_control_source_required", json::boolLiteral(identity.requires_single_control_source)),
        json::field("preferred_link", json::quote(identity.preferred_link)),
        json::field("rt_loop_hz", std::to_string(1000)),
        json::field("cartesian_impedance_limits", vectorJson(identity.cartesian_impedance_limits)),
        json::field("desired_wrench_limits", vectorJson(identity.desired_wrench_limits))
    });
    return replyJson(request_id, true, "get_clinical_mainline_contract accepted", data);
  }
  if (command == "get_session_drift_contract") {
    return replyJson(request_id, true, "get_session_drift_contract accepted", sessionDriftContractJsonLocked());
  }
  if (command == "get_hardware_lifecycle_contract") {
    return replyJson(request_id, true, "get_hardware_lifecycle_contract accepted", hardwareLifecycleContractJsonLocked());
  }
  if (command == "get_rt_kernel_contract") {
    return replyJson(request_id, true, "get_rt_kernel_contract accepted", rtKernelContractJsonLocked());
  }
  if (command == "get_authoritative_runtime_envelope") {
    return replyJson(request_id, true, "get_authoritative_runtime_envelope accepted", authoritativeRuntimeEnvelopeJsonLocked());
  }
  if (command == "get_session_freeze") {
    const auto data = json::object(std::vector<std::string>{
        json::field("session_locked", json::boolLiteral(!session_id_.empty())),
        json::field("session_id", json::quote(session_id_)),
        json::field("session_dir", json::quote(session_dir_)),
        json::field("locked_at_ns", std::to_string(session_locked_ts_ns_)),
        json::field("plan_hash", json::quote(plan_hash_)),
        json::field("active_segment", std::to_string(active_segment_)),
        json::field("tool_name", json::quote(config_.tool_name)),
        json::field("tcp_name", json::quote(config_.tcp_name)),
        json::field("load_kg", json::formatDouble(config_.load_kg)),
        json::field("rt_mode", json::quote(config_.rt_mode)),
        json::field("cartesian_impedance", vectorJson(config_.cartesian_impedance)),
        json::field("desired_wrench_n", vectorJson(config_.desired_wrench_n))
    });
    return replyJson(request_id, true, "get_session_freeze accepted", data);
  }
  if (command == "get_control_governance_contract") {
    return replyJson(request_id, true, "get_control_governance_contract accepted", controlGovernanceContractJsonLocked());
  }
  if (command == "get_controller_evidence") {
    return replyJson(request_id, true, "get_controller_evidence accepted", controllerEvidenceJsonLocked());
  }
  if (command == "get_dual_state_machine_contract") {
    return replyJson(request_id, true, "get_dual_state_machine_contract accepted", dualStateMachineContractJsonLocked());
  }
  if (command == "get_mainline_executor_contract") {
    return replyJson(request_id, true, "get_mainline_executor_contract accepted", mainlineExecutorContractJsonLocked());
  }
  if (command == "get_recovery_contract") {
    return replyJson(request_id, true, "get_recovery_contract accepted", safetyRecoveryContractJsonLocked());
  }
  if (command == "get_safety_recovery_contract") {
    return replyJson(request_id, true, "get_safety_recovery_contract accepted", safetyRecoveryContractJsonLocked());
  }
  if (command == "get_capability_contract") {
    return replyJson(request_id, true, "get_capability_contract accepted", capabilityContractJsonLocked());
  }
  if (command == "get_model_authority_contract") {
    return replyJson(request_id, true, "get_model_authority_contract accepted", modelAuthorityContractJsonLocked());
  }
  if (command == "get_release_contract") {
    return replyJson(request_id, true, "get_release_contract accepted", releaseContractJsonLocked());
  }
  if (command == "get_deployment_contract") {
    return replyJson(request_id, true, "get_deployment_contract accepted", deploymentContractJsonLocked());
  }
  if (command == "get_fault_injection_contract") {
    return replyJson(request_id, true, "get_fault_injection_contract accepted", faultInjectionContractJsonLocked());
  }
  return replyJson(request_id, false, "unsupported command: " + command);
}

}  // namespace robot_core
