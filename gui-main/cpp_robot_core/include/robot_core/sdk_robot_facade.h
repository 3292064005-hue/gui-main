#pragma once

#include <array>
#include <cstddef>
#include <map>
#include <string>
#include <vector>

namespace robot_core {

struct SdkRobotRuntimeConfig {
  std::string robot_model{"xmate3"};
  std::string sdk_robot_class{"xMateRobot"};
  std::string preferred_link{"wired_direct"};
  bool requires_single_control_source{true};
  std::string clinical_mainline_mode{"cartesianImpedance"};
  std::string remote_ip{"192.168.0.160"};
  std::string local_ip{"192.168.0.100"};
  int axis_count{6};
  int rt_network_tolerance_percent{15};
  double joint_filter_hz{40.0};
  double cart_filter_hz{30.0};
  double torque_filter_hz{25.0};
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

/**
 * @brief Runtime-owned façade for the vendored xCore SDK boundary.
 *
 * The façade preserves the historical public API exposed to the rest of the
 * repository while separating three concerns in its reported state:
 * 1. vendored SDK detection,
 * 2. contract-shell readiness, and
 * 3. live binding establishment.
 *
 * The current repository build can truthfully report contract-shell readiness
 * without over-claiming that a live SDK takeover has been established.
 */
class SdkRobotFacade {
public:
  SdkRobotFacade();
  ~SdkRobotFacade();

  /**
   * @brief Connect the runtime-facing robot façade.
   * @param remote_ip Robot/controller IP.
   * @param local_ip Host interface IP.
   * @return True when the façade can expose a connected contract surface.
   * @throws No exceptions are thrown.
   * @boundary Empty addresses block the connection attempt.
   */
  bool connect(const std::string& remote_ip, const std::string& local_ip);
  void disconnect();
  bool setPower(bool on);
  bool setAutoMode();
  bool setManualMode();
  bool configureRtMainline(const SdkRobotRuntimeConfig& config);
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
  /**
   * @brief Report whether a real SDK/device binding has been established.
   * @return True only when the runtime has evidence of live SDK takeover.
   * @throws No exceptions are thrown.
   * @boundary Vendored SDK discovery alone is insufficient for this method to
   *     return true.
   */
  bool liveBindingEstablished() const;
  /**
   * @brief Report whether the runtime is ready to claim live takeover.
   * @return True when the binding is established and the control path is
   *     configured for live execution.
   * @throws No exceptions are thrown.
   * @boundary Returns false for contract-shell builds to avoid overstating
   *     hardware authority.
   */
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

private:
  static std::vector<double> zeroVector(std::size_t count);
  void appendLog(const std::string& message);
  void refreshStateVectors(std::size_t axis_count);
  void refreshInventoryForAxisCount(std::size_t axis_count);
  void refreshBindingTruth();
  void setRtPhaseCode(const std::string& phase);

  bool connected_{false};
  bool powered_{false};
  bool auto_mode_{false};
  bool rt_mainline_configured_{false};
  bool motion_channel_ready_{false};
  bool state_channel_ready_{false};
  bool aux_channel_ready_{false};
  bool network_healthy_{true};
  bool control_source_exclusive_{true};
  bool vendored_sdk_detected_{false};
  bool live_binding_established_{false};
  int nominal_rt_loop_hz_{1000};
  int command_sequence_{0};
  std::string active_rt_phase_{"idle"};
  std::string active_nrt_profile_{"idle"};
  std::string backend_kind_{"contract_sim"};
  std::string binding_detail_{"boot"};
  SdkRobotRuntimeConfig rt_config_{};
  std::vector<double> joint_pos_;
  std::vector<double> joint_vel_;
  std::vector<double> joint_torque_;
  std::vector<double> tcp_pose_;
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
};

}  // namespace robot_core
