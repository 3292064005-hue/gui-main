#pragma once

#include <vector>

#include "robot_core/runtime_types.h"

namespace robot_core {
class SafetyService {
public:
  bool checkNetworkStable() const;
  bool checkNetworkStable(bool controller_online, bool pressure_fresh, bool robot_state_fresh, bool rt_jitter_ok) const;
  SafetyStatus evaluate(bool controller_online, bool powered, bool automatic_mode,
                        bool session_locked, bool path_loaded, bool pressure_fresh,
                        bool robot_state_fresh, bool pressure_safe, bool rt_jitter_ok,
                        bool tool_ready, bool tcp_ready, bool load_ready) const;
};
}  // namespace robot_core
