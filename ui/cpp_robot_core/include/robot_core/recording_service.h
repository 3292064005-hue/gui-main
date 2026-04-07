#pragma once

#include <atomic>
#include <filesystem>
#include <string>
#include <thread>

#include "robot_core/runtime_types.h"
#include "spsc_queue.hpp"

namespace robot_core {

/**
 * @brief Session recorder that decouples RT-path sample capture from disk I/O.
 *
 * 高频 RT 样本只允许入队，不允许在调用点进行 JSON 序列化或文件写入。
 * 真正的落盘由后台消费者线程完成，以避免反压 1ms 主循环。
 */
class RecordingService {
public:
  RecordingService();
  ~RecordingService();

  /**
   * @brief Open a recording session and start the asynchronous recorder worker.
   *
   * @param session_dir Session root directory.
   * @param session_id Logical session identifier written into recorder envelopes.
   * @return void
   * @throws No exceptions are thrown explicitly. Filesystem failures are handled by the underlying helpers.
   */
  void openSession(const std::filesystem::path& session_dir, const std::string& session_id);

  /**
   * @brief Close the active session and flush queued samples.
   *
   * @param None.
   * @return void
   * @throws No exceptions are thrown explicitly.
   */
  void closeSession();

  /**
   * @brief Report whether recording is currently enabled.
   *
   * @param None.
   * @return true when a session is active; otherwise false.
   * @throws No exceptions are thrown.
   */
  bool active() const;

  /**
   * @brief Return the current recorder status snapshot.
   *
   * @param None.
   * @return RecorderStatus Current recorder status.
   * @throws No exceptions are thrown.
   */
  RecorderStatus status() const;

  /**
   * @brief Queue a robot-state sample for asynchronous persistence.
   *
   * @param state Robot-state snapshot sampled by the runtime.
   * @return void
   * @throws No exceptions are thrown explicitly. Queue overflow is counted as dropped samples.
   */
  void recordRobotState(const RobotStateSnapshot& state);

  /**
   * @brief Queue a contact-state sample for asynchronous persistence.
   *
   * @param contact Contact telemetry snapshot sampled by the runtime.
   * @return void
   * @throws No exceptions are thrown explicitly. Queue overflow is counted as dropped samples.
   */
  void recordContactState(const ContactTelemetry& contact);

  /**
   * @brief Queue a scan-progress sample for asynchronous persistence.
   *
   * @param core_state Core runtime state paired with scan progress.
   * @param progress Scan progress snapshot.
   * @return void
   * @throws No exceptions are thrown explicitly. Queue overflow is counted as dropped samples.
   */
  void recordScanProgress(const CoreStateSnapshot& core_state, const ScanProgress& progress);

  /**
   * @brief Persist alarm events immediately on the non-RT event path.
   *
   * @param alarm Alarm event to append.
   * @return void
   * @throws No exceptions are thrown explicitly.
   */
  void recordAlarm(const AlarmEvent& alarm);

private:
  enum class SampleKind {
    RobotState,
    ContactState,
    ScanProgress,
  };

  struct QueuedSample {
    SampleKind kind{SampleKind::RobotState};
    RobotStateSnapshot robot_state{};
    ContactTelemetry contact_state{};
    CoreStateSnapshot core_state{};
    ScanProgress scan_progress{};
  };

  static constexpr std::size_t kQueueCapacity = 1024;

  void append(const std::filesystem::path& path, const std::string& payload_json);
  void recordQueuedSample(const QueuedSample& sample);
  void enqueueSample(const QueuedSample& sample);
  void recorderLoop();
  void stopWorker(bool drain_pending);

  std::filesystem::path session_dir_;
  std::string session_id_;
  int64_t seq_{0};
  std::atomic<bool> active_{false};
  RecorderStatus recorder_status_{};
  spine_core::SPSCQueue<QueuedSample> sample_queue_{kQueueCapacity};
  std::atomic<bool> stop_worker_{false};
  std::thread recorder_thread_;
};

}  // namespace robot_core
