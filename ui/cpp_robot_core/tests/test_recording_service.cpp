#include "robot_core/recording_service.h"
#include "robot_core/runtime_types.h"

#include <filesystem>
#include <fstream>
#include <iostream>
#include <string>

namespace {

bool require(bool condition, const char* message) {
  if (!condition) {
    std::cerr << "[FAIL] " << message << std::endl;
    return false;
  }
  return true;
}

int countLines(const std::filesystem::path& path) {
  std::ifstream in(path);
  int lines = 0;
  std::string line;
  while (std::getline(in, line)) {
    ++lines;
  }
  return lines;
}

}  // namespace

int main() {
  namespace fs = std::filesystem;

  const auto root = fs::temp_directory_path() / "spine_recording_service_test";
  std::error_code ec;
  fs::remove_all(root, ec);

  robot_core::RecordingService service;
  robot_core::RobotStateSnapshot robot_state;
  robot_state.timestamp_ns = 42;
  robot_state.joint_pos = {1.0, 2.0, 3.0};
  service.recordRobotState(robot_state);
  if (!require(!fs::exists(root / "raw" / "core" / "robot_state.jsonl"), "recording before openSession should be ignored")) {
    return 1;
  }

  service.openSession(root, "session-test");

  robot_state.last_event = "rt_sample";
  service.recordRobotState(robot_state);

  robot_core::ContactTelemetry contact;
  contact.mode = "STABLE_CONTACT";
  contact.pressure_current = 12.5;
  service.recordContactState(contact);

  robot_core::CoreStateSnapshot core_state;
  core_state.execution_state = robot_core::RobotCoreState::Scanning;
  core_state.session_id = "session-test";
  robot_core::ScanProgress progress;
  progress.active_segment = 2;
  progress.frame_id = 9;
  progress.overall_progress = 57.5;
  service.recordScanProgress(core_state, progress);

  robot_core::AlarmEvent alarm;
  alarm.message = "force excursion";
  alarm.session_id = "session-test";
  service.recordAlarm(alarm);

  service.closeSession();

  const auto robot_state_path = root / "raw" / "core" / "robot_state.jsonl";
  const auto contact_state_path = root / "raw" / "core" / "contact_state.jsonl";
  const auto scan_progress_path = root / "raw" / "core" / "scan_progress.jsonl";
  const auto alarm_path = root / "raw" / "core" / "alarm_event.jsonl";
  const auto timeline_path = root / "raw" / "core" / "event_timeline.jsonl";
  const auto manifest_path = root / "raw" / "core" / "recording_manifest.json";
  const auto replay_index_path = root / "derived" / "core" / "telemetry_replay_index.json";
  const auto alarm_index_path = root / "derived" / "core" / "alarm_review_index.json";
  const auto audit_index_path = root / "derived" / "core" / "audit_timeline_index.json";

  if (!require(fs::exists(robot_state_path), "robot state log should exist after closeSession")) {
    return 1;
  }
  if (!require(fs::exists(contact_state_path), "contact state log should exist after closeSession")) {
    return 1;
  }
  if (!require(fs::exists(scan_progress_path), "scan progress log should exist after closeSession")) {
    return 1;
  }
  if (!require(fs::exists(alarm_path), "alarm log should exist after closeSession")) {
    return 1;
  }
  if (!require(fs::exists(timeline_path), "event timeline should exist after closeSession")) {
    return 1;
  }
  if (!require(fs::exists(manifest_path), "recording manifest should exist after openSession")) {
    return 1;
  }
  if (!require(fs::exists(replay_index_path), "telemetry replay index should exist after closeSession")) {
    return 1;
  }
  if (!require(fs::exists(alarm_index_path), "alarm review index should exist after closeSession")) {
    return 1;
  }
  if (!require(fs::exists(audit_index_path), "audit timeline index should exist after closeSession")) {
    return 1;
  }
  if (!require(countLines(robot_state_path) == 1, "robot state log should contain one flushed sample")) {
    return 1;
  }
  if (!require(countLines(contact_state_path) == 1, "contact state log should contain one flushed sample")) {
    return 1;
  }
  if (!require(countLines(scan_progress_path) == 1, "scan progress log should contain one flushed sample")) {
    return 1;
  }
  if (!require(countLines(alarm_path) == 1, "alarm log should contain one flushed event")) {
    return 1;
  }
  if (!require(countLines(timeline_path) == 4, "event timeline should contain all four flushed samples")) {
    return 1;
  }

  const auto status = service.status();
  if (!require(!status.recording, "closeSession should clear recording flag")) {
    return 1;
  }
  if (!require(status.session_id == "session-test", "status should preserve session id")) {
    return 1;
  }

  fs::remove_all(root, ec);
  std::cout << "Recording service flush test passed." << std::endl;
  return 0;
}
