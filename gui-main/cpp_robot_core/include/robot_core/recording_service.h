#pragma once

#include <filesystem>
#include <string>

#include "robot_core/runtime_types.h"

namespace robot_core {

class RecordingService {
public:
  void openSession(const std::filesystem::path& session_dir, const std::string& session_id);
  void closeSession();
  bool active() const;
  RecorderStatus status() const;
  void recordRobotState(const RobotStateSnapshot& state);
  void recordContactState(const ContactTelemetry& contact);
  void recordScanProgress(const CoreStateSnapshot& core_state, const ScanProgress& progress);
  void recordAlarm(const AlarmEvent& alarm);

private:
  void append(const std::filesystem::path& path, const std::string& payload_json);

  std::filesystem::path session_dir_;
  std::string session_id_;
  int64_t seq_{0};
  bool active_{false};
  RecorderStatus recorder_status_{};
};

}  // namespace robot_core
