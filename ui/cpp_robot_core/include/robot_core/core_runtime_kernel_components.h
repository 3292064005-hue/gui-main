#pragma once

#include <mutex>
#include <set>
#include <string>
#include <vector>

#include "robot_core/contact_gate.h"
#include "robot_core/contact_observer.h"
#include "robot_core/execution_plan_runtime.h"
#include "robot_core/force_control_config.h"
#include "robot_core/model_authority.h"
#include "robot_core/nrt_motion_service.h"
#include "robot_core/recording_service.h"
#include "robot_core/recovery_kernel.h"
#include "robot_core/recovery_manager.h"
#include "robot_core/recovery_policy.h"
#include "robot_core/robot_state_hub.h"
#include "robot_core/rt_motion_service.h"
#include "robot_core/runtime_types.h"
#include "robot_core/safety_service.h"
#include "robot_core/scan_plan_parser.h"
#include "robot_core/scan_plan_validator.h"
#include "robot_core/sdk_robot_facade.h"
#include "robot_core/state_machine_guard.h"

namespace robot_core {

struct RuntimeAuthorityLease {
  bool active{false};
  std::string lease_id;
  std::string actor_id;
  std::string workspace;
  std::string role;
  std::string session_id;
  std::string source;
  std::string intent_reason;
  std::string deployment_profile;
  int64_t acquired_ts_ns{0};
  int64_t refreshed_ts_ns{0};
  std::set<std::string> granted_claims{};
};

struct RuntimeLaneScheduler {
  mutable std::mutex command;
  mutable std::mutex query;
  mutable std::mutex rt;
};

struct RuntimeStateStore {
  mutable std::mutex mutex;
  RuntimeConfig config{};
  RobotCoreState execution_state{RobotCoreState::Disconnected};
  bool controller_online{false};
  bool powered{false};
  bool automatic_mode{false};
  bool tool_ready{false};
  bool tcp_ready{false};
  bool load_ready{false};
  bool pressure_fresh{false};
  bool robot_state_fresh{false};
  bool rt_jitter_ok{true};
  std::string fault_code;
  std::string session_id;
  std::string session_dir;
  std::string plan_id;
  std::string plan_hash;
  std::string locked_scan_plan_hash;
  std::string strict_runtime_freeze_gate{"enforce"};
  std::string frozen_device_roster_json;
  std::string frozen_safety_thresholds_json;
  std::string frozen_device_health_snapshot_json;
  std::string frozen_session_freeze_policy_json;
  std::vector<std::string> frozen_execution_critical_fields{};
  std::vector<std::string> frozen_evidence_only_fields{};
  bool frozen_recheck_on_start_procedure{true};
  bool plan_loaded{false};
  int total_points{0};
  int total_segments{0};
  int path_index{0};
  int frame_id{0};
  int active_segment{0};
  int active_waypoint_index{0};
  int retreat_ticks_remaining{0};
  RobotCoreState retreat_completion_state{RobotCoreState::AutoReady};
  int64_t session_locked_ts_ns{0};
  double progress_pct{0.0};
  double phase{0.0};
  double pressure_current{0.0};
  int64_t contact_stable_since_ns{0};
  std::string last_transition;
  std::string state_reason;
  double image_quality{0.0};
  double feature_confidence{0.0};
  double quality_score{0.0};
  std::string quality_source{"unavailable"};
  bool quality_available{false};
  bool quality_authoritative{false};
  ContactTelemetry contact_state{};
};

struct RuntimeAuthorityKernel {
  RuntimeAuthorityLease lease{};
  std::set<std::string> injected_faults{};
};

struct RuntimeQueryProjector {
  RobotStateHub robot_state_hub{};
};

struct RuntimeEvidenceProjector {
  FinalVerdict last_final_verdict{};
  std::vector<DeviceHealth> devices{};
  std::vector<AlarmEvent> pending_alarms{};
  RecordingService recording_service{};
};

struct RuntimeProcedureExecutor {
  ExecutionPlanRuntime execution_plan_runtime{};
  bool scan_procedure_active{false};
  ContactGate contact_gate{};
  ContactObserver contact_observer{};
  NrtMotionService nrt_motion_service{};
  RtMotionService rt_motion_service{};
  RecoveryManager recovery_manager{};
  RecoveryKernel recovery_kernel{};
  RecoveryPolicy recovery_policy{};
  ScanPlanParser scan_plan_parser{};
  ScanPlanValidator scan_plan_validator{};
  StateMachineGuard state_machine_guard{};
  SdkRobotFacade sdk_robot{};
  ForceControlLimits force_limits{loadForceControlLimits()};
};

struct RuntimeKernelServices {
  SafetyService safety_service{};
  ModelAuthority model_authority{};
};

}  // namespace robot_core
