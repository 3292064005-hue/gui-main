#pragma once

#include <array>
#include <chrono>
#include <cstddef>
#include <map>
#include <memory>
#include <system_error>
#include <string>
#include <vector>

#ifndef ROBOT_CORE_DEFAULT_ROBOT_MODEL
#define ROBOT_CORE_DEFAULT_ROBOT_MODEL "xmate3"
#endif
#ifndef ROBOT_CORE_DEFAULT_SDK_CLASS
#define ROBOT_CORE_DEFAULT_SDK_CLASS "xMateRobot"
#endif
#ifndef ROBOT_CORE_DEFAULT_AXIS_COUNT
#define ROBOT_CORE_DEFAULT_AXIS_COUNT 6
#endif
#ifndef ROBOT_CORE_DEFAULT_CLINICAL_MAINLINE_MODE
#define ROBOT_CORE_DEFAULT_CLINICAL_MAINLINE_MODE "cartesianImpedance"
#endif

#include "robot_core/runtime_types.h"
#include "robot_core/contact_control_contract.h"
#include "robot_core/normal_axis_admittance_controller.h"
#include "robot_core/normal_force_estimator.h"
#include "robot_core/orientation_trim_controller.h"
#include "robot_core/tangential_scan_controller.h"

namespace rokae {
class xMateRobot;
template <unsigned short DoF>
class RtMotionControlCobot;
}

namespace robot_core {

struct SdkRobotRuntimeConfig {
  std::string robot_model{ROBOT_CORE_DEFAULT_ROBOT_MODEL};
  std::string sdk_robot_class{ROBOT_CORE_DEFAULT_SDK_CLASS};
  std::string preferred_link{"wired_direct"};
  bool requires_single_control_source{true};
  std::string clinical_mainline_mode{ROBOT_CORE_DEFAULT_CLINICAL_MAINLINE_MODE};
  std::string remote_ip{"192.168.0.160"};
  std::string local_ip{"192.168.0.100"};
  int axis_count{ROBOT_CORE_DEFAULT_AXIS_COUNT};
  int rt_network_tolerance_percent{15};
  double joint_filter_hz{40.0};
  double cart_filter_hz{30.0};
  double torque_filter_hz{25.0};
  double contact_seek_speed_mm_s{3.0};
  double scan_speed_mm_s{8.0};
  double retreat_speed_mm_s{20.0};
  double sample_step_mm{0.5};
  double seek_contact_max_travel_mm{8.0};
  double scan_follow_max_travel_mm{120.0};
  double retract_travel_mm{12.0};
  double scan_follow_lateral_amplitude_mm{0.5};
  double scan_follow_frequency_hz{0.25};
  double rt_stale_state_timeout_ms{40.0};
  int rt_phase_transition_debounce_cycles{5};
  double rt_max_cart_step_mm{0.25};
  double rt_max_cart_vel_mm_s{25.0};
  double rt_max_cart_acc_mm_s2{200.0};
  double rt_max_pose_trim_deg{1.5};
  double rt_max_force_error_n{8.0};
  double rt_integrator_limit_n{10.0};
  double contact_force_target_n{8.0};
  double contact_force_tolerance_n{1.0};
  int contact_establish_cycles{12};
  double normal_admittance_gain{0.00012};
  double normal_damping_gain{0.00004};
  double seek_contact_max_step_mm{0.08};
  double normal_velocity_quiet_threshold_mm_s{0.3};
  double scan_force_target_n{8.0};
  double scan_force_tolerance_n{1.0};
  double scan_normal_pi_kp{0.012};
  double scan_normal_pi_ki{0.008};
  double scan_tangent_speed_min_mm_s{2.0};
  double scan_tangent_speed_max_mm_s{12.0};
  double scan_pose_trim_gain{0.08};
  bool scan_follow_enable_lateral_modulation{true};
  double pause_hold_position_guard_mm{0.4};
  double pause_hold_force_guard_n{3.0};
  double pause_hold_drift_kp{0.010};
  double pause_hold_drift_ki{0.004};
  double pause_hold_integrator_leak{0.02};
  double retract_release_force_n{1.5};
  int retract_release_cycles{6};
  double retract_safe_gap_mm{3.0};
  double retract_max_travel_mm{15.0};
  double retract_jerk_limit_mm_s3{500.0};
  double retract_timeout_ms{1200.0};
  std::array<double, 6> cartesian_impedance{{1000.0, 1000.0, 1000.0, 80.0, 80.0, 80.0}};
  std::array<double, 6> desired_wrench_n{{0.0, 0.0, 8.0, 0.0, 0.0, 0.0}};
  std::array<double, 16> fc_frame_matrix{{1.0, 0.0, 0.0, 0.0,
                                          0.0, 1.0, 0.0, 0.0,
                                          0.0, 0.0, 1.0, 0.0,
                                          0.0, 0.0, 0.0, 1.0}};
  std::array<double, 16> tcp_frame_matrix{{1.0, 0.0, 0.0, 0.0,
                                           0.0, 1.0, 0.0, 0.0,
                                           0.0, 0.0, 1.0, 62.0,
                                           0.0, 0.0, 0.0, 1.0}};
  double load_kg{0.85};
  std::array<double, 3> load_com_mm{{0.0, 0.0, 62.0}};
  std::array<double, 6> load_inertia{{0.0012, 0.0012, 0.0008, 0.0, 0.0, 0.0}};
  std::array<double, 16> fc_frame_matrix_m{{1.0, 0.0, 0.0, 0.0,
                                            0.0, 1.0, 0.0, 0.0,
                                            0.0, 0.0, 1.0, 0.0,
                                            0.0, 0.0, 0.0, 1.0}};
  std::array<double, 16> tcp_frame_matrix_m{{1.0, 0.0, 0.0, 0.0,
                                             0.0, 1.0, 0.0, 0.0,
                                             0.0, 0.0, 1.0, 0.062,
                                             0.0, 0.0, 0.0, 1.0}};
  std::array<double, 3> load_com_m{{0.0, 0.0, 0.062}};
  std::string ui_length_unit{"mm"};
  std::string sdk_length_unit{"m"};
  bool boundary_normalized{true};
  ContactControlConfig contact_control{};
  ForceEstimatorRuntimeConfig force_estimator{};
  OrientationTrimRuntimeConfig orientation_trim{};
};

struct SdkRobotProjectInfo {
  std::string name;
  std::vector<std::string> tasks;
};

struct SdkRobotPathInfo {
  std::string name;
  double rate{0.0};
  int points{0};
};

struct SdkRobotRlStatus {
  std::string loaded_project;
  std::string loaded_task;
  bool running{false};
  double rate{1.0};
  bool loop{false};
};

struct SdkRobotDragState {
  bool enabled{false};
  std::string space{"cartesian"};
  std::string type{"admittance"};
};

struct RtObservedState {
  std::array<double, 16> tcp_pose{};
  std::array<double, 6> joint_pos{};
  std::array<double, 6> joint_vel{};
  std::array<double, 6> joint_torque{};
  std::array<double, 6> external_wrench{};
  double monotonic_time_s{0.0};
  double age_ms{0.0};
  double normal_axis_velocity_m_s{0.0};
  double pressure_force_n{0.0};
  double pressure_age_ms{0.0};
  bool pressure_valid{false};
  bool valid{false};
  bool stale{false};
};

struct RtPhaseTelemetry {
  std::string phase_name{"idle"};
  double normal_force_error_n{0.0};
  double estimated_normal_force_n{0.0};
  double normal_force_confidence{0.0};
  std::string normal_force_source{"invalid"};
  double tangent_progress_m{0.0};
  double retract_progress_m{0.0};
  double lateral_trim_m{0.0};
  double pose_trim_rad{0.0};
  double admittance_displacement_m{0.0};
  double admittance_velocity_m_s{0.0};
  bool admittance_saturated{false};
  bool orientation_trim_saturated{false};
  unsigned stable_cycles{0};
  unsigned stale_cycles{0};
};

enum class RtPhaseVerdict {
  Continue,
  PhaseCompleted,
  NeedPauseHold,
  NeedRetreat,
  NeedFaultStop,
  StaleState,
  ExceededTravel,
  ExceededForce,
  InstabilityDetected,
};

struct RtPhaseStepResult {
  std::array<double, 16> command_pose{};
  bool finished{false};
  RtPhaseVerdict verdict{RtPhaseVerdict::Continue};
  RtPhaseTelemetry telemetry{};
};

struct RtCommonControlLimits {
  double max_cart_step_mm{0.25};
  double max_cart_vel_mm_s{25.0};
  double max_cart_acc_mm_s2{200.0};
  double max_pose_trim_deg{1.5};
  double stale_state_timeout_ms{40.0};
  int phase_transition_debounce_cycles{5};
  double max_force_error_n{8.0};
  double max_integrator_n{10.0};
};

struct SeekContactControlContract {
  double force_target_n{8.0};
  double force_tolerance_n{1.0};
  int establish_cycles{12};
  double admittance_gain{0.00012};
  double damping_gain{0.00004};
  double max_step_mm{0.08};
  double max_travel_mm{8.0};
  double quiet_velocity_mm_s{0.3};
};

struct ScanFollowControlContract {
  double force_target_n{8.0};
  double force_tolerance_n{1.0};
  double normal_pi_kp{0.012};
  double normal_pi_ki{0.008};
  double tangent_speed_min_mm_s{2.0};
  double tangent_speed_max_mm_s{12.0};
  double pose_trim_gain{0.08};
  bool enable_lateral_modulation{true};
  double max_travel_mm{120.0};
  double lateral_amplitude_mm{0.5};
  double modulation_frequency_hz{0.25};
};

struct PauseHoldControlContract {
  double position_guard_mm{0.4};
  double force_guard_n{3.0};
  double drift_kp{0.010};
  double drift_ki{0.004};
  double integrator_leak{0.02};
};

struct ControlledRetractControlContract {
  double release_force_n{1.5};
  int release_cycles{6};
  double safe_gap_mm{3.0};
  double max_travel_mm{15.0};
  double jerk_limit_mm_s3{500.0};
  double timeout_ms{1200.0};
  double retract_travel_mm{12.0};
};

struct RtPhaseControlContract {
  RtCommonControlLimits common{};
  SeekContactControlContract seek_contact{};
  ScanFollowControlContract scan_follow{};
  PauseHoldControlContract pause_hold{};
  ControlledRetractControlContract controlled_retract{};
};


class SdkRobotFacade;

class SdkRobotLifecyclePort {
public:
  explicit SdkRobotLifecyclePort(SdkRobotFacade& owner);
  bool connect(const std::string& remote_ip, const std::string& local_ip);
  void disconnect();
  bool setPower(bool on);
  bool setAutoMode();
  bool setManualMode();
  bool ensureConnected(std::string* reason = nullptr);
  bool ensurePoweredAuto(std::string* reason = nullptr);
  bool ensureNrtMode(std::string* reason = nullptr);
private:
  SdkRobotFacade& owner_;
};

class SdkRobotQueryPort {
public:
  explicit SdkRobotQueryPort(SdkRobotFacade& owner);
  SdkRobotRuntimeConfig runtimeConfig() const;
  std::vector<std::string> controllerLogs() const;
  std::vector<SdkRobotProjectInfo> rlProjects() const;
  SdkRobotRlStatus rlStatus() const;
  std::vector<SdkRobotPathInfo> pathLibrary() const;
  SdkRobotDragState dragState() const;
  std::map<std::string, bool> di() const;
  std::map<std::string, bool> doState() const;
  std::map<std::string, double> ai() const;
  std::map<std::string, double> ao() const;
  std::map<std::string, int> registers() const;
  std::string runtimeSource() const;
  bool sdkAvailable() const;
  bool xmateModelAvailable() const;
  bool controlSourceExclusive() const;
  bool networkHealthy() const;
  bool motionChannelReady() const;
  bool stateChannelReady() const;
  bool auxChannelReady() const;
  int nominalRtLoopHz() const;
  std::string activeRtPhase() const;
  std::string activeNrtProfile() const;
  int commandSequence() const;
  std::string sdkBindingMode() const;
  std::string hardwareLifecycleState() const;
  bool liveBindingEstablished() const;
  RtPhaseTelemetry phaseTelemetry() const;
  bool liveTakeoverReady() const;
private:
  SdkRobotFacade& owner_;
};

class SdkRobotNrtExecutionPort {
public:
  explicit SdkRobotNrtExecutionPort(SdkRobotFacade& owner);
  bool executeMoveAbsJ(const std::vector<double>& joints_rad, int speed_mm_s, int zone_mm, std::string* reason = nullptr);
  bool executeMoveL(const std::vector<double>& tcp_xyzabc_m_rad, int speed_mm_s, int zone_mm, std::string* reason = nullptr);
  bool stop(std::string* reason = nullptr);
  bool beginProfile(const std::string& profile, const std::string& sdk_command, bool requires_auto_mode, std::string* reason = nullptr);
  void finishProfile(const std::string& profile, bool success, const std::string& detail = "");
private:
  SdkRobotFacade& owner_;
};

class SdkRobotRtControlPort {
public:
  explicit SdkRobotRtControlPort(SdkRobotFacade& owner);
  bool configureMainline(const SdkRobotRuntimeConfig& config);
  bool ensureRtMode(std::string* reason = nullptr);
  bool ensureController(std::string* reason = nullptr);
  bool ensureStateStream(const std::vector<std::string>& fields, std::string* reason = nullptr);
  bool applyConfig(const SdkRobotRuntimeConfig& config, std::string* reason = nullptr);
  bool stop(std::string* reason = nullptr);
  bool beginMainline(const std::string& phase, int nominal_loop_hz, std::string* reason = nullptr);
  void updatePhase(const std::string& phase, const std::string& detail = "");
  void finishMainline(const std::string& phase, const std::string& detail = "");
  bool populateObservedState(RtObservedState& out, std::string* reason = nullptr);
  RtPhaseStepResult stepSeekContact(const RtObservedState& state);
  RtPhaseStepResult stepScanFollow(const RtObservedState& state);
  RtPhaseStepResult stepPauseHold(const RtObservedState& state);
  RtPhaseStepResult stepControlledRetract(const RtObservedState& state);
  void resetPhaseIntegrators();
  bool validateContract(std::string* reason = nullptr) const;
  void setControlContract(const RtPhaseControlContract& contract);
  SdkRobotRuntimeConfig runtimeConfig() const;
  std::string activeRtPhase() const;
  bool networkHealthy() const;
  int nominalRtLoopHz() const;
  bool liveBindingEstablished() const;
  RtPhaseTelemetry phaseTelemetry() const;
private:
  SdkRobotFacade& owner_;
};

class SdkRobotCollaborationPort {
public:
  explicit SdkRobotCollaborationPort(SdkRobotFacade& owner);
  bool runRlProject(const std::string& project, const std::string& task, std::string* reason = nullptr);
  bool pauseRlProject(std::string* reason = nullptr);
  bool enableDrag(const std::string& space, const std::string& type, std::string* reason = nullptr);
  bool disableDrag(std::string* reason = nullptr);
  bool replayPath(const std::string& name, double rate, std::string* reason = nullptr);
  bool startRecordPath(int duration_s, std::string* reason = nullptr);
  bool stopRecordPath(std::string* reason = nullptr);
  bool cancelRecordPath(std::string* reason = nullptr);
  bool saveRecordPath(const std::string& name, const std::string& save_as, std::string* reason = nullptr);
  void setRlStatus(const std::string& project, const std::string& task, bool running);
  void setDragState(bool enabled, const std::string& space, const std::string& type);
private:
  SdkRobotFacade& owner_;
};

/**
 * @brief xMateRobot-only official SDK façade.
 *
 * This façade keeps every official SDK touchpoint inside cpp_robot_core while
 * preserving the historical public API already consumed by the runtime and the
 * Python bridge. The implementation therefore exposes two layers of truth:
 *
 * 1. vendor SDK availability and live-binding status,
 * 2. higher-level runtime state used by existing callers.
 *
 * When hardware or network prerequisites are unavailable, the façade reports a
 * truthful degraded state instead of overstating device authority.
 */
using LifecyclePort = SdkRobotLifecyclePort;
using QueryPort = SdkRobotQueryPort;
using NrtExecutionPort = SdkRobotNrtExecutionPort;
using RtControlPort = SdkRobotRtControlPort;
using CollaborationPort = SdkRobotCollaborationPort;

class SdkRobotFacade {
public:

  SdkRobotFacade();
  ~SdkRobotFacade();

  LifecyclePort& lifecyclePort();
  const LifecyclePort& lifecyclePort() const;
  QueryPort& queryPort();
  const QueryPort& queryPort() const;
  NrtExecutionPort& nrtExecutionPort();
  const NrtExecutionPort& nrtExecutionPort() const;
  RtControlPort& rtControlPort();
  const RtControlPort& rtControlPort() const;
  CollaborationPort& collaborationPort();
  const CollaborationPort& collaborationPort() const;


  /**
   * @brief Connect the xMateRobot live binding.
   * @param remote_ip Controller IP address.
   * @param local_ip Host NIC IP address used for RT traffic.
   * @return True when a live SDK binding is established, or when the binary is
   *         intentionally built without the vendor SDK and therefore exposes an
   *         explicit contract-only shell. False is returned when a vendored SDK
   *         build fails to establish the live binding.
   * @throws No exceptions are propagated to callers; SDK exceptions are caught and logged.
   * @boundary Empty addresses or rejected SDK construction block the connection.
   */
  bool connect(const std::string& remote_ip, const std::string& local_ip);
  void disconnect();
  bool setPower(bool on);
  bool setAutoMode();
  bool setManualMode();
  bool configureRtMainline(const SdkRobotRuntimeConfig& config);

  bool ensureConnected(std::string* reason = nullptr);
  bool ensurePoweredAuto(std::string* reason = nullptr);
  bool ensureNrtMode(std::string* reason = nullptr);
  bool ensureRtMode(std::string* reason = nullptr);
  bool ensureRtController(std::string* reason = nullptr);
  bool ensureRtStateStream(const std::vector<std::string>& fields, std::string* reason = nullptr);
  bool applyRtConfig(const SdkRobotRuntimeConfig& config, std::string* reason = nullptr);
  bool executeMoveAbsJ(const std::vector<double>& joints_rad, int speed_mm_s, int zone_mm, std::string* reason = nullptr);
  bool executeMoveL(const std::vector<double>& tcp_xyzabc_m_rad, int speed_mm_s, int zone_mm, std::string* reason = nullptr);
  bool stopNrt(std::string* reason = nullptr);
  bool stopRt(std::string* reason = nullptr);
  bool runRlProject(const std::string& project, const std::string& task, std::string* reason = nullptr);
  bool pauseRlProject(std::string* reason = nullptr);
  bool enableDrag(const std::string& space, const std::string& type, std::string* reason = nullptr);
  bool disableDrag(std::string* reason = nullptr);
  bool replayPath(const std::string& name, double rate, std::string* reason = nullptr);
  bool startRecordPath(int duration_s, std::string* reason = nullptr);
  bool stopRecordPath(std::string* reason = nullptr);
  bool cancelRecordPath(std::string* reason = nullptr);
  bool saveRecordPath(const std::string& name, const std::string& save_as, std::string* reason = nullptr);

  struct AuthoritativeKinematicsCheckResult {
    bool available{false};
    bool passed{true};
    std::string reason;
    std::vector<std::string> warnings;
  };

  /**
   * @brief Run authoritative xMateModel feasibility checks for a frozen scan plan.
   * @param plan Canonical scan plan to validate.
   * @return Availability/result bundle for the model-backed feasibility pass.
   * @throws No exceptions are propagated to callers; SDK/model failures are captured in the result.
   * @boundary Uses official xCore SDK model methods only when a live xMate binding is established.
   */
  AuthoritativeKinematicsCheckResult validatePlanAuthoritativeKinematics(const ScanPlan& plan) const;

  bool connected() const;
  bool powered() const;
  bool automaticMode() const;
  bool sdkAvailable() const;
  bool xmateModelAvailable() const;
  bool rtMainlineConfigured() const;
  bool motionChannelReady() const;
  bool stateChannelReady() const;
  bool auxChannelReady() const;
  bool networkHealthy() const;
  bool controlSourceExclusive() const;
  int nominalRtLoopHz() const;
  std::string activeRtPhase() const;
  std::string activeNrtProfile() const;
  int commandSequence() const;
  std::string sdkBindingMode() const;
  std::string hardwareLifecycleState() const;
  std::string runtimeSource() const;
  bool liveBindingEstablished() const;
  RtPhaseTelemetry phaseTelemetry() const;
  bool liveTakeoverReady() const;
  SdkRobotRuntimeConfig runtimeConfig() const;
  std::vector<double> jointPos() const;
  std::vector<double> jointVel() const;
  std::vector<double> jointTorque() const;
  std::vector<double> tcpPose() const;
  std::vector<std::string> configurationLog() const;
  std::vector<std::string> controllerLogs() const;
  std::vector<SdkRobotProjectInfo> rlProjects() const;
  SdkRobotRlStatus rlStatus() const;
  std::vector<SdkRobotPathInfo> pathLibrary() const;
  SdkRobotDragState dragState() const;
  std::map<std::string, bool> di() const;
  std::map<std::string, bool> doState() const;
  std::map<std::string, double> ai() const;
  std::map<std::string, double> ao() const;
  std::map<std::string, int> registers() const;
  void updateSessionRegisters(int active_segment, int frame_id);
  void setRlStatus(const std::string& project, const std::string& task, bool running);
  void setDragState(bool enabled, const std::string& space, const std::string& type);
  void setControlSourceExclusive(bool exclusive);
  void setNetworkHealthy(bool healthy);
  bool beginNrtProfile(const std::string& profile, const std::string& sdk_command, bool requires_auto_mode, std::string* reason = nullptr);
  void finishNrtProfile(const std::string& profile, bool success, const std::string& detail = "");
  bool beginRtMainline(const std::string& phase, int nominal_loop_hz, std::string* reason = nullptr);
  void updateRtPhase(const std::string& phase, const std::string& detail = "");
  void finishRtMainline(const std::string& phase, const std::string& detail = "");
  bool populateObservedState(RtObservedState& out, std::string* reason = nullptr);
  RtPhaseStepResult stepSeekContact(const RtObservedState& state);
  RtPhaseStepResult stepScanFollow(const RtObservedState& state);
  RtPhaseStepResult stepPauseHold(const RtObservedState& state);
  RtPhaseStepResult stepControlledRetract(const RtObservedState& state);
  void resetRtPhaseIntegrators();
  bool validateRtControlContract(std::string* reason = nullptr) const;
  void setRtPhaseControlContract(const RtPhaseControlContract& contract);
  /**
   * @brief Bind a plan-authored scan segment into the SDK façade RT/NRT execution cache.
   * @param segment Canonical frozen scan segment.
   * @return void
   * @throws No exceptions are thrown.
   * @boundary Exposes plan-driven waypoint geometry to RT scan-follow without letting UI/Python own execution state.
   */
  void setPlannedSegment(const ScanSegment& segment);
  /**
   * @brief Clear the currently bound planned segment from the SDK façade cache.
   * @return void
   * @throws No exceptions are thrown.
   * @boundary Removes plan-driven RT/NRT geometry when no active execution segment is owned by runtime.
   */
  void clearPlannedSegment();
  /**
   * @brief Return the id of the currently bound planned segment.
   * @return Planned segment id or zero when no segment is bound.
   * @throws No exceptions are thrown.
   */
  int plannedSegmentId() const;
  /**
   * @brief Return the waypoint count of the currently bound planned segment.
   * @return Number of plan-authored waypoints cached inside the façade.
   * @throws No exceptions are thrown.
   */
  std::size_t plannedWaypointCount() const;


  static std::vector<double> zeroVector(std::size_t count);
  static std::array<double, 16> defaultPoseMatrix();
  double measuredNormalForce(const RtObservedState& state) const;
  void configureContactControllersFromRuntimeConfig();
  double measuredNormalVelocity(const RtObservedState& state) const;
  void clampCommandPose(std::array<double, 16>& pose, const std::array<double, 16>& anchor);
  void clampPoseTrim(std::array<double, 16>& pose, const std::array<double, 16>& anchor) const;
  void applyLocalPitchTrim(std::array<double, 16>& pose, const std::array<double, 16>& anchor, double trim_rad) const;
  void appendLog(const std::string& message);
  void refreshStateVectors(std::size_t axis_count);
  void refreshInventoryForAxisCount(std::size_t axis_count);
  void refreshBindingTruth();
  void refreshRuntimeCaches();
  void refreshRlProjects();
  void refreshPathLibrary();
  void refreshIoSnapshots();
  void setRtPhaseCode(const std::string& phase);
  /**
   * @brief Enforce that a hardware-mutating SDK call has a live binding.
   * @param prefix Human-readable operation label written into controller logs on failure.
   * @param reason Optional output string receiving the blocking reason.
   * @return True only when the façade currently owns an authoritative live binding.
   * @throws No exceptions are thrown. Failure is reported through controller logs and the optional reason output.
   * @boundary Prevents contract-shell/local-cache state mutation from masquerading as a real controller-side write.
   */
  bool requireLiveWrite(const std::string& prefix, std::string* reason = nullptr);
  void finalizeNrtStopLocal(const std::string& detail = "");
  void finalizeRtStopLocal(const std::string& detail = "");
  bool beginRtMainlineInternal(const std::string& phase, int nominal_loop_hz, std::string* reason = nullptr);
  void updateRtPhaseInternal(const std::string& phase, const std::string& detail = "");
  void finishRtMainlineInternal(const std::string& phase, const std::string& detail = "");
  bool applyErrorCode(const std::string& prefix, const std::error_code& ec, std::string* reason = nullptr);
  void captureException(const std::string& prefix, const std::exception& ex, std::string* reason = nullptr);
  void captureFailure(const std::string& prefix, const std::string& detail, std::string* reason = nullptr);

  struct LocalStateStore {
    bool powered{false};
  };

  bool connected_{false};
  LocalStateStore state_store_{};
  bool auto_mode_{false};
  bool rt_mainline_configured_{false};
  bool motion_channel_ready_{false};
  bool state_channel_ready_{false};
  bool aux_channel_ready_{false};
  bool network_healthy_{true};
  bool control_source_exclusive_{true};
  bool vendored_sdk_detected_{false};
  bool live_binding_established_{false};
  bool rt_state_stream_started_{false};
  bool rt_loop_active_{false};
  int nominal_rt_loop_hz_{1000};
  int command_sequence_{0};
  std::string active_rt_phase_{"idle"};
  std::string active_nrt_profile_{"idle"};
  std::string backend_kind_{"contract_sim"};
  std::string binding_detail_{"boot"};
  std::vector<std::string> rt_state_fields_{};
  SdkRobotRuntimeConfig rt_config_{};
  RtPhaseControlContract rt_phase_contract_{};
  ContactControlContract contact_control_contract_{};
  struct RtPhaseLoopStateInternal {
    std::array<double, 16> anchor_pose{};
    std::array<double, 16> hold_reference_pose{};
    bool anchor_initialized{false};
    bool hold_reference_initialized{false};
    std::size_t cycle_count{0};
    std::size_t contact_axis_index{11};
    std::size_t scan_axis_index{3};
    std::size_t lateral_axis_index{7};
    double contact_direction_sign{1.0};
    double seek_progress_m{0.0};
    double scan_progress_m{0.0};
    double retract_progress_m{0.0};
    double retract_safe_gap_progress_m{0.0};
    double normal_integrator{0.0};
    double hold_integrator{0.0};
    double last_normal_error_n{0.0};
    unsigned stable_cycles{0};
    unsigned stale_cycles{0};
    unsigned release_cycles{0};
    bool retract_released{false};
    double phase_time_s{0.0};
    double last_command_step_m{0.0};
    double retract_velocity_mm_s{0.0};
    double retract_accel_mm_s2{0.0};
    RtPhaseVerdict pending_transition_verdict{RtPhaseVerdict::Continue};
    unsigned pending_transition_cycles{0};
  } rt_phase_loop_state_{};
  NormalForceEstimator normal_force_estimator_{};
  NormalAxisAdmittanceController normal_admittance_controller_{};
  TangentialScanController tangential_scan_controller_{};
  OrientationTrimController orientation_trim_controller_{};
  struct PlannedSegmentRuntime {
    bool configured{false};
    int segment_id{0};
    std::vector<ScanWaypoint> waypoints;
    std::vector<double> cumulative_lengths_m;
    double total_length_m{0.0};
    std::string transition_policy{"serpentine"};
    double target_force_n{0.0};
  } planned_segment_{};
  RtPhaseTelemetry last_phase_telemetry_{};
  std::vector<double> joint_pos_;
  std::vector<double> joint_vel_;
  std::vector<double> joint_torque_;
  std::vector<double> tcp_pose_;
  std::array<double, 16> last_rt_observed_pose_{};
  bool last_rt_observed_pose_initialized_{false};
  double last_rt_observed_time_s_{0.0};
  double last_rt_state_sample_time_s_{0.0};
  std::vector<std::string> configuration_log_;
  std::vector<std::string> controller_logs_;
  std::vector<SdkRobotProjectInfo> rl_projects_;
  SdkRobotRlStatus rl_status_{};
  std::vector<SdkRobotPathInfo> path_library_;
  SdkRobotDragState drag_state_{};
  std::map<std::string, bool> di_;
  std::map<std::string, bool> do_;
  std::map<std::string, double> ai_;
  std::map<std::string, double> ao_;
  std::map<std::string, int> registers_;
  std::shared_ptr<rokae::xMateRobot> robot_;
  std::shared_ptr<rokae::RtMotionControlCobot<6>> rt_controller_;
  std::unique_ptr<SdkRobotLifecyclePort> lifecycle_port_;
  std::unique_ptr<SdkRobotQueryPort> query_port_;
  std::unique_ptr<SdkRobotNrtExecutionPort> nrt_execution_port_;
  std::unique_ptr<SdkRobotRtControlPort> rt_control_port_;
  std::unique_ptr<SdkRobotCollaborationPort> collaboration_port_;
};

}  // namespace robot_core
