#include "robot_core/sdk_robot_facade.h"

namespace robot_core {

SdkRobotFacade::LifecyclePort& SdkRobotFacade::lifecyclePort() { return lifecycle_port_; }
const SdkRobotFacade::LifecyclePort& SdkRobotFacade::lifecyclePort() const { return lifecycle_port_; }
SdkRobotFacade::QueryPort& SdkRobotFacade::queryPort() { return query_port_; }
const SdkRobotFacade::QueryPort& SdkRobotFacade::queryPort() const { return query_port_; }
SdkRobotFacade::NrtExecutionPort& SdkRobotFacade::nrtExecutionPort() { return nrt_execution_port_; }
const SdkRobotFacade::NrtExecutionPort& SdkRobotFacade::nrtExecutionPort() const { return nrt_execution_port_; }
SdkRobotFacade::RtControlPort& SdkRobotFacade::rtControlPort() { return rt_control_port_; }
const SdkRobotFacade::RtControlPort& SdkRobotFacade::rtControlPort() const { return rt_control_port_; }
SdkRobotFacade::CollaborationPort& SdkRobotFacade::collaborationPort() { return collaboration_port_; }
const SdkRobotFacade::CollaborationPort& SdkRobotFacade::collaborationPort() const { return collaboration_port_; }

bool SdkRobotFacade::LifecyclePort::connect(const std::string& remote_ip, const std::string& local_ip) {
  return owner_.connect(remote_ip, local_ip);
}

void SdkRobotFacade::LifecyclePort::disconnect() { owner_.disconnect(); }

bool SdkRobotFacade::LifecyclePort::setPower(bool on) { return owner_.setPower(on); }

bool SdkRobotFacade::LifecyclePort::setAutoMode() { return owner_.setAutoMode(); }

bool SdkRobotFacade::LifecyclePort::setManualMode() { return owner_.setManualMode(); }

bool SdkRobotFacade::LifecyclePort::ensureConnected(std::string* reason) { return owner_.ensureConnected(reason); }

bool SdkRobotFacade::LifecyclePort::ensurePoweredAuto(std::string* reason) { return owner_.ensurePoweredAuto(reason); }

bool SdkRobotFacade::LifecyclePort::ensureNrtMode(std::string* reason) { return owner_.ensureNrtMode(reason); }

SdkRobotRuntimeConfig SdkRobotFacade::QueryPort::runtimeConfig() const { return owner_.runtimeConfig(); }
std::vector<std::string> SdkRobotFacade::QueryPort::controllerLogs() const { return owner_.controllerLogs(); }
std::vector<SdkRobotProjectInfo> SdkRobotFacade::QueryPort::rlProjects() const { return owner_.rlProjects(); }
SdkRobotRlStatus SdkRobotFacade::QueryPort::rlStatus() const { return owner_.rlStatus(); }
std::vector<SdkRobotPathInfo> SdkRobotFacade::QueryPort::pathLibrary() const { return owner_.pathLibrary(); }
SdkRobotDragState SdkRobotFacade::QueryPort::dragState() const { return owner_.dragState(); }
std::map<std::string, bool> SdkRobotFacade::QueryPort::di() const { return owner_.di(); }
std::map<std::string, bool> SdkRobotFacade::QueryPort::doState() const { return owner_.doState(); }
std::map<std::string, double> SdkRobotFacade::QueryPort::ai() const { return owner_.ai(); }
std::map<std::string, double> SdkRobotFacade::QueryPort::ao() const { return owner_.ao(); }
std::map<std::string, int> SdkRobotFacade::QueryPort::registers() const { return owner_.registers(); }
std::string SdkRobotFacade::QueryPort::runtimeSource() const { return owner_.runtimeSource(); }
bool SdkRobotFacade::QueryPort::sdkAvailable() const { return owner_.sdkAvailable(); }
bool SdkRobotFacade::QueryPort::xmateModelAvailable() const { return owner_.xmateModelAvailable(); }
bool SdkRobotFacade::QueryPort::controlSourceExclusive() const { return owner_.controlSourceExclusive(); }
bool SdkRobotFacade::QueryPort::networkHealthy() const { return owner_.networkHealthy(); }
bool SdkRobotFacade::QueryPort::motionChannelReady() const { return owner_.motionChannelReady(); }
bool SdkRobotFacade::QueryPort::stateChannelReady() const { return owner_.stateChannelReady(); }
bool SdkRobotFacade::QueryPort::auxChannelReady() const { return owner_.auxChannelReady(); }
int SdkRobotFacade::QueryPort::nominalRtLoopHz() const { return owner_.nominalRtLoopHz(); }
std::string SdkRobotFacade::QueryPort::activeRtPhase() const { return owner_.activeRtPhase(); }
std::string SdkRobotFacade::QueryPort::activeNrtProfile() const { return owner_.activeNrtProfile(); }
int SdkRobotFacade::QueryPort::commandSequence() const { return owner_.commandSequence(); }
std::string SdkRobotFacade::QueryPort::sdkBindingMode() const { return owner_.sdkBindingMode(); }
std::string SdkRobotFacade::QueryPort::hardwareLifecycleState() const { return owner_.hardwareLifecycleState(); }
bool SdkRobotFacade::QueryPort::liveBindingEstablished() const { return owner_.liveBindingEstablished(); }
RtPhaseTelemetry SdkRobotFacade::QueryPort::phaseTelemetry() const { return owner_.phaseTelemetry(); }
bool SdkRobotFacade::QueryPort::liveTakeoverReady() const { return owner_.liveTakeoverReady(); }

bool SdkRobotFacade::NrtExecutionPort::executeMoveAbsJ(const std::vector<double>& joints_rad, int speed_mm_s, int zone_mm, std::string* reason) {
  return owner_.executeMoveAbsJ(joints_rad, speed_mm_s, zone_mm, reason);
}

bool SdkRobotFacade::NrtExecutionPort::executeMoveL(const std::vector<double>& tcp_xyzabc_m_rad, int speed_mm_s, int zone_mm, std::string* reason) {
  return owner_.executeMoveL(tcp_xyzabc_m_rad, speed_mm_s, zone_mm, reason);
}

bool SdkRobotFacade::NrtExecutionPort::stop(std::string* reason) { return owner_.stopNrt(reason); }

bool SdkRobotFacade::NrtExecutionPort::beginProfile(const std::string& profile, const std::string& sdk_command, bool requires_auto_mode, std::string* reason) {
  return owner_.beginNrtProfile(profile, sdk_command, requires_auto_mode, reason);
}

void SdkRobotFacade::NrtExecutionPort::finishProfile(const std::string& profile, bool success, const std::string& detail) {
  owner_.finishNrtProfile(profile, success, detail);
}

bool SdkRobotFacade::RtControlPort::configureMainline(const SdkRobotRuntimeConfig& config) { return owner_.configureRtMainline(config); }
bool SdkRobotFacade::RtControlPort::ensureRtMode(std::string* reason) { return owner_.ensureRtMode(reason); }
bool SdkRobotFacade::RtControlPort::ensureController(std::string* reason) { return owner_.ensureRtController(reason); }
bool SdkRobotFacade::RtControlPort::ensureStateStream(const std::vector<std::string>& fields, std::string* reason) { return owner_.ensureRtStateStream(fields, reason); }
bool SdkRobotFacade::RtControlPort::applyConfig(const SdkRobotRuntimeConfig& config, std::string* reason) { return owner_.applyRtConfig(config, reason); }
bool SdkRobotFacade::RtControlPort::stop(std::string* reason) { return owner_.stopRt(reason); }
bool SdkRobotFacade::RtControlPort::beginMainline(const std::string& phase, int nominal_loop_hz, std::string* reason) { return owner_.beginRtMainline(phase, nominal_loop_hz, reason); }
void SdkRobotFacade::RtControlPort::updatePhase(const std::string& phase, const std::string& detail) { owner_.updateRtPhase(phase, detail); }
void SdkRobotFacade::RtControlPort::finishMainline(const std::string& phase, const std::string& detail) { owner_.finishRtMainline(phase, detail); }
bool SdkRobotFacade::RtControlPort::populateObservedState(RtObservedState& out, std::string* reason) { return owner_.populateObservedState(out, reason); }
RtPhaseStepResult SdkRobotFacade::RtControlPort::stepSeekContact(const RtObservedState& state) { return owner_.stepSeekContact(state); }
RtPhaseStepResult SdkRobotFacade::RtControlPort::stepScanFollow(const RtObservedState& state) { return owner_.stepScanFollow(state); }
RtPhaseStepResult SdkRobotFacade::RtControlPort::stepPauseHold(const RtObservedState& state) { return owner_.stepPauseHold(state); }
RtPhaseStepResult SdkRobotFacade::RtControlPort::stepControlledRetract(const RtObservedState& state) { return owner_.stepControlledRetract(state); }
void SdkRobotFacade::RtControlPort::resetPhaseIntegrators() { owner_.resetRtPhaseIntegrators(); }
bool SdkRobotFacade::RtControlPort::validateContract(std::string* reason) const { return owner_.validateRtControlContract(reason); }
void SdkRobotFacade::RtControlPort::setControlContract(const RtPhaseControlContract& contract) { owner_.setRtPhaseControlContract(contract); }
SdkRobotRuntimeConfig SdkRobotFacade::RtControlPort::runtimeConfig() const { return owner_.runtimeConfig(); }
std::string SdkRobotFacade::RtControlPort::activeRtPhase() const { return owner_.activeRtPhase(); }
bool SdkRobotFacade::RtControlPort::networkHealthy() const { return owner_.networkHealthy(); }
int SdkRobotFacade::RtControlPort::nominalRtLoopHz() const { return owner_.nominalRtLoopHz(); }
bool SdkRobotFacade::RtControlPort::liveBindingEstablished() const { return owner_.liveBindingEstablished(); }
RtPhaseTelemetry SdkRobotFacade::RtControlPort::phaseTelemetry() const { return owner_.phaseTelemetry(); }

bool SdkRobotFacade::CollaborationPort::runRlProject(const std::string& project, const std::string& task, std::string* reason) {
  return owner_.runRlProject(project, task, reason);
}

bool SdkRobotFacade::CollaborationPort::pauseRlProject(std::string* reason) { return owner_.pauseRlProject(reason); }

bool SdkRobotFacade::CollaborationPort::enableDrag(const std::string& space, const std::string& type, std::string* reason) {
  return owner_.enableDrag(space, type, reason);
}

bool SdkRobotFacade::CollaborationPort::disableDrag(std::string* reason) { return owner_.disableDrag(reason); }

bool SdkRobotFacade::CollaborationPort::replayPath(const std::string& name, double rate, std::string* reason) {
  return owner_.replayPath(name, rate, reason);
}

bool SdkRobotFacade::CollaborationPort::startRecordPath(int duration_s, std::string* reason) {
  return owner_.startRecordPath(duration_s, reason);
}

bool SdkRobotFacade::CollaborationPort::stopRecordPath(std::string* reason) { return owner_.stopRecordPath(reason); }

bool SdkRobotFacade::CollaborationPort::cancelRecordPath(std::string* reason) { return owner_.cancelRecordPath(reason); }

bool SdkRobotFacade::CollaborationPort::saveRecordPath(const std::string& name, const std::string& save_as, std::string* reason) {
  return owner_.saveRecordPath(name, save_as, reason);
}

void SdkRobotFacade::CollaborationPort::setRlStatus(const std::string& project, const std::string& task, bool running) {
  owner_.setRlStatus(project, task, running);
}

void SdkRobotFacade::CollaborationPort::setDragState(bool enabled, const std::string& space, const std::string& type) {
  owner_.setDragState(enabled, space, type);
}

}  // namespace robot_core
