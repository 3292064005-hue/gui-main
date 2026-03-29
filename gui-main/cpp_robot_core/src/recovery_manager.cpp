#include "robot_core/recovery_manager.h"
#include <chrono>
#include <iostream>
#include <thread>

namespace robot_core {

RecoveryManager::RecoveryManager() = default;

RecoveryManager::~RecoveryManager() {
  cancelRetry();
  joinRetryThreadIfNeeded();
}

void RecoveryManager::pauseAndHold() {
  pause_hold_active_.store(true);
  retreat_completed_ = false;
  stable_since_ts_ns_.store(0);
  current_state_.store(RecoveryState::Holding);
}

void RecoveryManager::controlledRetract() {
  pause_hold_active_.store(false);
  retreat_completed_ = true;
  stable_since_ts_ns_.store(0);
  current_state_.store(RecoveryState::ControlledRetract);
}

bool RecoveryManager::retreatCompleted() const {
  return retreat_completed_;
}

bool RecoveryManager::pauseHoldActive() const {
  return pause_hold_active_.load();
}

void RecoveryManager::setRetryCallback(RetryFunction callback) {
  retry_callback_ = std::move(callback);
}

void RecoveryManager::triggerRetry(int max_attempts, std::chrono::milliseconds delay) {
  cancelRetry();
  joinRetryThreadIfNeeded();
  max_attempts_ = max_attempts;
  retry_delay_ = delay;
  retry_active_.store(true);
  stable_since_ts_ns_.store(0);
  current_state_.store(RecoveryState::Holding);
  retry_thread_ = std::thread(&RecoveryManager::retryLoop, this);
}

void RecoveryManager::cancelRetry() {
  retry_active_.store(false);
}

bool RecoveryManager::retryActive() const {
  return retry_active_.load();
}

void RecoveryManager::latchEstop() {
  cancelRetry();
  pause_hold_active_.store(false);
  retreat_completed_ = false;
  stable_since_ts_ns_.store(0);
  current_state_.store(RecoveryState::EstopLatched);
}

void RecoveryManager::resetToIdle() {
  cancelRetry();
  joinRetryThreadIfNeeded();
  pause_hold_active_.store(false);
  retreat_completed_ = true;
  stable_since_ts_ns_.store(0);
  current_state_.store(RecoveryState::Idle);
}

void RecoveryManager::setRetrySettleWindow(std::chrono::milliseconds window) {
  retry_settle_window_ = window;
}

void RecoveryManager::updateStableCondition(bool within_resume_band, int64_t now_ns) {
  const auto state = current_state_.load();
  if (state == RecoveryState::EstopLatched || state == RecoveryState::Idle) {
    return;
  }
  if (!within_resume_band) {
    stable_since_ts_ns_.store(0);
    if (state == RecoveryState::RetryReady) {
      current_state_.store(RecoveryState::RetryWaitStable);
    }
    return;
  }
  auto stable_since = stable_since_ts_ns_.load();
  if (stable_since <= 0) {
    stable_since_ts_ns_.store(now_ns);
    stable_since = now_ns;
  }
  if (state == RecoveryState::ControlledRetract || state == RecoveryState::Holding || state == RecoveryState::RetryWaitStable) {
    current_state_.store(RecoveryState::RetryWaitStable);
  }
  const auto elapsed_ns = now_ns - stable_since;
  if (elapsed_ns >= retry_settle_window_.count() * 1000LL * 1000LL) {
    pause_hold_active_.store(false);
    retreat_completed_ = true;
    current_state_.store(RecoveryState::RetryReady);
  }
}

RecoveryState RecoveryManager::currentState() const {
  return current_state_.load();
}

const char* RecoveryManager::currentStateName() const {
  switch (current_state_.load()) {
    case RecoveryState::Idle:
      return "IDLE";
    case RecoveryState::Holding:
      return "HOLDING";
    case RecoveryState::ControlledRetract:
      return "CONTROLLED_RETRACT";
    case RecoveryState::RetryWaitStable:
      return "RETRY_WAIT_STABLE";
    case RecoveryState::RetryReady:
      return "RETRY_READY";
    case RecoveryState::EstopLatched:
      return "ESTOP_LATCHED";
  }
  return "UNKNOWN";
}

void RecoveryManager::joinRetryThreadIfNeeded() {
  if (retry_thread_.joinable() && retry_thread_.get_id() != std::this_thread::get_id()) {
    retry_thread_.join();
  }
}

void RecoveryManager::retryLoop() {
  for (int attempt = 1; attempt <= max_attempts_ && retry_active_.load(); ++attempt) {
    std::this_thread::sleep_for(retry_delay_);
    if (!retry_active_.load()) {
      break;
    }
    std::cout << "RecoveryManager: Retry attempt " << attempt << "/" << max_attempts_ << std::endl;
    if (retry_callback_ && retry_callback_()) {
      retry_active_.store(false);
      pause_hold_active_.store(true);
      retreat_completed_ = false;
      stable_since_ts_ns_.store(0);
      current_state_.store(RecoveryState::RetryWaitStable);
      return;
    }
  }
  retry_active_.store(false);
}

}  // namespace robot_core
