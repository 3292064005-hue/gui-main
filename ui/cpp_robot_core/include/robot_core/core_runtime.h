#pragma once

#include <memory>
#include <mutex>
#include <string_view>
#include <set>
#include <string>
#include <vector>

#include "robot_core/contact_gate.h"
#include "robot_core/contact_observer.h"
#include "robot_core/force_control_config.h"
#include "robot_core/model_authority.h"
#include "robot_core/nrt_motion_service.h"
#include "robot_core/recording_service.h"
#include "robot_core/recovery_kernel.h"
#include "robot_core/recovery_policy.h"
#include "robot_core/scan_plan_parser.h"
#include "robot_core/scan_plan_validator.h"
#include "robot_core/sdk_robot_facade.h"
#include "robot_core/state_machine_guard.h"
#include "robot_core/recovery_manager.h"
#include "robot_core/robot_state_hub.h"
#include "robot_core/rt_motion_service.h"
#include "robot_core/runtime_command_contracts.h"
#include "robot_core/runtime_types.h"
#include "robot_core/safety_service.h"

namespace robot_core {

class CoreRuntime;
class CoreRuntimeDispatcher;
class CoreRuntimeContractPublisher;

class CoreRuntime {
public:
  enum class RuntimeLane {
    Command,
    Query,
    RtControl,
  };

  CoreRuntime();
  ~CoreRuntime();

  /**
   * @brief Dispatch a JSON command onto the canonical runtime lane.
   * @param line Canonical JSON command envelope received from the control plane.
   * @return JSON reply envelope preserving request_id and compatibility fields.
   * @throws No exceptions are propagated to callers; malformed or unsupported commands
   *     are converted into explicit reply envelopes.
   * @boundary Dispatch is serialized per-lane so that query traffic does not share the
   *     same outer execution lane as mutating commands or RT maintenance loops.
   */
  std::string handleCommandJson(const std::string& line);

  /**
   * @brief Build a telemetry snapshot for the query/telemetry lane.
   * @return Point-in-time runtime telemetry snapshot.
   * @throws No exceptions are thrown.
   * @boundary Only the minimal shared state copy/clear section is performed under the
   *     runtime state mutex; snapshot materialization happens on the query lane.
   */
  TelemetrySnapshot takeTelemetrySnapshot();

  /**
   * @brief Execute one RT maintenance tick.
   * @throws No exceptions are thrown.
   * @boundary Serialized on the RT lane; the measured loop must not share the outer
   *     lane mutex with command/query dispatch.
   */
  void rtStep();
  /**
   * @brief Publish a measured RT loop timing sample into the runtime state.
   * @param scheduled_period_ms Nominal loop period enforced by the scheduler.
   * @param execution_ms Measured callback execution time.
   * @param wake_jitter_ms Absolute wake-up jitter for the sample.
   * @param overrun True when the RT loop missed its deadline.
   * @throws No exceptions are thrown.
   * @boundary Updates only timing-derived runtime state and preserves the
   *     existing external command/telemetry interfaces.
   */
  void recordRtLoopSample(double scheduled_period_ms, double execution_ms, double wake_jitter_ms, bool overrun);

  /**
   * @brief Poll live robot state into the runtime mirror.
   * @throws No exceptions are thrown.
   * @boundary Runs on the RT/control maintenance lane and updates only the mirrored
   *     robot-state cache.
   */
  void statePollStep();

  /**
   * @brief Evaluate watchdog and recovery policies.
   * @throws No exceptions are thrown.
   * @boundary Runs on the RT/control maintenance lane and may enqueue alarms or force
   *     state transitions when safety conditions are violated.
   */
  void watchdogStep();
  void setState(RobotCoreState state);
  RobotCoreState state() const;


private:
  friend class CoreRuntimeDispatcher;
  friend class CoreRuntimeContractPublisher;


  std::string handleConnectionCommand(const RuntimeCommandInvocation& invocation);
  std::string handlePowerModeCommand(const RuntimeCommandInvocation& invocation);
  std::string handleValidationCommand(const RuntimeCommandInvocation& invocation);
  std::string handleQueryCommand(const RuntimeCommandInvocation& invocation);
  std::string handleFaultInjectionCommand(const RuntimeCommandInvocation& invocation);
  std::string handleSessionCommand(const RuntimeCommandInvocation& invocation);
  std::string handleExecutionCommand(const RuntimeCommandInvocation& invocation);
#include "robot_core/generated_runtime_command_typed_handler_decls.inc"
  template <typename RequestT>
  std::string handleTypedCommand(const RuntimeCommandContext& context, const RequestT& request);
  std::string dispatchTypedCommand(const RuntimeCommandInvocation& invocation);
  void updateKinematicsLocked();
  void updateQualityLocked(const RtObservedState& observed, const RtPhaseTelemetry& phase_telemetry);
  void updateContactAndProgressLocked(const RtObservedState& observed);
  void refreshDeviceHealthLocked(int64_t ts_ns, const RtObservedState& observed);
  bool simulatedTelemetryAllowedLocked() const;
  SafetyStatus evaluateSafetyLocked() const;
  /**
   * @brief Queue an alarm for telemetry publication and asynchronous recorder persistence.
   * @param severity Canonical severity label.
   * @param source Subsystem that raised the alarm.
   * @param message Human-readable alarm detail.
   * @param workflow_step Optional workflow step associated with the alarm.
   * @param request_id Optional originating command request id.
   * @param auto_action Optional automatic recovery action taken by the runtime.
   * @return void
   * @throws No exceptions are thrown.
   * @boundary Runs under ``state_mutex_`` and must only copy alarm payload into in-memory queues.
   *     JSON serialization and filesystem writes are delegated to ``RecordingService``'s worker thread.
   */
  void queueAlarmLocked(const std::string& severity, const std::string& source, const std::string& message, const std::string& workflow_step = "", const std::string& request_id = "", const std::string& auto_action = "");
  CoreStateSnapshot buildCoreSnapshotLocked() const;
  ScanProgress buildScanProgressLocked() const;
  struct PendingRecordBundle {
    bool enabled{false};
    RobotStateSnapshot robot_state{};
    ContactTelemetry contact_state{};
    CoreStateSnapshot core_state{};
    ScanProgress scan_progress{};
  };
  PendingRecordBundle buildRecordBundleLocked() const;
  void flushRecordBundle(const PendingRecordBundle& bundle);
  void applyConfigSnapshotLocked(const std::string& config_snapshot_json);
  void loadPlanLocked(const std::string& scan_plan_json, const std::string& scan_plan_hash = "");
  FinalVerdict compileScanPlanVerdictLocked(const std::string& config_snapshot_json, const std::string& scan_plan_json, const std::string& scan_plan_hash = "");
  void appendMainlineContractIssuesLocked(std::vector<std::string>* blockers, std::vector<std::string>* warnings) const;
  bool sessionFreezeConsistentLocked() const;
  std::string capabilityContractJsonLocked() const;
  std::string robotFamilyContractJsonLocked() const;
  std::string vendorBoundaryContractJsonLocked() const;
  std::string modelAuthorityContractJsonLocked() const;
  std::string safetyRecoveryContractJsonLocked() const;
  std::string hardwareLifecycleContractJsonLocked() const;
  std::string rtKernelContractJsonLocked() const;
  std::string sessionDriftContractJsonLocked() const;
  std::string authoritativeRuntimeEnvelopeJsonLocked() const;
  std::string authoritativeRuntimeEnvelopeJsonInternal() const;
  std::string controlGovernanceContractJsonLocked() const;
  std::string controlGovernanceContractJsonInternal() const;
  std::string controllerEvidenceJsonLocked() const;
  std::string controllerEvidenceJsonInternal() const;
  std::string dualStateMachineContractJsonLocked() const;
  std::string mainlineExecutorContractJsonLocked() const;
  std::string releaseContractJsonLocked() const;
  std::string releaseContractJsonInternal() const;
  std::string deploymentContractJsonLocked() const;
  std::string deploymentContractJsonInternal() const;
  std::string faultInjectionContractJsonLocked() const;
  bool applyFaultInjectionLocked(const std::string& fault_name, std::string* error_message);
  void clearInjectedFaultsLocked();
  std::string finalVerdictJson(const FinalVerdict& verdict) const;
  std::string replyJson(const std::string& request_id, bool ok, const std::string& message, const std::string& data_json = "{}") const;

  RuntimeLane commandLaneFor(std::string_view command) const;

  mutable std::mutex state_mutex_;
  mutable std::mutex command_lane_mutex_;
  mutable std::mutex query_lane_mutex_;
  mutable std::mutex rt_lane_mutex_;
  RuntimeConfig config_{};
  RobotCoreState execution_state_{RobotCoreState::Disconnected};
  bool controller_online_{false};
  bool powered_{false};
  bool automatic_mode_{false};
  bool tool_ready_{false};
  bool tcp_ready_{false};
  bool load_ready_{false};
  bool pressure_fresh_{false};
  bool robot_state_fresh_{false};
  bool rt_jitter_ok_{true};
  std::string fault_code_;
  std::string session_id_;
  std::string session_dir_;
  std::string plan_id_;
  std::string plan_hash_;
  std::string locked_scan_plan_hash_;
  bool plan_loaded_{false};
  int total_points_{0};
  int total_segments_{0};
  int path_index_{0};
  int frame_id_{0};
  int active_segment_{0};
  int active_waypoint_index_{0};
  int retreat_ticks_remaining_{0};
  int64_t session_locked_ts_ns_{0};
  double progress_pct_{0.0};
  double phase_{0.0};
  double pressure_current_{0.0};
  int64_t contact_stable_since_ns_{0};
  std::string last_transition_;
  std::string state_reason_;
  double image_quality_{0.0};
  double feature_confidence_{0.0};
  double quality_score_{0.0};
  std::string quality_source_{"unavailable"};
  bool quality_available_{false};
  bool quality_authoritative_{false};
  ContactTelemetry contact_state_{};
  FinalVerdict last_final_verdict_{};
  std::vector<DeviceHealth> devices_{};
  std::vector<AlarmEvent> pending_alarms_{};
  RobotStateHub robot_state_hub_{};
  RecordingService recording_service_{};
  SafetyService safety_service_{};
  ContactGate contact_gate_{};
  ContactObserver contact_observer_{};
  NrtMotionService nrt_motion_service_{};
  RtMotionService rt_motion_service_{};
  RecoveryManager recovery_manager_{};
  RecoveryKernel recovery_kernel_{};
  RecoveryPolicy recovery_policy_{};
  ScanPlanParser scan_plan_parser_{};
  ScanPlanValidator scan_plan_validator_{};
  StateMachineGuard state_machine_guard_{};
  SdkRobotFacade sdk_robot_{};
  ModelAuthority model_authority_{};
  ForceControlLimits force_limits_{loadForceControlLimits()};
  std::set<std::string> injected_faults_{};
  std::unique_ptr<CoreRuntimeDispatcher> runtime_dispatcher_;
  std::unique_ptr<CoreRuntimeContractPublisher> runtime_contract_publisher_;
};

}  // namespace robot_core


namespace robot_core {

template <typename RequestT>
inline std::string CoreRuntime::handleTypedCommand(const RuntimeCommandContext& context, const RequestT& request) {
  RuntimeCommandInvocation invocation{};
  invocation.request_id = context.request_id;
  invocation.command = RequestT::kCommand;
  invocation.envelope_json = context.envelope_json;
  invocation.typed_request = request;
  invocation.typed_contract = findRuntimeCommandTypedContract(RequestT::kCommand);
  return replyJson(context.request_id, false, std::string("unsupported typed handler: ") + RequestT::kCommand);
}

#include "robot_core/generated_runtime_command_typed_handlers.inc"

}  // namespace robot_core
