#pragma once

#include <memory>
#include <mutex>
#include <string_view>
#include <set>
#include <string>
#include <vector>

#include "robot_core/core_runtime_kernel_components.h"
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
  std::string handleOperationalQueryCommandLocked(const RuntimeCommandInvocation& invocation);
  std::string handleMotionQueryCommandLocked(const RuntimeCommandInvocation& invocation);
  std::string handleIdentityQueryCommandLocked(const RuntimeCommandInvocation& invocation);
  std::string handleContractQueryCommandLocked(const RuntimeCommandInvocation& invocation);
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
   * @boundary Runs under ``state_store_.mutex`` and must only copy alarm payload into in-memory queues.
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
  /**
   * @brief Clear the canonical execution-plan runtime mirror.
   * @return void
   * @throws No exceptions are thrown.
   * @boundary Resets plan-owned segment/waypoint execution state and detaches planned-segment bindings from the SDK/NRT shells.
   */
  void clearExecutionPlanRuntimeLocked();
  /**
   * @brief Freeze a parsed scan plan into the canonical runtime execution graph.
   * @param plan Validated scan plan payload.
   * @param error Optional output receiving the blocking reason when freezing fails.
   * @return True when the execution runtime mirror was rebuilt successfully.
   * @throws No exceptions are thrown.
   * @boundary Builds per-segment waypoint caches and cumulative path lengths used by RT execution/progress telemetry.
   */
  bool rebuildExecutionPlanRuntimeLocked(const ScanPlan& plan, std::string* error = nullptr);
  /**
   * @brief Bind the currently active execution-plan segment into SDK/NRT execution shells.
   * @param reason Optional output receiving the blocking reason when configuration fails.
   * @return True when the active segment was configured successfully.
   * @throws No exceptions are thrown.
   * @boundary Updates segment-scoped plan ownership without mutating unrelated runtime/session state.
   */
  bool configureActiveSegmentLocked(std::string* reason = nullptr);
  /**
   * @brief Start RT scan-follow against the currently active frozen plan segment.
   * @param reason Optional output receiving the blocking reason when execution cannot start.
   * @return True when RT scan-follow entered the scanning state.
   * @throws No exceptions are thrown.
   * @boundary Owns the runtime transition from stable-contact into segment-driven RT execution.
   */
  bool startPlanDrivenScanLocked(std::string* reason = nullptr);
  /**
   * @brief Advance to the next frozen plan segment or complete the scan when exhausted.
   * @param reason Optional output receiving the blocking reason when advancement fails.
   * @return True when the next segment (or completion state) was activated successfully.
   * @throws No exceptions are thrown.
   * @boundary Maintains canonical segment ownership and completion semantics inside the runtime kernel.
   */
  bool advancePlanSegmentLocked(std::string* reason = nullptr);
  /**
   * @brief Project RT phase telemetry back onto canonical segment/waypoint progress state.
   * @param observed Current RT observation sample.
   * @param phase_telemetry Current RT phase telemetry emitted by the SDK façade.
   * @return void
   * @throws No exceptions are thrown.
   * @boundary Converts low-level RT motion progress into plan-authored segment/waypoint telemetry for UI/recorder consumers.
   */
  void updatePlanProgressLocked(const RtObservedState& observed, const RtPhaseTelemetry& phase_telemetry);
  FinalVerdict compileScanPlanVerdictLocked(const std::string& config_snapshot_json, const std::string& scan_plan_json, const std::string& scan_plan_hash = "");
  // Runtime-owned authority helpers. These methods are the final write-command
  // arbiter on the core path and must only be called with state_store_.mutex held.
  bool authorizeInvocationLocked(const RuntimeCommandInvocation& invocation, std::string* error);
  bool roleCanClaimLocked(const std::string& role, const std::string& claim) const;
  std::vector<std::string> allowedClaimsForRoleLocked(const std::string& role) const;
  std::string makeRuntimeLeaseIdLocked(const RuntimeCommandContext& context) const;
  void bindAuthoritySessionLocked(const std::string& session_id);
  void clearAuthoritySessionBindingLocked();
  std::string controlAuthorityJsonLocked() const;
  void appendMainlineContractIssuesLocked(std::vector<std::string>* blockers, std::vector<std::string>* warnings) const;
  void captureSessionFreezeInputsLocked(const LockSessionRequest& request);
  void clearSessionFreezeInputsLocked();
  void appendSessionFreezeGateIssuesLocked(std::vector<std::string>* blockers, std::vector<std::string>* warnings, bool recheck_live_state) const;
  bool sessionFreezeGateEnforcedLocked() const;
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

  RuntimeLaneScheduler lanes_{};
  RuntimeStateStore state_store_{};
  RuntimeAuthorityKernel authority_kernel_{};
  RuntimeQueryProjector query_projector_{};
  RuntimeEvidenceProjector evidence_projector_{};
  RuntimeProcedureExecutor procedure_executor_{};
  RuntimeKernelServices services_{};
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
