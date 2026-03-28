#include "robot_core/recovery_manager.h"

#include <atomic>
#include <chrono>
#include <iostream>
#include <thread>

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
  if (!require(!manager.pauseHoldActive(), "successful retry should clear hold state")) {
    return 1;
  }
  if (!require(manager.retreatCompleted(), "successful retry should restore retreat completion")) {
    return 1;
  }
  if (!require(std::string(manager.currentStateName()) == "RETRY_READY", "successful retry should expose RETRY_READY")) {
    return 1;
  }

  manager.latchEstop();
  if (!require(std::string(manager.currentStateName()) == "ESTOP_LATCHED", "latchEstop should expose ESTOP_LATCHED")) {
    return 1;
  }

  std::cout << "Recovery manager smoke test passed." << std::endl;
  return 0;
}
