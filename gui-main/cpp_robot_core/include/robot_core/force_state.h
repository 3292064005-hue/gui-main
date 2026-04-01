#pragma once

#include <cmath>
#include <cstdint>
#include <string>
#include <vector>

#include "robot_core/force_control_config.h"

namespace robot_core {

enum class ForceFreshnessState {
  Fresh,
  Stale,
  Timeout,
  EstopTimeout,
};

struct ForceStateSnapshot {
  int64_t ts_ns{0};
  std::vector<double> wrench_n{0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
  std::string status{"OK"};
  std::string source{"mock_force_sensor"};
  double age_ms{0.0};
  ForceFreshnessState freshness_state{ForceFreshnessState::Fresh};
  bool warning_active{false};
  bool hard_limit_active{false};
  bool within_resume_band{false};
  int64_t stable_since_ts_ns{0};
};

inline ForceFreshnessState evaluateForceFreshness(double age_ms, const ForceControlLimits& limits) {
  if (age_ms > limits.sensor_timeout_ms * 2.0) {
    return ForceFreshnessState::EstopTimeout;
  }
  if (age_ms > limits.sensor_timeout_ms) {
    return ForceFreshnessState::Timeout;
  }
  if (age_ms > limits.stale_telemetry_ms) {
    return ForceFreshnessState::Stale;
  }
  return ForceFreshnessState::Fresh;
}

inline ForceStateSnapshot makeForceStateSnapshot(
    int64_t ts_ns,
    double age_ms,
    const std::vector<double>& wrench_n,
    const ForceControlLimits& limits,
    double desired_contact_force,
    int64_t stable_since_ts_ns = 0,
    const std::string& source = "mock_force_sensor") {
  ForceStateSnapshot snapshot;
  snapshot.ts_ns = ts_ns;
  snapshot.wrench_n = wrench_n;
  snapshot.source = source;
  snapshot.age_ms = age_ms;
  snapshot.freshness_state = evaluateForceFreshness(age_ms, limits);
  const double force_z = wrench_n.size() > 2 ? std::fabs(wrench_n[2]) : 0.0;
  const double force_xy = std::hypot(wrench_n.size() > 0 ? wrench_n[0] : 0.0, wrench_n.size() > 1 ? wrench_n[1] : 0.0);
  snapshot.warning_active = force_z >= limits.warning_z_force_n;
  snapshot.hard_limit_active = force_z >= limits.max_z_force_n || force_xy >= limits.max_xy_force_n;
  snapshot.within_resume_band = std::fabs(force_z - desired_contact_force) <= limits.resume_force_band_n;
  snapshot.stable_since_ts_ns = snapshot.within_resume_band ? stable_since_ts_ns : 0;
  switch (snapshot.freshness_state) {
    case ForceFreshnessState::Fresh: snapshot.status = snapshot.hard_limit_active ? "HARD_LIMIT" : (snapshot.warning_active ? "WARN" : "OK"); break;
    case ForceFreshnessState::Stale: snapshot.status = "STALE"; break;
    case ForceFreshnessState::Timeout: snapshot.status = "TIMEOUT"; break;
    case ForceFreshnessState::EstopTimeout: snapshot.status = "ESTOP_TIMEOUT"; break;
  }
  return snapshot;
}

}  // namespace robot_core
