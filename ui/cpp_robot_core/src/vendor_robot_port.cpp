#include "robot_core/vendor_robot_port.h"

namespace robot_core {

namespace {
VendorRobotPortSnapshot buildSnapshot(const SdkRobotFacade* facade) {
  VendorRobotPortSnapshot out;
  if (facade == nullptr) {
    return out;
  }
  out.binding_mode = facade->sdkBindingMode();
  out.runtime_source = facade->runtimeSource();
  out.lifecycle_state = facade->hardwareLifecycleState();
  out.sdk_available = facade->sdkAvailable();
  out.xmate_model_available = facade->xmateModelAvailable();
  out.motion_channel_ready = facade->motionChannelReady();
  out.state_channel_ready = facade->stateChannelReady();
  out.aux_channel_ready = facade->auxChannelReady();
  out.control_source_exclusive = facade->controlSourceExclusive();
  out.network_healthy = facade->networkHealthy();
  out.nominal_rt_loop_hz = facade->nominalRtLoopHz();
  out.active_nrt_profile = facade->activeNrtProfile();
  out.active_rt_phase = facade->activeRtPhase();
  out.command_sequence = facade->commandSequence();
  return out;
}
}  // namespace

VendorRobotPortSnapshot XCoreRobotPort::snapshot() const { return buildSnapshot(facade_); }
bool XCoreRobotPort::connect(const std::string& remote_ip, const std::string& local_ip) { return facade_ != nullptr && facade_->connect(remote_ip, local_ip); }
void XCoreRobotPort::disconnect() { if (facade_ != nullptr) facade_->disconnect(); }
bool XCoreRobotPort::setPower(bool on) { return facade_ != nullptr && facade_->setPower(on); }
bool XCoreRobotPort::setAutoMode() { return facade_ != nullptr && facade_->setAutoMode(); }
bool XCoreRobotPort::setManualMode() { return facade_ != nullptr && facade_->setManualMode(); }
bool XCoreRobotPort::configureRtMainline(const SdkRobotRuntimeConfig& config) { return facade_ != nullptr && facade_->configureRtMainline(config); }

VendorRobotPortSnapshot LabRobotPort::snapshot() const { return buildSnapshot(facade_); }
bool LabRobotPort::connect(const std::string& remote_ip, const std::string& local_ip) { return facade_ != nullptr && facade_->connect(remote_ip, local_ip); }
void LabRobotPort::disconnect() { if (facade_ != nullptr) facade_->disconnect(); }
bool LabRobotPort::setPower(bool on) { return facade_ != nullptr && facade_->setPower(on); }
bool LabRobotPort::setAutoMode() { return facade_ != nullptr && facade_->setAutoMode(); }
bool LabRobotPort::setManualMode() { return facade_ != nullptr && facade_->setManualMode(); }
bool LabRobotPort::configureRtMainline(const SdkRobotRuntimeConfig& config) { return facade_ != nullptr && facade_->configureRtMainline(config); }

}  // namespace robot_core
