#include "robot_core/recording_service.h"

#include <chrono>
#include <filesystem>
#include <thread>

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
    case RobotCoreState::ContactStable: return "CONTACT_STABLE";
    case RobotCoreState::RecoveryRetract: return "RECOVERY_RETRACT";
    case RobotCoreState::SegmentAborted: return "SEGMENT_ABORTED";
    case RobotCoreState::PlanAborted: return "PLAN_ABORTED";
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
      field("workflow_step", quote(alarm.workflow_step)),
      field("request_id", quote(alarm.request_id)),
      field("auto_action", quote(alarm.auto_action)),
  });
}

}  // namespace

RecordingService::RecordingService() = default;

RecordingService::~RecordingService() {
  stopWorker(true);
}

void RecordingService::openSession(const std::filesystem::path& session_dir, const std::string& session_id) {
  stopWorker(true);
  session_dir_ = session_dir;
  session_id_ = session_id;
  seq_ = 0;
  active_.store(true);
  recorder_status_.session_id = session_id;
  recorder_status_.recording = true;
  recorder_status_.dropped_samples = 0;
  recorder_status_.last_flush_ns = 0;
  json::ensureDir(session_dir_ / "raw" / "core");
  stop_worker_.store(false);
  recorder_thread_ = std::thread(&RecordingService::recorderLoop, this);
}

void RecordingService::closeSession() {
  active_.store(false);
  recorder_status_.recording = false;
  stopWorker(true);
}

bool RecordingService::active() const {
  return active_.load();
}

RecorderStatus RecordingService::status() const {
  return recorder_status_;
}

void RecordingService::recordRobotState(const RobotStateSnapshot& state) {
  if (!active()) {
    return;
  }
  QueuedSample sample;
  sample.kind = SampleKind::RobotState;
  sample.robot_state = state;
  enqueueSample(sample);
}

void RecordingService::recordContactState(const ContactTelemetry& contact) {
  if (!active()) {
    return;
  }
  QueuedSample sample;
  sample.kind = SampleKind::ContactState;
  sample.contact_state = contact;
  enqueueSample(sample);
}

void RecordingService::recordScanProgress(const CoreStateSnapshot& core_state, const ScanProgress& progress) {
  if (!active()) {
    return;
  }
  QueuedSample sample;
  sample.kind = SampleKind::ScanProgress;
  sample.core_state = core_state;
  sample.scan_progress = progress;
  enqueueSample(sample);
}

void RecordingService::recordAlarm(const AlarmEvent& alarm) {
  if (!active()) {
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

void RecordingService::recordQueuedSample(const QueuedSample& sample) {
  switch (sample.kind) {
    case SampleKind::RobotState:
      append(session_dir_ / "raw" / "core" / "robot_state.jsonl", robotStateJson(sample.robot_state));
      break;
    case SampleKind::ContactState:
      append(session_dir_ / "raw" / "core" / "contact_state.jsonl", contactJson(sample.contact_state));
      break;
    case SampleKind::ScanProgress:
      append(session_dir_ / "raw" / "core" / "scan_progress.jsonl", progressJson(sample.core_state, sample.scan_progress));
      break;
  }
}

void RecordingService::enqueueSample(const QueuedSample& sample) {
  if (!sample_queue_.try_enqueue(sample)) {
    ++recorder_status_.dropped_samples;
  }
}

void RecordingService::recorderLoop() {
  QueuedSample sample;
  while (true) {
    if (sample_queue_.try_dequeue(sample)) {
      recordQueuedSample(sample);
      continue;
    }
    if (stop_worker_.load()) {
      break;
    }
    std::this_thread::sleep_for(std::chrono::milliseconds(1));
  }
}

void RecordingService::stopWorker(bool drain_pending) {
  active_.store(false);
  if (recorder_thread_.joinable()) {
    stop_worker_.store(true);
    recorder_thread_.join();
  }
  if (!drain_pending) {
    sample_queue_.clear();
    return;
  }
  QueuedSample pending;
  while (sample_queue_.try_dequeue(pending)) {
    recordQueuedSample(pending);
  }
}

}  // namespace robot_core
