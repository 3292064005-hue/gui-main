#pragma once
#include <atomic>
#include <chrono>
#include <cstdint>
#include <functional>
#include <thread>

namespace robot_core {
enum class RecoveryState {
  Idle,
  Holding,
  ControlledRetract,
  RetryWaitStable,
  RetryReady,
  EstopLatched,
};

class RecoveryManager {
public:
  RecoveryManager();
  ~RecoveryManager();

  void pauseAndHold();
  void controlledRetract();
  bool retreatCompleted() const;
  bool pauseHoldActive() const;

  using RetryFunction = std::function<bool()>;
  void setRetryCallback(RetryFunction callback);
  void triggerRetry(int max_attempts = 3, std::chrono::milliseconds delay = std::chrono::milliseconds(1000));
  void cancelRetry();
  bool retryActive() const;
  void latchEstop();
  void resetToIdle();

  void setRetrySettleWindow(std::chrono::milliseconds window);
  void updateStableCondition(bool within_resume_band, int64_t now_ns);

  RecoveryState currentState() const;
  const char* currentStateName() const;

private:
  void joinRetryThreadIfNeeded();
  void retryLoop();

  bool retreat_completed_{true};
  std::atomic<bool> pause_hold_active_{false};
  std::atomic<RecoveryState> current_state_{RecoveryState::Idle};
  RetryFunction retry_callback_;
  std::atomic<bool> retry_active_{false};
  std::atomic<int> max_attempts_{0};
  std::chrono::milliseconds retry_delay_{std::chrono::milliseconds(1000)};
  std::chrono::milliseconds retry_settle_window_{std::chrono::milliseconds(150)};
  std::atomic<int64_t> stable_since_ts_ns_{0};
  std::thread retry_thread_;
};
}
