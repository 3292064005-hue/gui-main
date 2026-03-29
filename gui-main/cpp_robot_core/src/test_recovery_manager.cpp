#include "robot_core/recovery_manager.h"
#include "robot_core/safety_decision.h"

#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>
#include <vector>

namespace {

bool require(bool condition, const char* message) {
  if (!condition) {
    std::cerr << "[FAIL] " << message << std::endl;
    return false;
  }
  return true;
}

}  // namespace

int main() {
  using namespace std::chrono_literals;

  robot_core::RecoveryManager manager;
  manager.setRetrySettleWindow(20ms);

  manager.pauseAndHold();
  if (!require(manager.pauseHoldActive(), "pauseAndHold should mark hold as active")) {
    return 1;
  }
  if (!require(std::string(manager.currentStateName()) == "HOLDING", "pauseAndHold should expose HOLDING state")) {
    return 1;
  }
  if (!require(!manager.retreatCompleted(), "pauseAndHold should clear retreat completion")) {
    return 1;
  }

  manager.controlledRetract();
  if (!require(!manager.pauseHoldActive(), "controlledRetract should clear hold state")) {
    return 1;
  }
  if (!require(manager.retreatCompleted(), "controlledRetract should mark retreat as complete")) {
    return 1;
  }
  if (!require(std::string(manager.currentStateName()) == "CONTROLLED_RETRACT", "controlledRetract should expose CONTROLLED_RETRACT state")) {
    return 1;
  }

  std::atomic<int> attempts{0};
  manager.pauseAndHold();
  manager.setRetryCallback([&attempts]() {
    return ++attempts >= 2;
  });
  manager.triggerRetry(3, 10ms);

  const auto deadline = std::chrono::steady_clock::now() + 2s;
  while (manager.retryActive() && std::chrono::steady_clock::now() < deadline) {
    std::this_thread::sleep_for(5ms);
  }

  if (!require(!manager.retryActive(), "retry loop should finish within timeout")) {
    return 1;
  }
  if (!require(attempts.load() == 2, "retry callback should stop after the successful second attempt")) {
    return 1;
  }
  if (!require(std::string(manager.currentStateName()) == "RETRY_WAIT_STABLE", "successful retry should wait for stable force before ready")) {
    return 1;
  }

  const auto stable_start = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
  manager.updateStableCondition(true, stable_start);
  std::this_thread::sleep_for(25ms);
  const auto stable_end = std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now().time_since_epoch()).count();
  manager.updateStableCondition(true, stable_end);
  if (!require(std::string(manager.currentStateName()) == "RETRY_READY", "stable force window should expose RETRY_READY")) {
    return 1;
  }

  manager.updateStableCondition(false, stable_end + 1);
  if (!require(std::string(manager.currentStateName()) == "RETRY_WAIT_STABLE", "loss of stable force should fall back to RETRY_WAIT_STABLE")) {
    return 1;
  }

  manager.latchEstop();
  if (!require(std::string(manager.currentStateName()) == "ESTOP_LATCHED", "latchEstop should expose ESTOP_LATCHED")) {
    return 1;
  }
  manager.updateStableCondition(true, stable_end + 10'000'000);
  if (!require(std::string(manager.currentStateName()) == "ESTOP_LATCHED", "estop latched should not auto-resume")) {
    return 1;
  }

  const auto limits = robot_core::ForceControlLimits{};
  const auto force_state = robot_core::makeForceStateSnapshot(
      stable_end,
      0.0,
      std::vector<double>{0.0, 0.0, limits.warning_z_force_n + 1.0, 0.0, 0.0, 0.0},
      limits,
      limits.desired_contact_force_n);
  if (!require(
          robot_core::decideSafetyAction(force_state) == robot_core::SafetyDecision::WarnOnly,
          "warning band should map to WARN_ONLY")) {
    return 1;
  }

  std::cout << "Recovery manager smoke test passed." << std::endl;
  return 0;
}
