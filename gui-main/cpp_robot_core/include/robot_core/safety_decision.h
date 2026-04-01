#pragma once

#include "robot_core/force_state.h"

namespace robot_core {

enum class SafetyDecision {
  SafeContinue,
  WarnOnly,
  PauseHold,
  ControlledRetract,
  EstopLatch,
};

inline SafetyDecision decideSafetyAction(const ForceStateSnapshot& snapshot) {
  if (snapshot.freshness_state == ForceFreshnessState::EstopTimeout) {
    return SafetyDecision::EstopLatch;
  }
  if (snapshot.freshness_state == ForceFreshnessState::Timeout || snapshot.hard_limit_active) {
    return SafetyDecision::ControlledRetract;
  }
  if (snapshot.freshness_state == ForceFreshnessState::Stale) {
    return SafetyDecision::PauseHold;
  }
  if (snapshot.warning_active) {
    return SafetyDecision::WarnOnly;
  }
  return SafetyDecision::SafeContinue;
}

inline const char* safetyDecisionName(SafetyDecision decision) {
  switch (decision) {
    case SafetyDecision::SafeContinue: return "SAFE_CONTINUE";
    case SafetyDecision::WarnOnly: return "WARN_ONLY";
    case SafetyDecision::PauseHold: return "PAUSE_HOLD";
    case SafetyDecision::ControlledRetract: return "CONTROLLED_RETRACT";
    case SafetyDecision::EstopLatch: return "ESTOP_LATCH";
  }
  return "SAFE_CONTINUE";
}

}  // namespace robot_core
