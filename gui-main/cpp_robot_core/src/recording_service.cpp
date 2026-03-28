#include "robot_core/recording_service.h"

#include <filesystem>

#include "json_utils.h"

namespace robot_core {

namespace {

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
    case RobotCoreState::Scanning: return "SCANNING";
    case RobotCoreState::PausedHold: return "PAUSED_HOLD";
    case RobotCoreState::Retreating: return "RETREATING";
    case RobotCoreState::ScanComplete: return "SCAN_COMPLETE";
    case RobotCoreState::Fault: return "FAULT";
    case RobotCoreState::Estop: return "ESTOP";
  }
  return "BOOT";
}

std::string robotStateJson(const RobotStateSnapshot& state) {
  using namespace json;
  return object({
      field("timestamp_ns", std::to_string(state.timestamp_ns)),
      field("power_state", quote(state.power_state)),
      field("operate_mode", quote(state.operate_mode)),
      field("operation_state", quote(state.operation_state)),
      field("joint_pos", array(state.joint_pos)),
      field("joint_vel", array(state.joint_vel)),
      field("joint_torque", array(state.joint_torque)),
      field("tcp_pose", array(state.tcp_pose)),
      field("cart_force", array(state.cart_force)),
      field("last_event", quote(state.last_event)),
      field("last_controller_log", quote(state.last_controller_log)),
  });
}

std::string contactJson(const ContactTelemetry& contact) {
  using namespace json;
  return object({
      field("mode", quote(contact.mode)),
      field("confidence", formatDouble(contact.confidence)),
      field("pressure_current", formatDouble(contact.pressure_current)),
      field("recommended_action", quote(contact.recommended_action)),
  });
}

std::string progressJson(const CoreStateSnapshot& core_state, const ScanProgress& progress) {
  using namespace json;
  return object({
      field("execution_state", quote(stateName(core_state.execution_state))),
      field("active_segment", std::to_string(progress.active_segment)),
      field("path_index", std::to_string(progress.path_index)),
      field("progress_pct", formatDouble(progress.overall_progress)),
      field("frame_id", std::to_string(progress.frame_id)),
      field("session_id", quote(core_state.session_id)),
  });
}

std::string alarmJson(const AlarmEvent& alarm) {
  using namespace json;
  return object({
      field("severity", quote(alarm.severity)),
      field("source", quote(alarm.source)),
      field("message", quote(alarm.message)),
      field("session_id", quote(alarm.session_id)),
      field("segment_id", std::to_string(alarm.segment_id)),
      field("event_ts_ns", std::to_string(alarm.event_ts_ns)),
  });
}

}  // namespace

void RecordingService::openSession(const std::filesystem::path& session_dir, const std::string& session_id) {
  session_dir_ = session_dir;
  session_id_ = session_id;
  seq_ = 0;
  active_ = true;
  recorder_status_.session_id = session_id;
  recorder_status_.recording = true;
  recorder_status_.dropped_samples = 0;
  recorder_status_.last_flush_ns = 0;
  json::ensureDir(session_dir_ / "raw" / "core");
}

void RecordingService::closeSession() {
  active_ = false;
  recorder_status_.recording = false;
}

bool RecordingService::active() const {
  return active_;
}

RecorderStatus RecordingService::status() const {
  return recorder_status_;
}

void RecordingService::recordRobotState(const RobotStateSnapshot& state) {
  if (!active_) {
    return;
  }
  append(session_dir_ / "raw" / "core" / "robot_state.jsonl", robotStateJson(state));
}

void RecordingService::recordContactState(const ContactTelemetry& contact) {
  if (!active_) {
    return;
  }
  append(session_dir_ / "raw" / "core" / "contact_state.jsonl", contactJson(contact));
}

void RecordingService::recordScanProgress(const CoreStateSnapshot& core_state, const ScanProgress& progress) {
  if (!active_) {
    return;
  }
  append(session_dir_ / "raw" / "core" / "scan_progress.jsonl", progressJson(core_state, progress));
}

void RecordingService::recordAlarm(const AlarmEvent& alarm) {
  if (!active_) {
    return;
  }
  append(session_dir_ / "raw" / "core" / "alarm_event.jsonl", alarmJson(alarm));
}

void RecordingService::append(const std::filesystem::path& path, const std::string& payload_json) {
  using namespace json;
  ++seq_;
  recorder_status_.last_flush_ns = nowNs();
  const auto envelope = object({
      field("monotonic_ns", std::to_string(nowNs())),
      field("source_ts_ns", std::to_string(recorder_status_.last_flush_ns)),
      field("seq", std::to_string(seq_)),
      field("session_id", quote(session_id_)),
      field("data", payload_json),
  });
  appendLine(path, envelope);
}

}  // namespace robot_core
