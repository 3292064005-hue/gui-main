#include "robot_core/sdk_robot_facade.h"

#ifdef ROBOT_CORE_WITH_XCORE_SDK
#include "rokae/robot.h"
#endif

#include <algorithm>
#include <cmath>
#include <sstream>

namespace robot_core {

namespace {

constexpr std::size_t kTranslationIndices[3] = {3, 7, 11};

bool looksLikeMillimetres(double value) {
  return std::abs(value) > 2.0;
}

double mmToM(double value_mm) {
  return value_mm / 1000.0;
}

std::array<double, 16> normalizeFrameMatrixMmToM(const std::array<double, 16>& matrix) {
  auto normalized = matrix;
  for (const auto idx : kTranslationIndices) {
    if (looksLikeMillimetres(normalized[idx])) {
      normalized[idx] = mmToM(normalized[idx]);
    }
  }
  return normalized;
}

std::array<double, 3> normalizeLoadComMmToM(const std::array<double, 3>& values) {
  return {mmToM(values[0]), mmToM(values[1]), mmToM(values[2])};
}

}  // namespace

SdkRobotFacade::SdkRobotFacade() {
  vendored_sdk_detected_ = sdkAvailable();
  backend_kind_ = vendored_sdk_detected_ ? "vendored_sdk_contract_shell" : "contract_sim";
  binding_detail_ = vendored_sdk_detected_ ? "vendored_sdk_detected_contract_shell_only" : "no_vendored_sdk_detected";
  refreshStateVectors(6);
  refreshInventoryForAxisCount(6);
  tcp_pose_ = {0.0, 0.0, 240.0, 180.0, 0.0, 90.0};
  rl_projects_ = {{"spine_mainline", {"scan", "prep", "retreat"}}, {"spine_research", {"sweep", "contact_probe"}}};
  di_ = {{"board0_port0", false}, {"board0_port1", true}};
  do_ = {{"board0_port0", false}, {"board0_port1", false}};
  ai_ = {{"board0_port0", 0.12}};
  ao_ = {{"board0_port0", 0.0}};
  registers_ = {{"spine.session.segment", 0}, {"spine.session.frame", 0}, {"spine.rt.phase_code", 0}, {"spine.command.sequence", 0}};
  refreshBindingTruth();
  appendLog(std::string("sdk facade booted source=") + runtimeSource());
}

SdkRobotFacade::~SdkRobotFacade() = default;

bool SdkRobotFacade::connect(const std::string& remote_ip, const std::string& local_ip) {
  connected_ = !remote_ip.empty() && !local_ip.empty();
  rt_config_.remote_ip = remote_ip;
  rt_config_.local_ip = local_ip;
  network_healthy_ = connected_;
  control_source_exclusive_ = rt_config_.requires_single_control_source;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  // All official SDK ownership stays inside this façade. Higher layers are not
  // allowed to bypass the contract shell even when the vendored SDK is present.
#endif
  state_channel_ready_ = connected_;
  aux_channel_ready_ = connected_;
  motion_channel_ready_ = connected_ && powered_;
  active_rt_phase_ = "idle";
  active_nrt_profile_ = "idle";
  binding_detail_ = connected_ ? "contract_shell_connected" : "connect_blocked_invalid_endpoint";
  refreshBindingTruth();
  appendLog("connectToRobot(" + remote_ip + "," + local_ip + ")");
  return connected_;
}

void SdkRobotFacade::disconnect() {
  connected_ = false;
  powered_ = false;
  auto_mode_ = false;
  rt_mainline_configured_ = false;
  motion_channel_ready_ = false;
  state_channel_ready_ = false;
  aux_channel_ready_ = false;
  network_healthy_ = false;
  live_binding_established_ = false;
  nominal_rt_loop_hz_ = 1000;
  active_rt_phase_ = "idle";
  active_nrt_profile_ = "idle";
  rl_status_ = {};
  drag_state_ = {};
  refreshStateVectors(static_cast<std::size_t>(std::max(1, rt_config_.axis_count)));
  refreshInventoryForAxisCount(static_cast<std::size_t>(std::max(1, rt_config_.axis_count)));
  tcp_pose_ = {0.0, 0.0, 240.0, 180.0, 0.0, 90.0};
  updateSessionRegisters(0, 0);
  binding_detail_ = "disconnected";
  refreshBindingTruth();
  appendLog("disconnectFromRobot()");
}

bool SdkRobotFacade::setPower(bool on) {
  if (!connected_) {
    appendLog("setPowerState blocked: controller_not_connected");
    return false;
  }
  powered_ = on;
  motion_channel_ready_ = connected_ && powered_ && network_healthy_;
  binding_detail_ = on ? "contract_shell_powered" : "contract_shell_unpowered";
  refreshBindingTruth();
  appendLog(std::string("setPowerState(") + (on ? "on" : "off") + ")");
  return true;
}

bool SdkRobotFacade::setAutoMode() {
  if (!connected_) {
    appendLog("setOperateMode(auto) blocked: controller_not_connected");
    return false;
  }
  auto_mode_ = true;
  binding_detail_ = "contract_shell_auto_mode";
  refreshBindingTruth();
  appendLog("setOperateMode(auto)");
  return true;
}

bool SdkRobotFacade::setManualMode() {
  if (!connected_) {
    appendLog("setOperateMode(manual) blocked: controller_not_connected");
    return false;
  }
  auto_mode_ = false;
  active_rt_phase_ = "idle";
  live_binding_established_ = false;
  binding_detail_ = "contract_shell_manual_mode";
  refreshBindingTruth();
  appendLog("setOperateMode(manual)");
  return true;
}

bool SdkRobotFacade::configureRtMainline(const SdkRobotRuntimeConfig& config) {
  if (!connected_ || !powered_ || !auto_mode_) {
    binding_detail_ = "configure_rt_blocked_lifecycle_not_ready";
    refreshBindingTruth();
    appendLog("configureRtMainline blocked: lifecycle_not_ready");
    return false;
  }
  rt_config_ = config;
  rt_config_.fc_frame_matrix_m = normalizeFrameMatrixMmToM(config.fc_frame_matrix);
  rt_config_.tcp_frame_matrix_m = normalizeFrameMatrixMmToM(config.tcp_frame_matrix);
  rt_config_.load_com_m = normalizeLoadComMmToM(config.load_com_mm);
  rt_config_.ui_length_unit = "mm";
  rt_config_.sdk_length_unit = "m";
  rt_config_.boundary_normalized = true;
  control_source_exclusive_ = rt_config_.requires_single_control_source;
  nominal_rt_loop_hz_ = 1000;
  rt_mainline_configured_ = control_source_exclusive_ && network_healthy_ && config.axis_count >= 6;
  motion_channel_ready_ = connected_ && powered_ && network_healthy_;
  state_channel_ready_ = connected_ && network_healthy_;
  aux_channel_ready_ = connected_;
  live_binding_established_ = false;

  refreshStateVectors(static_cast<std::size_t>(std::max(1, config.axis_count)));
  refreshInventoryForAxisCount(static_cast<std::size_t>(std::max(1, config.axis_count)));
  tcp_pose_ = {118.0, 15.0, 205.0, 180.0, 0.0, 90.0};
  std::ostringstream oss;
  oss << "configureRtMainline(robot=" << config.robot_model
      << ", class=" << config.sdk_robot_class
      << ", preferred_link=" << config.preferred_link
      << ", single_control_source=" << (config.requires_single_control_source ? "true" : "false")
      << ", rt_network_tolerance=" << config.rt_network_tolerance_percent
      << ", joint_filter_hz=" << config.joint_filter_hz
      << ", cart_filter_hz=" << config.cart_filter_hz
      << ", torque_filter_hz=" << config.torque_filter_hz
      << ", axis_count=" << config.axis_count
      << ", cartesian_impedance_z=" << config.cartesian_impedance[2]
      << ", desired_wrench_z=" << config.desired_wrench_n[2]
      << ", tcp_frame_translation_m=["
      << rt_config_.tcp_frame_matrix_m[3] << ',' << rt_config_.tcp_frame_matrix_m[7] << ',' << rt_config_.tcp_frame_matrix_m[11]
      << "])";
  binding_detail_ = rt_mainline_configured_ ? "rt_contract_configured_waiting_live_binding" : "rt_contract_config_invalid";
  refreshBindingTruth();
  appendLog(oss.str());
  appendLog("sdk boundary normalization ui(mm)->sdk(m) enabled");
  return rt_mainline_configured_;
}

bool SdkRobotFacade::beginNrtProfile(const std::string& profile, const std::string& sdk_command, bool requires_auto_mode, std::string* reason) {
  if (!connected_) {
    if (reason != nullptr) *reason = "controller_not_connected";
    binding_detail_ = "nrt_blocked_controller_not_connected";
    refreshBindingTruth();
    appendLog("nrt profile blocked: controller_not_connected");
    return false;
  }
  if (!powered_) {
    if (reason != nullptr) *reason = "controller_not_powered";
    binding_detail_ = "nrt_blocked_controller_not_powered";
    refreshBindingTruth();
    appendLog("nrt profile blocked: controller_not_powered");
    return false;
  }
  if (requires_auto_mode && !auto_mode_) {
    if (reason != nullptr) *reason = "auto_mode_required";
    binding_detail_ = "nrt_blocked_auto_mode_required";
    refreshBindingTruth();
    appendLog("nrt profile blocked: auto_mode_required");
    return false;
  }
  if (!control_source_exclusive_) {
    if (reason != nullptr) *reason = "single_control_source_required";
    binding_detail_ = "nrt_blocked_single_control_source_required";
    refreshBindingTruth();
    appendLog("nrt profile blocked: single_control_source_required");
    return false;
  }
  if (!motion_channel_ready_) {
    if (reason != nullptr) *reason = "motion_channel_not_ready";
    binding_detail_ = "nrt_blocked_motion_channel_not_ready";
    refreshBindingTruth();
    appendLog("nrt profile blocked: motion_channel_not_ready");
    return false;
  }
  active_nrt_profile_ = profile;
  ++command_sequence_;
  registers_["spine.command.sequence"] = command_sequence_;
  binding_detail_ = "nrt_contract_accepted_waiting_live_binding";
  refreshBindingTruth();
  appendLog(std::string("moveReset(); moveAppend(") + sdk_command + "); moveStart(); profile=" + profile + "; command_sequence=" + std::to_string(command_sequence_));
  return true;
}

void SdkRobotFacade::finishNrtProfile(const std::string& profile, bool success, const std::string& detail) {
  if (active_nrt_profile_ == profile) {
    active_nrt_profile_ = "idle";
  }
  binding_detail_ = success ? "nrt_contract_finished" : "nrt_contract_failed";
  refreshBindingTruth();
  appendLog(std::string("nrt profile ") + profile + (success ? " finished" : " failed") + (detail.empty() ? std::string() : std::string(" detail=") + detail));
}

bool SdkRobotFacade::beginRtMainline(const std::string& phase, int nominal_loop_hz, std::string* reason) {
  if (!connected_ || !powered_ || !auto_mode_) {
    if (reason != nullptr) *reason = "rt_lifecycle_not_ready";
    binding_detail_ = "rt_blocked_lifecycle_not_ready";
    refreshBindingTruth();
    appendLog("rt mainline blocked: lifecycle_not_ready");
    return false;
  }
  if (!rt_mainline_configured_) {
    if (reason != nullptr) *reason = "rt_mainline_not_configured";
    binding_detail_ = "rt_blocked_not_configured";
    refreshBindingTruth();
    appendLog("rt mainline blocked: rt_mainline_not_configured");
    return false;
  }
  if (!control_source_exclusive_) {
    if (reason != nullptr) *reason = "single_control_source_required";
    binding_detail_ = "rt_blocked_single_control_source_required";
    refreshBindingTruth();
    appendLog("rt mainline blocked: single_control_source_required");
    return false;
  }
  if (!network_healthy_) {
    if (reason != nullptr) *reason = "network_unhealthy";
    binding_detail_ = "rt_blocked_network_unhealthy";
    refreshBindingTruth();
    appendLog("rt mainline blocked: network_unhealthy");
    return false;
  }
  active_rt_phase_ = phase;
  nominal_rt_loop_hz_ = nominal_loop_hz > 0 ? nominal_loop_hz : nominal_rt_loop_hz_;
  ++command_sequence_;
  registers_["spine.command.sequence"] = command_sequence_;
  setRtPhaseCode(phase);
  binding_detail_ = vendored_sdk_detected_ ? "rt_contract_ready_live_binding_not_established" : "rt_contract_only";
  refreshBindingTruth();
  appendLog(std::string("rt mainline begin phase=") + phase + ", nominal_loop_hz=" + std::to_string(nominal_rt_loop_hz_) + ", command_sequence=" + std::to_string(command_sequence_));
  return true;
}

void SdkRobotFacade::updateRtPhase(const std::string& phase, const std::string& detail) {
  active_rt_phase_ = phase;
  setRtPhaseCode(phase);
  appendLog(std::string("rt phase=") + phase + (detail.empty() ? std::string() : std::string(" detail=") + detail));
}

void SdkRobotFacade::finishRtMainline(const std::string& phase, const std::string& detail) {
  if (active_rt_phase_ == phase) {
    active_rt_phase_ = "idle";
  }
  setRtPhaseCode("idle");
  live_binding_established_ = false;
  binding_detail_ = "rt_contract_finished";
  refreshBindingTruth();
  appendLog(std::string("rt mainline end phase=") + phase + (detail.empty() ? std::string() : std::string(" detail=") + detail));
}

std::vector<double> SdkRobotFacade::zeroVector(std::size_t count) {
  return std::vector<double>(count, 0.0);
}

void SdkRobotFacade::appendLog(const std::string& message) {
  configuration_log_.push_back(message);
  controller_logs_.insert(controller_logs_.begin(), message);
  if (controller_logs_.size() > 40) {
    controller_logs_.resize(40);
  }
}

void SdkRobotFacade::refreshStateVectors(std::size_t axis_count) {
  joint_pos_ = zeroVector(axis_count);
  joint_vel_ = zeroVector(axis_count);
  joint_torque_ = zeroVector(axis_count);
  for (std::size_t idx = 0; idx < axis_count; ++idx) {
    joint_pos_[idx] = 0.05 * std::sin(static_cast<double>(idx) * 0.4);
    joint_vel_[idx] = 0.01 * std::cos(static_cast<double>(idx) * 0.3);
    joint_torque_[idx] = 0.2 * std::sin(static_cast<double>(idx) * 0.2);
  }
}

void SdkRobotFacade::refreshInventoryForAxisCount(std::size_t axis_count) {
  path_library_.clear();
  path_library_.push_back({"spine_demo_path", 0.5, std::max<int>(static_cast<int>(axis_count) * 20, 128)});
  path_library_.push_back({"thoracic_followup", 0.4, std::max<int>(static_cast<int>(axis_count) * 15, 92)});
}

void SdkRobotFacade::refreshBindingTruth() {
  vendored_sdk_detected_ = sdkAvailable();
  backend_kind_ = vendored_sdk_detected_ ? "vendored_sdk_contract_shell" : "contract_sim";
  if (!vendored_sdk_detected_) {
    live_binding_established_ = false;
  }
}

void SdkRobotFacade::setRtPhaseCode(const std::string& phase) {
  registers_["spine.rt.phase_code"] =
      (phase == "seek_contact" ? 1 : (phase == "scan_follow" ? 2 : (phase == "pause_hold" ? 3 : (phase == "controlled_retract" ? 4 : 0))));
}

}  // namespace robot_core
