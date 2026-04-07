#pragma once

#include <string>
#include <vector>

#include "robot_core/force_control_config.h"
#include "robot_core/runtime_types.h"

namespace robot_core {

class RecoveryManager;

struct RecoveryKernelSnapshot {
  std::string summary_state{"ready"};
  std::string summary_label{"safety/recovery kernel"};
  std::string detail{"Safety/recovery kernel owns hold, retract, retry and latched-fault semantics."};
  std::vector<std::string> policy_layers{"L0_hard_block", "L1_runtime_guard", "L2_auto_recovery", "L3_evidence_ack"};
  std::vector<std::string> supported_actions{"pause_hold", "controlled_retract", "retry_wait_stable", "retry_ready", "estop_latched"};
  bool pause_resume_enabled{true};
  bool safe_retreat_enabled{true};
  bool operator_ack_required_for_fault_latched{true};
  bool runtime_guard_enforced{true};
  std::string recovery_state{"Idle"};
  std::string collision_behavior{"pause_hold"};
  double resume_force_band_n{0.0};
  double warning_z_force_n{0.0};
  double max_z_force_n{0.0};
  double sensor_timeout_ms{0.0};
  double stale_telemetry_ms{0.0};
  double emergency_retract_mm{0.0};
};

class RecoveryKernel {
public:
  RecoveryKernel() = default;
  RecoveryKernelSnapshot snapshot(const RuntimeConfig& config,
                                  const ForceControlLimits& limits,
                                  const RecoveryManager& recovery_manager) const;
};

}  // namespace robot_core
