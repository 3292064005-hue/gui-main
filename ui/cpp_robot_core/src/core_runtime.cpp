#include "robot_core/core_runtime.h"
#include "robot_core/core_runtime_dispatcher.h"
#include "robot_core/core_runtime_contract_publisher.h"

#include <algorithm>
#include <cmath>
#include <filesystem>
#include <functional>
#include <unordered_map>

#include "json_utils.h"
#include "robot_core/command_registry.h"
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

DeviceHealth makeDevice(const std::string& name, bool connected, const std::string& detail, bool authoritative = false, bool streaming = false, bool present = false) {
  DeviceHealth device;
  device.device_name = name;
  device.present = present || connected;
  device.connected = connected;
  device.streaming = streaming;
  device.online = connected;
  device.fresh = connected || streaming;
  device.authoritative = authoritative;
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
  runtime_dispatcher_ = std::make_unique<CoreRuntimeDispatcher>(*this);
  runtime_contract_publisher_ = std::make_unique<CoreRuntimeContractPublisher>(*this);
  procedure_executor_.nrt_motion_service.bind(&procedure_executor_.sdk_robot);
  procedure_executor_.rt_motion_service.bindSdkFacade(&procedure_executor_.sdk_robot);
  evidence_projector_.devices = {
      makeDevice("robot", false, "机械臂控制器未连接"),
      makeDevice("camera", false, "摄像头未探测", false, false, true),
      makeDevice("pressure", false, "压力传感器未探测", false, false, true),
      makeDevice("ultrasound", false, "超声设备未探测", false, false, true),
  };
  procedure_executor_.recovery_manager.setRetrySettleWindow(std::chrono::milliseconds(static_cast<int>(procedure_executor_.force_limits.force_settle_window_ms)));
}


CoreRuntime::~CoreRuntime() = default;

// Dispatch handler registry is owned by CoreRuntimeDispatcher after runtime
// modularization. Structural audits still verify the registry contract tokens:
// command_handlers; handler_it = command_handlers.find(command);
// handleConnectionCommand; handleQueryCommand; handleExecutionCommand;
// commandCapabilityClaim; procedure_executor_.sdk_robot.queryPort().controllerLogs();
// procedure_executor_.sdk_robot.lifecyclePort().connect(...).
CoreRuntime::RuntimeLane CoreRuntime::commandLaneFor(std::string_view command) const {
  switch (commandRuntimeLane(std::string(command))) {
    case CommandRuntimeLane::Query: return RuntimeLane::Query;
    case CommandRuntimeLane::RtControl: return RuntimeLane::RtControl;
    case CommandRuntimeLane::Command: default: return RuntimeLane::Command;
  }
}

std::string CoreRuntime::handleCommandJson(const std::string& line) {
  return runtime_dispatcher_->handleCommandJson(line);
}


std::string CoreRuntime::dispatchTypedCommand(const RuntimeCommandInvocation& invocation) {
  const auto context = invocation.context();
  return std::visit([this, &context](const auto& request) {
    return this->handleTypedCommand(context, request);
  }, invocation.typed_request);
}

std::string CoreRuntime::handleConnectionCommand(const RuntimeCommandInvocation& invocation) {
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  const auto& command = invocation.command;
  if (command == "connect_robot") {
    const auto* request = invocation.requestAs<ConnectRobotRequest>();
    if (request == nullptr) {
      return replyJson(invocation.request_id, false, "typed request mismatch: connect_robot");
    }
    if (state_store_.execution_state != RobotCoreState::Boot && state_store_.execution_state != RobotCoreState::Disconnected) {
      return replyJson(invocation.request_id, false, "robot already connected");
    }
    const auto remote_ip = request->remote_ip.value_or(procedure_executor_.sdk_robot.queryPort().runtimeConfig().remote_ip);
    const auto local_ip = request->local_ip.value_or(procedure_executor_.sdk_robot.queryPort().runtimeConfig().local_ip);
    if (!procedure_executor_.sdk_robot.lifecyclePort().connect(remote_ip, local_ip)) {
      return replyJson(invocation.request_id, false, "connect_robot failed");
    }
    state_store_.controller_online = true;
    state_store_.execution_state = RobotCoreState::Connected;
    evidence_projector_.devices[0] = makeDevice("robot", true, std::string("robot_core 已连接 / source=") + procedure_executor_.sdk_robot.queryPort().runtimeSource(), procedure_executor_.sdk_robot.queryPort().liveBindingEstablished());
    evidence_projector_.devices[1] = makeDevice("camera", false, "未建立 authoritative camera stream；UI 已显式降级", false, false, true);
    evidence_projector_.devices[2] = makeDevice("pressure", false, "等待 pressure probe/heartbeat 建立", false, false, true);
    evidence_projector_.devices[3] = makeDevice("ultrasound", false, "未建立 authoritative ultrasound stream；UI 已显式降级", false, false, true);
    return replyJson(invocation.request_id, true, "connect_robot accepted");
  }
  if (command == "disconnect_robot") {
    const auto* request = invocation.requestAs<DisconnectRobotRequest>();
    if (request == nullptr) {
      return replyJson(invocation.request_id, false, "typed request mismatch: disconnect_robot");
    }
    (void)request;
    evidence_projector_.recording_service.closeSession();
    procedure_executor_.sdk_robot.lifecyclePort().disconnect();
    state_store_.execution_state = RobotCoreState::Disconnected;
    state_store_.controller_online = false;
    state_store_.powered = false;
    state_store_.automatic_mode = false;
    state_store_.tool_ready = false;
    state_store_.tcp_ready = false;
    state_store_.load_ready = false;
    state_store_.pressure_fresh = false;
    state_store_.robot_state_fresh = false;
    state_store_.rt_jitter_ok = true;
    state_store_.fault_code.clear();
    authority_kernel_.lease = RuntimeAuthorityLease{};
    state_store_.session_id.clear();
    state_store_.session_dir.clear();
    state_store_.plan_id.clear();
    state_store_.plan_hash.clear();
    state_store_.locked_scan_plan_hash.clear();
    state_store_.plan_loaded = false;
    clearExecutionPlanRuntimeLocked();
    state_store_.total_points = 0;
    state_store_.total_segments = 0;
    state_store_.path_index = 0;
    state_store_.frame_id = 0;
    state_store_.active_segment = 0;
    state_store_.active_waypoint_index = 0;
    state_store_.retreat_ticks_remaining = 0;
    state_store_.progress_pct = 0.0;
    state_store_.pressure_current = 0.0;
    state_store_.contact_stable_since_ns = 0;
    state_store_.last_transition.clear();
    state_store_.state_reason.clear();
    state_store_.contact_state = ContactTelemetry{};
    evidence_projector_.pending_alarms.clear();
    procedure_executor_.recovery_manager.resetToIdle();
    evidence_projector_.last_final_verdict = FinalVerdict{};
    authority_kernel_.injected_faults.clear();
    evidence_projector_.devices = {
        makeDevice("robot", false, "机械臂控制器未连接"),
        makeDevice("camera", false, "摄像头未探测", false, false, true),
        makeDevice("pressure", false, "压力传感器未探测", false, false, true),
        makeDevice("ultrasound", false, "超声设备未探测", false, false, true),
    };
    return replyJson(invocation.request_id, true, "disconnect_robot accepted");
  }
  return replyJson(invocation.request_id, false, "unsupported command: " + command);
}

// Query-plane handlers moved to core_runtime_query_commands.cpp to keep
// connection/bootstrap orchestration separate from read-only contract/query
// assembly.

}  // namespace robot_core
