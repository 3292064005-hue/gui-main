#include "robot_core/sdk_robot_facade_internal.h"

namespace robot_core {

SdkRobotLifecyclePort::SdkRobotLifecyclePort(SdkRobotFacade& owner) : owner_(owner) {}
SdkRobotQueryPort::SdkRobotQueryPort(SdkRobotFacade& owner) : owner_(owner) {}
SdkRobotNrtExecutionPort::SdkRobotNrtExecutionPort(SdkRobotFacade& owner) : owner_(owner) {}
SdkRobotRtControlPort::SdkRobotRtControlPort(SdkRobotFacade& owner) : owner_(owner) {}
SdkRobotCollaborationPort::SdkRobotCollaborationPort(SdkRobotFacade& owner) : owner_(owner) {}

LifecyclePort& SdkRobotFacade::lifecyclePort() { return *lifecycle_port_; }
const LifecyclePort& SdkRobotFacade::lifecyclePort() const { return *lifecycle_port_; }
QueryPort& SdkRobotFacade::queryPort() { return *query_port_; }
const QueryPort& SdkRobotFacade::queryPort() const { return *query_port_; }
NrtExecutionPort& SdkRobotFacade::nrtExecutionPort() { return *nrt_execution_port_; }
const NrtExecutionPort& SdkRobotFacade::nrtExecutionPort() const { return *nrt_execution_port_; }
RtControlPort& SdkRobotFacade::rtControlPort() { return *rt_control_port_; }
const RtControlPort& SdkRobotFacade::rtControlPort() const { return *rt_control_port_; }
CollaborationPort& SdkRobotFacade::collaborationPort() { return *collaboration_port_; }
const CollaborationPort& SdkRobotFacade::collaborationPort() const { return *collaboration_port_; }

bool SdkRobotLifecyclePort::connect(const std::string& remote_ip, const std::string& local_ip) { return owner_.connect(remote_ip, local_ip); }
void SdkRobotLifecyclePort::disconnect() { owner_.disconnect(); }
bool SdkRobotLifecyclePort::setPower(bool on) { return owner_.setPower(on); }
bool SdkRobotLifecyclePort::setAutoMode() { return owner_.setAutoMode(); }
bool SdkRobotLifecyclePort::setManualMode() { return owner_.setManualMode(); }
bool SdkRobotLifecyclePort::ensureConnected(std::string* reason) { return owner_.ensureConnected(reason); }
bool SdkRobotLifecyclePort::ensurePoweredAuto(std::string* reason) { return owner_.ensurePoweredAuto(reason); }
bool SdkRobotLifecyclePort::ensureNrtMode(std::string* reason) { return owner_.ensureNrtMode(reason); }

SdkRobotRuntimeConfig SdkRobotQueryPort::runtimeConfig() const { return owner_.runtimeConfig(); }
std::vector<std::string> SdkRobotQueryPort::controllerLogs() const { return owner_.controllerLogs(); }
std::vector<SdkRobotProjectInfo> SdkRobotQueryPort::rlProjects() const { return owner_.rlProjects(); }
SdkRobotRlStatus SdkRobotQueryPort::rlStatus() const { return owner_.rlStatus(); }
std::vector<SdkRobotPathInfo> SdkRobotQueryPort::pathLibrary() const { return owner_.pathLibrary(); }
SdkRobotDragState SdkRobotQueryPort::dragState() const { return owner_.dragState(); }
std::map<std::string, bool> SdkRobotQueryPort::di() const { return owner_.di(); }
std::map<std::string, bool> SdkRobotQueryPort::doState() const { return owner_.doState(); }
std::map<std::string, double> SdkRobotQueryPort::ai() const { return owner_.ai(); }
std::map<std::string, double> SdkRobotQueryPort::ao() const { return owner_.ao(); }
std::map<std::string, int> SdkRobotQueryPort::registers() const { return owner_.registers(); }
std::string SdkRobotQueryPort::runtimeSource() const { return owner_.runtimeSource(); }
bool SdkRobotQueryPort::sdkAvailable() const { return owner_.sdkAvailable(); }
bool SdkRobotQueryPort::xmateModelAvailable() const { return owner_.xmateModelAvailable(); }
bool SdkRobotQueryPort::controlSourceExclusive() const { return owner_.controlSourceExclusive(); }
bool SdkRobotQueryPort::networkHealthy() const { return owner_.networkHealthy(); }
bool SdkRobotQueryPort::motionChannelReady() const { return owner_.motionChannelReady(); }
bool SdkRobotQueryPort::stateChannelReady() const { return owner_.stateChannelReady(); }
bool SdkRobotQueryPort::auxChannelReady() const { return owner_.auxChannelReady(); }
int SdkRobotQueryPort::nominalRtLoopHz() const { return owner_.nominalRtLoopHz(); }
std::string SdkRobotQueryPort::activeRtPhase() const { return owner_.activeRtPhase(); }
std::string SdkRobotQueryPort::activeNrtProfile() const { return owner_.activeNrtProfile(); }
int SdkRobotQueryPort::commandSequence() const { return owner_.commandSequence(); }
std::string SdkRobotQueryPort::sdkBindingMode() const { return owner_.sdkBindingMode(); }
std::string SdkRobotQueryPort::hardwareLifecycleState() const { return owner_.hardwareLifecycleState(); }
bool SdkRobotQueryPort::liveBindingEstablished() const { return owner_.liveBindingEstablished(); }
RtPhaseTelemetry SdkRobotQueryPort::phaseTelemetry() const { return owner_.phaseTelemetry(); }
bool SdkRobotQueryPort::liveTakeoverReady() const { return owner_.liveTakeoverReady(); }

bool SdkRobotNrtExecutionPort::executeMoveAbsJ(const std::vector<double>& joints_rad, int speed_mm_s, int zone_mm, std::string* reason) { return owner_.executeMoveAbsJ(joints_rad, speed_mm_s, zone_mm, reason); }
bool SdkRobotNrtExecutionPort::executeMoveL(const std::vector<double>& tcp_xyzabc_m_rad, int speed_mm_s, int zone_mm, std::string* reason) { return owner_.executeMoveL(tcp_xyzabc_m_rad, speed_mm_s, zone_mm, reason); }
bool SdkRobotNrtExecutionPort::stop(std::string* reason) { return owner_.stopNrt(reason); }
bool SdkRobotNrtExecutionPort::beginProfile(const std::string& profile, const std::string& sdk_command, bool requires_auto_mode, std::string* reason) { return owner_.beginNrtProfile(profile, sdk_command, requires_auto_mode, reason); }
void SdkRobotNrtExecutionPort::finishProfile(const std::string& profile, bool success, const std::string& detail) { owner_.finishNrtProfile(profile, success, detail); }

bool SdkRobotRtControlPort::configureMainline(const SdkRobotRuntimeConfig& config) { return owner_.configureRtMainline(config); }
bool SdkRobotRtControlPort::ensureRtMode(std::string* reason) { return owner_.ensureRtMode(reason); }
bool SdkRobotRtControlPort::ensureController(std::string* reason) { return owner_.ensureRtController(reason); }
bool SdkRobotRtControlPort::ensureStateStream(const std::vector<std::string>& fields, std::string* reason) { return owner_.ensureRtStateStream(fields, reason); }
bool SdkRobotRtControlPort::applyConfig(const SdkRobotRuntimeConfig& config, std::string* reason) { return owner_.applyRtConfig(config, reason); }
bool SdkRobotRtControlPort::stop(std::string* reason) { return owner_.stopRt(reason); }
bool SdkRobotRtControlPort::beginMainline(const std::string& phase, int nominal_loop_hz, std::string* reason) { return owner_.beginRtMainline(phase, nominal_loop_hz, reason); }
void SdkRobotRtControlPort::updatePhase(const std::string& phase, const std::string& detail) { owner_.updateRtPhase(phase, detail); }
void SdkRobotRtControlPort::finishMainline(const std::string& phase, const std::string& detail) { owner_.finishRtMainline(phase, detail); }
bool SdkRobotRtControlPort::populateObservedState(RtObservedState& out, std::string* reason) { return owner_.populateObservedState(out, reason); }
RtPhaseStepResult SdkRobotRtControlPort::stepSeekContact(const RtObservedState& state) { return owner_.stepSeekContact(state); }
RtPhaseStepResult SdkRobotRtControlPort::stepScanFollow(const RtObservedState& state) { return owner_.stepScanFollow(state); }
RtPhaseStepResult SdkRobotRtControlPort::stepPauseHold(const RtObservedState& state) { return owner_.stepPauseHold(state); }
RtPhaseStepResult SdkRobotRtControlPort::stepControlledRetract(const RtObservedState& state) { return owner_.stepControlledRetract(state); }
void SdkRobotRtControlPort::resetPhaseIntegrators() { owner_.resetRtPhaseIntegrators(); }
bool SdkRobotRtControlPort::validateContract(std::string* reason) const { return owner_.validateRtControlContract(reason); }
void SdkRobotRtControlPort::setControlContract(const RtPhaseControlContract& contract) { owner_.setRtPhaseControlContract(contract); }
SdkRobotRuntimeConfig SdkRobotRtControlPort::runtimeConfig() const { return owner_.runtimeConfig(); }
std::string SdkRobotRtControlPort::activeRtPhase() const { return owner_.activeRtPhase(); }
bool SdkRobotRtControlPort::networkHealthy() const { return owner_.networkHealthy(); }
int SdkRobotRtControlPort::nominalRtLoopHz() const { return owner_.nominalRtLoopHz(); }
bool SdkRobotRtControlPort::liveBindingEstablished() const { return owner_.liveBindingEstablished(); }
RtPhaseTelemetry SdkRobotRtControlPort::phaseTelemetry() const { return owner_.phaseTelemetry(); }

bool SdkRobotCollaborationPort::runRlProject(const std::string& project, const std::string& task, std::string* reason) { return owner_.runRlProject(project, task, reason); }
bool SdkRobotCollaborationPort::pauseRlProject(std::string* reason) { return owner_.pauseRlProject(reason); }
bool SdkRobotCollaborationPort::enableDrag(const std::string& space, const std::string& type, std::string* reason) { return owner_.enableDrag(space, type, reason); }
bool SdkRobotCollaborationPort::disableDrag(std::string* reason) { return owner_.disableDrag(reason); }
bool SdkRobotCollaborationPort::replayPath(const std::string& name, double rate, std::string* reason) { return owner_.replayPath(name, rate, reason); }
bool SdkRobotCollaborationPort::startRecordPath(int duration_s, std::string* reason) { return owner_.startRecordPath(duration_s, reason); }
bool SdkRobotCollaborationPort::stopRecordPath(std::string* reason) { return owner_.stopRecordPath(reason); }
bool SdkRobotCollaborationPort::cancelRecordPath(std::string* reason) { return owner_.cancelRecordPath(reason); }
bool SdkRobotCollaborationPort::saveRecordPath(const std::string& name, const std::string& save_as, std::string* reason) { return owner_.saveRecordPath(name, save_as, reason); }
void SdkRobotCollaborationPort::setRlStatus(const std::string& project, const std::string& task, bool running) { owner_.setRlStatus(project, task, running); }
void SdkRobotCollaborationPort::setDragState(bool enabled, const std::string& space, const std::string& type) { owner_.setDragState(enabled, space, type); }

}  // namespace robot_core
