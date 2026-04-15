#include "robot_core/recording_service.h"

#include <chrono>
#include <filesystem>
#include <fstream>
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
      field("runtime_source", quote(state.runtime_source)),
      field("pose_source", quote(state.pose_source)),
      field("force_source", quote(state.force_source)),
      field("pose_available", boolLiteral(state.pose_available)),
      field("force_available", boolLiteral(state.force_available)),
      field("pose_authoritative", boolLiteral(state.pose_authoritative)),
      field("force_authoritative", boolLiteral(state.force_authoritative)),
  });
}

std::string contactJson(const ContactTelemetry& contact) {
  using namespace json;
  return object({
      field("mode", quote(contact.mode)),
      field("confidence", formatDouble(contact.confidence)),
      field("pressure_current", formatDouble(contact.pressure_current)),
      field("recommended_action", quote(contact.recommended_action)),
      field("pressure_source", quote(contact.pressure_source)),
      field("quality_source", quote(contact.quality_source)),
      field("pressure_available", boolLiteral(contact.pressure_available)),
      field("quality_available", boolLiteral(contact.quality_available)),
      field("authoritative", boolLiteral(contact.authoritative)),
      field("contact_stable", boolLiteral(contact.contact_stable)),
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
  writeConsumerManifest();
  stop_worker_.store(false);
  recorder_thread_ = std::thread(&RecordingService::recorderLoop, this);
}

void RecordingService::closeSession() {
  active_.store(false);
  recorder_status_.recording = false;
  stopWorker(true);
  materializeConsumerArtifacts();
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
  QueuedSample sample;
  sample.kind = SampleKind::AlarmEvent;
  sample.alarm_event = alarm;
  enqueueSample(sample);
}

void RecordingService::append(const std::filesystem::path& path, const std::string& payload_json, int64_t source_ts_ns) {
  using namespace json;
  ++seq_;
  recorder_status_.last_flush_ns = nowNs();
  const auto envelope = object({
      field("monotonic_ns", std::to_string(nowNs())),
      field("source_ts_ns", std::to_string(source_ts_ns > 0 ? source_ts_ns : recorder_status_.last_flush_ns)),
      field("seq", std::to_string(seq_)),
      field("session_id", quote(session_id_)),
      field("data", payload_json),
  });
  appendLine(path, envelope);
}

std::filesystem::path RecordingService::samplePath(const QueuedSample& sample) const {
  return session_dir_ / "raw" / "core" / (sampleStreamName(sample) + ".jsonl");
}

std::string RecordingService::sampleStreamName(const QueuedSample& sample) const {
  switch (sample.kind) {
    case SampleKind::RobotState: return "robot_state";
    case SampleKind::ContactState: return "contact_state";
    case SampleKind::ScanProgress: return "scan_progress";
    case SampleKind::AlarmEvent: return "alarm_event";
  }
  return "unknown";
}

std::string RecordingService::samplePayloadJson(const QueuedSample& sample) const {
  switch (sample.kind) {
    case SampleKind::RobotState: return robotStateJson(sample.robot_state);
    case SampleKind::ContactState: return contactJson(sample.contact_state);
    case SampleKind::ScanProgress: return progressJson(sample.core_state, sample.scan_progress);
    case SampleKind::AlarmEvent: return alarmJson(sample.alarm_event);
  }
  return "{}";
}


int64_t RecordingService::sampleSourceTimestampNs(const QueuedSample& sample) const {
  switch (sample.kind) {
    case SampleKind::RobotState: return sample.robot_state.timestamp_ns;
    case SampleKind::AlarmEvent: return sample.alarm_event.event_ts_ns;
    case SampleKind::ScanProgress: return sample.core_state.contact_stable_since_ns;
    case SampleKind::ContactState: return 0;
  }
  return 0;
}

void RecordingService::appendTimelineEntry(const QueuedSample& sample, const std::string& payload_json, int64_t source_ts_ns) {
  using namespace json;
  appendLine(session_dir_ / "raw" / "core" / "event_timeline.jsonl",
             object({
                 field("monotonic_ns", std::to_string(nowNs())),
                 field("source_ts_ns", std::to_string(source_ts_ns > 0 ? source_ts_ns : nowNs())),
                 field("session_id", quote(session_id_)),
                 field("stream", quote(sampleStreamName(sample))),
                 field("payload", payload_json),
             }));
}

void RecordingService::recordQueuedSample(const QueuedSample& sample) {
  const auto payload_json = samplePayloadJson(sample);
  const auto source_ts_ns = sampleSourceTimestampNs(sample);
  append(samplePath(sample), payload_json, source_ts_ns);
  appendTimelineEntry(sample, payload_json, source_ts_ns);
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


std::filesystem::path RecordingService::derivedPath(const std::string& name) const {
  return session_dir_ / "derived" / "core" / name;
}

void RecordingService::materializeConsumerArtifacts() {
  using namespace json;
  if (session_dir_.empty()) {
    return;
  }
  ensureDir(session_dir_ / "derived" / "core");

  const auto robot_state_path = session_dir_ / "raw" / "core" / "robot_state.jsonl";
  const auto contact_state_path = session_dir_ / "raw" / "core" / "contact_state.jsonl";
  const auto scan_progress_path = session_dir_ / "raw" / "core" / "scan_progress.jsonl";
  const auto alarm_path = session_dir_ / "raw" / "core" / "alarm_event.jsonl";
  const auto timeline_path = session_dir_ / "raw" / "core" / "event_timeline.jsonl";

  auto count_lines = [](const std::filesystem::path& path) -> int {
    if (!std::filesystem::exists(path)) {
      return 0;
    }
    std::ifstream in(path);
    int lines = 0;
    std::string line;
    while (std::getline(in, line)) {
      ++lines;
    }
    return lines;
  };

  const int robot_state_count = count_lines(robot_state_path);
  const int contact_state_count = count_lines(contact_state_path);
  const int scan_progress_count = count_lines(scan_progress_path);
  const int alarm_count = count_lines(alarm_path);
  const int timeline_count = count_lines(timeline_path);

  appendLine(derivedPath("telemetry_replay_index.json"), object({
      field("session_id", quote(session_id_)),
      field("consumer", quote("telemetry_replay")),
      field("ready", boolLiteral(robot_state_count > 0 && contact_state_count > 0 && scan_progress_count > 0)),
      field("event_timeline_path", quote("raw/core/event_timeline.jsonl")),
      field("robot_state_path", quote("raw/core/robot_state.jsonl")),
      field("contact_state_path", quote("raw/core/contact_state.jsonl")),
      field("scan_progress_path", quote("raw/core/scan_progress.jsonl")),
      field("robot_state_samples", std::to_string(robot_state_count)),
      field("contact_state_samples", std::to_string(contact_state_count)),
      field("scan_progress_samples", std::to_string(scan_progress_count)),
      field("timeline_events", std::to_string(timeline_count))
  }));

  appendLine(derivedPath("alarm_review_index.json"), object({
      field("session_id", quote(session_id_)),
      field("consumer", quote("alarm_review")),
      field("ready", boolLiteral(alarm_count > 0 && timeline_count >= alarm_count)),
      field("alarm_event_path", quote("raw/core/alarm_event.jsonl")),
      field("event_timeline_path", quote("raw/core/event_timeline.jsonl")),
      field("alarm_events", std::to_string(alarm_count)),
      field("timeline_events", std::to_string(timeline_count))
  }));

  appendLine(derivedPath("audit_timeline_index.json"), object({
      field("session_id", quote(session_id_)),
      field("consumer", quote("audit_timeline")),
      field("ready", boolLiteral(timeline_count > 0)),
      field("event_timeline_path", quote("raw/core/event_timeline.jsonl")),
      field("timeline_events", std::to_string(timeline_count))
  }));
}

void RecordingService::writeConsumerManifest() {
  using namespace json;
  const auto manifest = object({
      field("session_id", quote(session_id_)),
      field("streams", object({
          field("robot_state", quote("raw/core/robot_state.jsonl")),
          field("contact_state", quote("raw/core/contact_state.jsonl")),
          field("scan_progress", quote("raw/core/scan_progress.jsonl")),
          field("alarm_event", quote("raw/core/alarm_event.jsonl")),
          field("event_timeline", quote("raw/core/event_timeline.jsonl"))
      })),
      field("consumers", object({
          field("telemetry_replay", object({field("reads", stringArray({"robot_state", "contact_state", "scan_progress", "event_timeline"})), field("writes", stringArray({"derived/core/telemetry_replay_index.json"}))})),
          field("alarm_review", object({field("reads", stringArray({"alarm_event", "event_timeline"})), field("writes", stringArray({"derived/core/alarm_review_index.json"}))})),
          field("audit_timeline", object({field("reads", stringArray({"event_timeline"})), field("writes", stringArray({"derived/core/audit_timeline_index.json"}))}))
      }))
  });
  appendLine(session_dir_ / "raw" / "core" / "recording_manifest.json", manifest);
}

}  // namespace robot_core
