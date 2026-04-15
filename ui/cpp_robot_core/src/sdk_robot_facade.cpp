#include "robot_core/sdk_robot_facade_internal.h"

#include <sstream>
#include <stdexcept>

namespace robot_core {

using namespace sdk_robot_facade_internal;

SdkRobotFacade::SdkRobotFacade() {
  lifecycle_port_ = std::make_unique<SdkRobotLifecyclePort>(*this);
  query_port_ = std::make_unique<SdkRobotQueryPort>(*this);
  nrt_execution_port_ = std::make_unique<SdkRobotNrtExecutionPort>(*this);
  rt_control_port_ = std::make_unique<SdkRobotRtControlPort>(*this);
  collaboration_port_ = std::make_unique<SdkRobotCollaborationPort>(*this);
  vendored_sdk_detected_ = sdkAvailable();
  backend_kind_ = vendored_sdk_detected_ ? "vendored_sdk_contract_shell" : "contract_sim";
  binding_detail_ = vendored_sdk_detected_ ? "vendored_sdk_detected_waiting_live_binding" : "no_vendored_sdk_detected";
  refreshStateVectors(6);
  refreshInventoryForAxisCount(6);
  tcp_pose_ = {0.0, 0.0, 0.240, 0.0, 0.0, 0.0};
  rl_projects_ = {{"spine_mainline", {"scan", "prep", "retreat"}}, {"spine_research", {"sweep", "contact_probe"}}};
  di_ = {{"board0_port0", false}, {"board0_port1", true}};
  do_ = {{"board0_port0", false}, {"board0_port1", false}};
  ai_ = {{"board0_port0", 0.12}};
  ao_ = {{"board0_port0", 0.0}};
  registers_ = {{"spine.session.segment", 0}, {"spine.session.frame", 0}, {"spine.rt.phase_code", 0}, {"spine.command.sequence", 0}};
  configureContactControllersFromRuntimeConfig();
  refreshBindingTruth();
  appendLog(std::string("sdk facade booted source=") + runtimeSource());
}

/**
 * @brief Establish the single authoritative SDK lifecycle binding for the runtime.
 *
 * The function either returns with a fully initialized live xCore binding or a
 * truthful contract-shell state. It never reports a successful contract-shell
 * connection after a live bind attempt has failed.
 *
 * @param remote_ip Robot controller IP address used by the vendor SDK.
 * @param local_ip Host interface IP used for RT state / command traffic.
 * @return true when a connection is established for the current build profile.
 *         With ROBOT_CORE_WITH_XCORE_SDK enabled this means a real live bind;
 *         otherwise it means the contract-shell transport is connected.
 * @exception None. Vendor exceptions are captured and converted into binding
 *            detail / controller-log evidence, and the function returns false.
 * @note Empty IP inputs are rejected before touching the SDK.
 */
bool SdkRobotFacade::connect(const std::string& remote_ip, const std::string& local_ip) {
  rt_config_.remote_ip = remote_ip;
  rt_config_.local_ip = local_ip;
  if (remote_ip.empty() || local_ip.empty()) {
    captureFailure("connectToRobot", "remote_ip/local_ip missing");
    robot_.reset();
    rt_controller_.reset();
    connected_ = false;
    state_channel_ready_ = false;
    aux_channel_ready_ = false;
    motion_channel_ready_ = false;
    network_healthy_ = false;
    live_binding_established_ = false;
    powered_ = false;
    auto_mode_ = false;
    rt_mainline_configured_ = false;
    active_rt_phase_.clear();
    active_nrt_profile_.clear();
    refreshBindingTruth();
    return false;
  }
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  try {
    robot_ = std::make_shared<rokae::xMateRobot>(remote_ip, local_ip);
    connected_ = true;
    live_binding_established_ = true;
    network_healthy_ = true;
    state_channel_ready_ = true;
    aux_channel_ready_ = true;
    motion_channel_ready_ = powered_;
    backend_kind_ = "xcore_sdk_live_binding";
    binding_detail_ = "live_binding_connected";
    refreshRuntimeCaches();
    appendLog("connectToRobot(" + remote_ip + "," + local_ip + ") live_binding_established");
    refreshBindingTruth();
    return true;
  } catch (const std::exception& ex) {
    robot_.reset();
    connected_ = false;
    state_channel_ready_ = false;
    aux_channel_ready_ = false;
    motion_channel_ready_ = false;
    network_healthy_ = false;
    live_binding_established_ = false;
    powered_ = false;
    auto_mode_ = false;
    rt_mainline_configured_ = false;
    active_rt_phase_.clear();
    active_nrt_profile_.clear();
    backend_kind_ = "vendored_sdk_contract_shell";
    binding_detail_ = "live_binding_failed";
    captureException("connectToRobot", ex);
    binding_detail_ = "live_binding_failed";
    appendLog("connectToRobot(" + remote_ip + "," + local_ip + ") live_binding_failed");
    refreshBindingTruth();
    return false;
  }
#else
  connected_ = true;
  state_channel_ready_ = true;
  aux_channel_ready_ = true;
  motion_channel_ready_ = powered_;
  binding_detail_ = "contract_shell_connected";
  appendLog("connectToRobot(" + remote_ip + "," + local_ip + ") contract_only");
  refreshBindingTruth();
  return true;
#endif
}

/**
 * @brief Tear down the authoritative lifecycle binding and reset cached runtime state.
 *
 * @return void
 * @exception None. Vendor disconnect exceptions are captured as controller-log
 *            evidence so shutdown remains idempotent.
 * @boundary Stops any active RT phase before dropping the SDK handle and resets
 *           lifecycle / telemetry caches back to the disconnected baseline.
 */
void SdkRobotFacade::disconnect() {
  std::string ignored;
  stopRt(&ignored);
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  try {
    if (robot_ != nullptr) {
      std::error_code ec;
      robot_->disconnectFromRobot(ec);
      applyErrorCode("disconnectFromRobot", ec, nullptr);
    }
  } catch (const std::exception& ex) {
    captureException("disconnectFromRobot", ex);
  }
#endif
  robot_.reset();
  rt_controller_.reset();
  connected_ = false;
  powered_ = false;
  auto_mode_ = false;
  rt_mainline_configured_ = false;
  motion_channel_ready_ = false;
  state_channel_ready_ = false;
  aux_channel_ready_ = false;
  network_healthy_ = false;
  live_binding_established_ = false;
  rt_state_stream_started_ = false;
  rt_loop_active_ = false;
  nominal_rt_loop_hz_ = 1000;
  active_rt_phase_ = "idle";
  active_nrt_profile_ = "idle";
  rl_status_ = {};
  drag_state_ = {};
  refreshStateVectors(static_cast<std::size_t>(std::max(1, rt_config_.axis_count)));
  refreshInventoryForAxisCount(static_cast<std::size_t>(std::max(1, rt_config_.axis_count)));
  tcp_pose_ = {0.0, 0.0, 0.240, 0.0, 0.0, 0.0};
  updateSessionRegisters(0, 0);
  binding_detail_ = "disconnected";
  refreshBindingTruth();
  appendLog("disconnectFromRobot() complete");
}

SdkRobotFacade::~SdkRobotFacade() = default;

bool SdkRobotFacade::requireLiveWrite(const std::string& prefix, std::string* reason) {
  if (live_binding_established_ && robot_ != nullptr) {
    return true;
  }
  if (rt_config_.allow_contract_shell_writes) {
    appendLog(prefix + " contract_shell_write_override");
    return true;
  }
  captureFailure(prefix, vendored_sdk_detected_ ? "live_binding_required" : "sdk_live_binding_unavailable", reason);
  binding_detail_ = vendored_sdk_detected_ ? "live_write_blocked_contract_shell" : "live_write_blocked_no_sdk";
  refreshBindingTruth();
  return false;
}

void SdkRobotFacade::finalizeNrtStopLocal(const std::string& detail) {
  active_nrt_profile_ = "idle";
  if (!detail.empty()) {
    appendLog("stop() local teardown: " + detail);
  }
  refreshRuntimeCaches();
  refreshBindingTruth();
}

void SdkRobotFacade::finalizeRtStopLocal(const std::string& detail) {
  rt_state_stream_started_ = false;
  rt_loop_active_ = false;
  active_rt_phase_ = "idle";
  setRtPhaseCode("idle");
  if (!detail.empty()) {
    appendLog("stopRt() local teardown: " + detail);
  }
  refreshRuntimeCaches();
  refreshBindingTruth();
}

}  // namespace robot_core
