#include "robot_core/sdk_robot_facade.h"

namespace robot_core {

bool SdkRobotFacade::connected() const { return connected_; }
bool SdkRobotFacade::powered() const { return powered_; }
bool SdkRobotFacade::automaticMode() const { return auto_mode_; }
bool SdkRobotFacade::rtMainlineConfigured() const { return rt_mainline_configured_; }
bool SdkRobotFacade::motionChannelReady() const { return motion_channel_ready_; }
bool SdkRobotFacade::stateChannelReady() const { return state_channel_ready_; }
bool SdkRobotFacade::auxChannelReady() const { return aux_channel_ready_; }
bool SdkRobotFacade::networkHealthy() const { return network_healthy_; }
bool SdkRobotFacade::controlSourceExclusive() const { return control_source_exclusive_; }
int SdkRobotFacade::nominalRtLoopHz() const { return nominal_rt_loop_hz_; }
std::string SdkRobotFacade::activeRtPhase() const { return active_rt_phase_; }
std::string SdkRobotFacade::activeNrtProfile() const { return active_nrt_profile_; }
int SdkRobotFacade::commandSequence() const { return command_sequence_; }
bool SdkRobotFacade::liveBindingEstablished() const { return live_binding_established_; }

bool SdkRobotFacade::liveTakeoverReady() const {
  return vendored_sdk_detected_ && live_binding_established_ && control_source_exclusive_ && connected_ && powered_ && auto_mode_ && rt_mainline_configured_;
}

std::string SdkRobotFacade::sdkBindingMode() const {
  if (liveTakeoverReady()) {
    return "live_takeover_ready";
  }
  if (vendored_sdk_detected_) {
    return control_source_exclusive_ ? "vendored_sdk_contract_shell" : "vendored_sdk_nonexclusive";
  }
  return "contract_only";
}

std::string SdkRobotFacade::hardwareLifecycleState() const {
  if (!connected_) return "disconnected";
  if (!network_healthy_) return "network_degraded";
  if (!powered_) return "connected";
  if (!auto_mode_) return "powered";
  if (!rt_mainline_configured_) return "auto_ready";
  if (active_rt_phase_ != "idle") return live_binding_established_ ? "rt_active" : "rt_contract_active";
  if (active_nrt_profile_ != "idle") return live_binding_established_ ? "nrt_active" : "nrt_contract_active";
  return liveTakeoverReady() ? "rt_ready" : "contract_shell_ready";
}

bool SdkRobotFacade::sdkAvailable() const {
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  return true;
#else
  return false;
#endif
}

bool SdkRobotFacade::xmateModelAvailable() const {
#ifdef ROBOT_CORE_WITH_XMATE_MODEL
  return true;
#else
  return false;
#endif
}

std::string SdkRobotFacade::runtimeSource() const {
  if (liveTakeoverReady()) {
    return xmateModelAvailable() ? "xcore_sdk_live_takeover+xmatemodel" : "xcore_sdk_live_takeover";
  }
  if (vendored_sdk_detected_ && xmateModelAvailable()) {
    return "xcore_sdk_contract_shell+xmatemodel";
  }
  if (vendored_sdk_detected_) {
    return "xcore_sdk_contract_shell";
  }
  return "simulated_contract";
}

SdkRobotRuntimeConfig SdkRobotFacade::runtimeConfig() const { return rt_config_; }

std::vector<double> SdkRobotFacade::jointPos() const { return joint_pos_; }
std::vector<double> SdkRobotFacade::jointVel() const { return joint_vel_; }
std::vector<double> SdkRobotFacade::jointTorque() const { return joint_torque_; }
std::vector<double> SdkRobotFacade::tcpPose() const { return tcp_pose_; }
std::vector<std::string> SdkRobotFacade::configurationLog() const { return configuration_log_; }
std::vector<std::string> SdkRobotFacade::controllerLogs() const { return controller_logs_; }
std::vector<SdkRobotProjectInfo> SdkRobotFacade::rlProjects() const { return rl_projects_; }
SdkRobotRlStatus SdkRobotFacade::rlStatus() const { return rl_status_; }
std::vector<SdkRobotPathInfo> SdkRobotFacade::pathLibrary() const { return path_library_; }
SdkRobotDragState SdkRobotFacade::dragState() const { return drag_state_; }
std::map<std::string, bool> SdkRobotFacade::di() const { return di_; }
std::map<std::string, bool> SdkRobotFacade::doState() const { return do_; }
std::map<std::string, double> SdkRobotFacade::ai() const { return ai_; }
std::map<std::string, double> SdkRobotFacade::ao() const { return ao_; }
std::map<std::string, int> SdkRobotFacade::registers() const { return registers_; }

void SdkRobotFacade::updateSessionRegisters(int active_segment, int frame_id) {
  registers_["spine.session.segment"] = active_segment;
  registers_["spine.session.frame"] = frame_id;
}

void SdkRobotFacade::setRlStatus(const std::string& project, const std::string& task, bool running) {
  rl_status_.loaded_project = project;
  rl_status_.loaded_task = task;
  rl_status_.running = running;
  appendLog(std::string("rl_status(project=") + project + ",task=" + task + ",running=" + (running ? "true" : "false") + ")");
}

void SdkRobotFacade::setDragState(bool enabled, const std::string& space, const std::string& type) {
  drag_state_.enabled = enabled;
  drag_state_.space = space;
  drag_state_.type = type;
  appendLog(std::string("drag_state(enabled=") + (enabled ? "true" : "false") + ",space=" + space + ",type=" + type + ")");
}

void SdkRobotFacade::setControlSourceExclusive(bool exclusive) {
  control_source_exclusive_ = exclusive;
  refreshBindingTruth();
  appendLog(std::string("control_source_exclusive=") + (exclusive ? "true" : "false"));
}

void SdkRobotFacade::setNetworkHealthy(bool healthy) {
  network_healthy_ = healthy;
  motion_channel_ready_ = connected_ && powered_ && healthy;
  state_channel_ready_ = connected_ && healthy;
  refreshBindingTruth();
  appendLog(std::string("network_health=") + (healthy ? "healthy" : "degraded"));
}

}  // namespace robot_core
