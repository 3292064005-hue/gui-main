#include "robot_core/sdk_robot_facade.h"

#ifdef ROBOT_CORE_WITH_XCORE_SDK
#include "rokae/data_types.h"
#include "rokae/robot.h"
#include "rokae/utility.h"
#endif

#include <algorithm>
#include <cmath>
#include <sstream>
#include <stdexcept>

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

std::size_t translationIndexForAxis(int axis) {
  switch (axis) {
    case 0: return 3;
    case 1: return 7;
    default: return 11;
  }
}

std::array<double, 16> postureVectorToMatrix(const std::vector<double>& posture) {
  std::array<double, 16> matrix{};
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  std::array<double, 6> xyzabc{0.0, 0.0, 0.240, 0.0, 0.0, 0.0};
  for (std::size_t idx = 0; idx < std::min<std::size_t>(xyzabc.size(), posture.size()); ++idx) {
    xyzabc[idx] = posture[idx];
  }
  rokae::Utils::postureToTransArray(xyzabc, matrix);
#else
  matrix = {1.0, 0.0, 0.0, 0.0,
            0.0, 1.0, 0.0, 0.0,
            0.0, 0.0, 1.0, 0.240,
            0.0, 0.0, 0.0, 1.0};
#endif
  return matrix;
}

double clampSigned(double value, double magnitude) {
  return std::max(-std::abs(magnitude), std::min(std::abs(magnitude), value));
}

std::array<double, 16> identityPoseMatrix() {
  return {1.0, 0.0, 0.0, 0.0,
          0.0, 1.0, 0.0, 0.0,
          0.0, 0.0, 1.0, 0.240,
          0.0, 0.0, 0.0, 1.0};
}

double degToRad(double value_deg) {
  return value_deg * M_PI / 180.0;
}

#ifdef ROBOT_CORE_WITH_XCORE_SDK
std::array<double, 6> toArray6(const std::vector<double>& values) {
  std::array<double, 6> out{};
  for (std::size_t idx = 0; idx < std::min<std::size_t>(out.size(), values.size()); ++idx) {
    out[idx] = values[idx];
  }
  return out;
}

std::array<double, 3> toArray3(const std::vector<double>& values) {
  std::array<double, 3> out{};
  for (std::size_t idx = 0; idx < std::min<std::size_t>(out.size(), values.size()); ++idx) {
    out[idx] = values[idx];
  }
  return out;
}
#endif

}  // namespace

SdkRobotFacade::SdkRobotFacade()
    : lifecycle_port_(*this),
      query_port_(*this),
      nrt_execution_port_(*this),
      rt_control_port_(*this),
      collaboration_port_(*this) {
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

SdkRobotFacade::~SdkRobotFacade() = default;

bool SdkRobotFacade::connect(const std::string& remote_ip, const std::string& local_ip) {
  rt_config_.remote_ip = remote_ip;
  rt_config_.local_ip = local_ip;
  if (remote_ip.empty() || local_ip.empty()) {
    captureFailure("connectToRobot", "remote_ip/local_ip missing");
    connected_ = false;
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
    automatic_mode_ = false;
    rt_mainline_configured_ = false;
    active_rt_phase_.clear();
    active_nrt_profile_.clear();
    backend_kind_ = "vendored_sdk_contract_shell";
    binding_detail_ = "live_binding_failed";
    captureException("connectToRobot", ex);
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

bool SdkRobotFacade::setPower(bool on) {
  if (!ensureConnected(nullptr)) {
    captureFailure("setPowerState", "controller_not_connected");
    return false;
  }
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->setPowerState(on, ec);
    if (!applyErrorCode("setPowerState", ec, nullptr)) {
      powered_ = false;
      motion_channel_ready_ = false;
      refreshBindingTruth();
      return false;
    }
    } catch (const std::exception& ex) {
      captureException("setPowerState", ex);
      return false;
    }
  }
#endif
  powered_ = on;
  motion_channel_ready_ = connected_ && powered_ && network_healthy_;
  binding_detail_ = on ? "powered" : "unpowered";
  refreshRuntimeCaches();
  refreshBindingTruth();
  appendLog(std::string("setPowerState(") + (on ? "on" : "off") + ") accepted");
  return true;
}

bool SdkRobotFacade::setAutoMode() {
  if (!ensureConnected(nullptr)) {
    captureFailure("setOperateMode(auto)", "controller_not_connected");
    return false;
  }
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->setOperateMode(rokae::OperateMode::automatic, ec);
    if (!applyErrorCode("setOperateMode(auto)", ec, nullptr)) {
      return false;
    }
    } catch (const std::exception& ex) {
      captureException("setOperateMode(auto)", ex);
      return false;
    }
  }
#endif
  auto_mode_ = true;
  binding_detail_ = "automatic_mode";
  refreshRuntimeCaches();
  refreshBindingTruth();
  appendLog("setOperateMode(auto) accepted");
  return true;
}

bool SdkRobotFacade::setManualMode() {
  if (!ensureConnected(nullptr)) {
    captureFailure("setOperateMode(manual)", "controller_not_connected");
    return false;
  }
  std::string ignored;
  stopRt(&ignored);
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->setOperateMode(rokae::OperateMode::manual, ec);
    if (!applyErrorCode("setOperateMode(manual)", ec, nullptr)) {
      return false;
    }
    } catch (const std::exception& ex) {
      captureException("setOperateMode(manual)", ex);
      return false;
    }
  }
#endif
  auto_mode_ = false;
  active_rt_phase_ = "idle";
  binding_detail_ = "manual_mode";
  refreshRuntimeCaches();
  refreshBindingTruth();
  appendLog("setOperateMode(manual) accepted");
  return true;
}

bool SdkRobotFacade::configureRtMainline(const SdkRobotRuntimeConfig& config) {
  rt_config_ = config;
  rt_config_.fc_frame_matrix_m = normalizeFrameMatrixMmToM(config.fc_frame_matrix);
  rt_config_.tcp_frame_matrix_m = normalizeFrameMatrixMmToM(config.tcp_frame_matrix);
  rt_config_.load_com_m = normalizeLoadComMmToM(config.load_com_mm);
  rt_config_.ui_length_unit = "mm";
  rt_config_.sdk_length_unit = "m";
  rt_config_.boundary_normalized = true;
  control_source_exclusive_ = rt_config_.requires_single_control_source;
  nominal_rt_loop_hz_ = 1000;
  const bool config_valid = rt_config_.robot_model == "xmate3" && rt_config_.sdk_robot_class == "xMateRobot" && rt_config_.axis_count == 6;
  configureContactControllersFromRuntimeConfig();
  rt_mainline_configured_ = connected_ && powered_ && auto_mode_ && config_valid && control_source_exclusive_;
  binding_detail_ = rt_mainline_configured_ ? "rt_configured" : "rt_configuration_blocked";
  appendLog("configureRtMainline(robot=" + rt_config_.robot_model + ",class=" + rt_config_.sdk_robot_class + ",axis_count=" + std::to_string(rt_config_.axis_count) + ",rt_network_tolerance=" + std::to_string(rt_config_.rt_network_tolerance_percent) + ")");
  refreshBindingTruth();
  return rt_mainline_configured_;
}

bool SdkRobotFacade::ensureConnected(std::string* reason) {
  if (!connected_) {
    captureFailure("ensureConnected", "controller_not_connected", reason);
    return false;
  }
  return true;
}

bool SdkRobotFacade::ensurePoweredAuto(std::string* reason) {
  if (!ensureConnected(reason)) return false;
  if (!powered_) {
    captureFailure("ensurePoweredAuto", "controller_not_powered", reason);
    return false;
  }
  if (!auto_mode_) {
    captureFailure("ensurePoweredAuto", "auto_mode_required", reason);
    return false;
  }
  return true;
}

bool SdkRobotFacade::ensureNrtMode(std::string* reason) {
  if (!ensurePoweredAuto(reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->setMotionControlMode(rokae::MotionControlMode::NrtCommand, ec);
    if (!applyErrorCode("setMotionControlMode(NrtCommand)", ec, reason)) {
      return false;
    }
    } catch (const std::exception& ex) {
      captureException("setMotionControlMode(NrtCommand)", ex, reason);
      return false;
    }
  }
#endif
  motion_channel_ready_ = true;
  binding_detail_ = "nrt_mode_selected";
  return true;
}

bool SdkRobotFacade::ensureRtMode(std::string* reason) {
  if (!ensurePoweredAuto(reason)) return false;
  if (!rt_mainline_configured_) {
    captureFailure("ensureRtMode", "rt_mainline_not_configured", reason);
    return false;
  }
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->setRtNetworkTolerance(static_cast<unsigned>(std::max(0, rt_config_.rt_network_tolerance_percent)), ec);
    if (!applyErrorCode("setRtNetworkTolerance", ec, reason)) {
      return false;
    }
    robot_->setMotionControlMode(rokae::MotionControlMode::RtCommand, ec);
    if (!applyErrorCode("setMotionControlMode(RtCommand)", ec, reason)) {
      return false;
    }
    } catch (const std::exception& ex) {
      captureException("setMotionControlMode(RtCommand)", ex, reason);
      return false;
    }
  }
#endif
  binding_detail_ = "rt_mode_selected";
  return true;
}

bool SdkRobotFacade::ensureRtController(std::string* reason) {
  if (!ensureRtMode(reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      rt_controller_ = robot_->getRtMotionController().lock();
    if (rt_controller_ == nullptr) {
      captureFailure("getRtMotionController", "rt_controller_unavailable", reason);
      return false;
    }
    return true;
    } catch (const std::exception& ex) {
      captureException("getRtMotionController", ex, reason);
      return false;
    }
  }
#else
#endif
  return true;
}

bool SdkRobotFacade::ensureRtStateStream(const std::vector<std::string>& fields, std::string* reason) {
  if (!ensureRtController(reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    if (rt_state_stream_started_ && fields == rt_state_fields_) {
      return true;
    }
    try {
      if (rt_state_stream_started_) {
        robot_->stopReceiveRobotState();
        rt_state_stream_started_ = false;
      }
      robot_->startReceiveRobotState(std::chrono::milliseconds(1), fields);
      rt_state_stream_started_ = true;
      rt_state_fields_ = fields;
      state_channel_ready_ = true;
      return true;
    } catch (const std::exception& ex) {
      captureException("startReceiveRobotState", ex, reason);
      return false;
    }
  }
#endif
  rt_state_stream_started_ = true;
  rt_state_fields_ = fields;
  state_channel_ready_ = true;
  appendLog("rt_state_stream_contract_shell");
  return true;
}

bool SdkRobotFacade::applyRtConfig(const SdkRobotRuntimeConfig& config, std::string* reason) {
  if (!ensureRtController(reason)) return false;
  rt_config_ = config;
  rt_config_.fc_frame_matrix_m = normalizeFrameMatrixMmToM(config.fc_frame_matrix);
  rt_config_.tcp_frame_matrix_m = normalizeFrameMatrixMmToM(config.tcp_frame_matrix);
  rt_config_.load_com_m = normalizeLoadComMmToM(config.load_com_mm);
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && rt_controller_ != nullptr) {
    try {
      std::error_code ec;
      rokae::Load load(std::max(0.0, config.load_kg),
                       rt_config_.load_com_m,
                       {config.load_inertia[0], config.load_inertia[1], config.load_inertia[2]});
      rt_controller_->setEndEffectorFrame(rt_config_.tcp_frame_matrix_m, ec);
      if (!applyErrorCode("setEndEffectorFrame", ec, reason)) return false;
      rt_controller_->setLoad(load, ec);
      if (!applyErrorCode("setLoad", ec, reason)) return false;
      rt_controller_->setFilterFrequency(config.joint_filter_hz, config.cart_filter_hz, config.torque_filter_hz, ec);
      if (!applyErrorCode("setFilterFrequency", ec, reason)) return false;
      rt_controller_->setCartesianImpedance(config.cartesian_impedance, ec);
      if (!applyErrorCode("setCartesianImpedance", ec, reason)) return false;
      rt_controller_->setCartesianImpedanceDesiredTorque(config.desired_wrench_n, ec);
      if (!applyErrorCode("setCartesianImpedanceDesiredTorque", ec, reason)) return false;
      rt_controller_->setFcCoor(rt_config_.fc_frame_matrix_m, rokae::FrameType::path, ec);
      if (!applyErrorCode("setFcCoor", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("applyRtConfig", ex, reason);
      return false;
    }
  }
#endif
  configureContactControllersFromRuntimeConfig();
  rt_mainline_configured_ = true;
  binding_detail_ = "rt_config_applied";
  return true;
}

bool SdkRobotFacade::executeMoveAbsJ(const std::vector<double>& joints_rad, int speed_mm_s, int zone_mm, std::string* reason) {
  if (!ensureNrtMode(reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->setDefaultSpeed(speed_mm_s, ec);
      if (!applyErrorCode("setDefaultSpeed", ec, reason)) return false;
      robot_->setDefaultZone(zone_mm, ec);
      if (!applyErrorCode("setDefaultZone", ec, reason)) return false;
      robot_->moveReset(ec);
      if (!applyErrorCode("moveReset", ec, reason)) return false;
      robot_->moveAppend({rokae::MoveAbsJCommand(rokae::JointPosition(joints_rad))}, active_nrt_profile_, ec);
      if (!applyErrorCode("moveAppend(MoveAbsJ)", ec, reason)) return false;
      robot_->moveStart(ec);
      if (!applyErrorCode("moveStart", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("executeMoveAbsJ", ex, reason);
      return false;
    }
  }
#endif
  ++command_sequence_;
  registers_["spine.command.sequence"] = command_sequence_;
  refreshRuntimeCaches();
  return true;
}


bool SdkRobotFacade::executeMoveL(const std::vector<double>& tcp_xyzabc_m_rad, int speed_mm_s, int zone_mm, std::string* reason) {
  if (!ensureNrtMode(reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->setDefaultSpeed(speed_mm_s, ec);
      if (!applyErrorCode("setDefaultSpeed", ec, reason)) return false;
      robot_->setDefaultZone(zone_mm, ec);
      if (!applyErrorCode("setDefaultZone", ec, reason)) return false;
      robot_->moveReset(ec);
      if (!applyErrorCode("moveReset", ec, reason)) return false;
      rokae::CartesianPosition target(toArray6(tcp_xyzabc_m_rad));
      robot_->moveAppend({rokae::MoveLCommand(target)}, active_nrt_profile_, ec);
      if (!applyErrorCode("moveAppend(MoveL)", ec, reason)) return false;
      robot_->moveStart(ec);
      if (!applyErrorCode("moveStart", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("executeMoveL", ex, reason);
      return false;
    }
  }
#endif
  ++command_sequence_;
  registers_["spine.command.sequence"] = command_sequence_;
  refreshRuntimeCaches();
  return true;
}


bool SdkRobotFacade::stopNrt(std::string* reason) {
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->stop(ec);
      if (!applyErrorCode("stop", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("stop", ex, reason);
      return false;
    }
  }
#endif
  refreshRuntimeCaches();
  appendLog("stop() accepted");
  return true;
}


bool SdkRobotFacade::stopRt(std::string* reason) {
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      if (rt_controller_ != nullptr) {
        if (rt_loop_active_) {
          rt_controller_->stopLoop();
        }
        rt_controller_->stopMove();
      }
      if (rt_state_stream_started_) {
        robot_->stopReceiveRobotState();
      }
    } catch (const std::exception& ex) {
      captureException("stopRt", ex, reason);
      return false;
    }
  }
#endif
  rt_state_stream_started_ = false;
  rt_loop_active_ = false;
  active_rt_phase_ = "idle";
  setRtPhaseCode("idle");
  refreshRuntimeCaches();
  return true;
}


bool SdkRobotFacade::runRlProject(const std::string& project, const std::string& task, std::string* reason) {
  if (!ensurePoweredAuto(reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->loadProject(project, {task}, ec);
    if (!applyErrorCode("loadProject", ec, reason)) return false;
    robot_->ppToMain(ec);
    if (!applyErrorCode("ppToMain", ec, reason)) return false;
    robot_->runProject(ec);
    if (!applyErrorCode("runProject", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("runRlProject", ex, reason);
      return false;
    }
  }
#endif
  rl_status_.loaded_project = project;
  rl_status_.loaded_task = task;
  rl_status_.running = true;
  appendLog("runRlProject(project=" + project + ",task=" + task + ") accepted");
  return true;
}

bool SdkRobotFacade::pauseRlProject(std::string* reason) {
  if (!ensurePoweredAuto(reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->pauseProject(ec);
    if (!applyErrorCode("pauseProject", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("pauseRlProject", ex, reason);
      return false;
    }
  }
#endif
  rl_status_.running = false;
  appendLog("pauseRlProject accepted");
  return true;
}

bool SdkRobotFacade::enableDrag(const std::string& space, const std::string& type, std::string* reason) {
  if (!ensureConnected(reason)) return false;
  if (powered_ || auto_mode_) {
    captureFailure("enableDrag", "manual_mode_and_power_off_required", reason);
    return false;
  }
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      const auto drag_space = (space == "joint") ? rokae::DragParameter::Space::jointSpace : rokae::DragParameter::Space::cartesianSpace;
      const auto drag_type = (type == "translation_only") ? rokae::DragParameter::Type::translationOnly :
                             ((type == "rotation_only") ? rokae::DragParameter::Type::rotationOnly : rokae::DragParameter::Type::freely);
      robot_->enableDrag(drag_space, drag_type, ec);
      if (!applyErrorCode("enableDrag", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("enableDrag", ex, reason);
      return false;
    }
  }
#endif
  drag_state_ = {true, space, type};
  appendLog("enableDrag(space=" + space + ",type=" + type + ") accepted");
  return true;
}


bool SdkRobotFacade::disableDrag(std::string* reason) {
  if (!ensureConnected(reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->disableDrag(ec);
      if (!applyErrorCode("disableDrag", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("disableDrag", ex, reason);
      return false;
    }
  }
#endif
  drag_state_.enabled = false;
  appendLog("disableDrag accepted");
  return true;
}


bool SdkRobotFacade::replayPath(const std::string& name, double rate, std::string* reason) {
  if (!ensurePoweredAuto(reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->replayPath(name, rate, ec);
      if (!applyErrorCode("replayPath", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("replayPath", ex, reason);
      return false;
    }
  }
#endif
  appendLog("replayPath(name=" + name + ",rate=" + std::to_string(rate) + ") accepted");
  return true;
}


bool SdkRobotFacade::startRecordPath(int duration_s, std::string* reason) {
  if (!ensureConnected(reason)) return false;
  if (powered_ || auto_mode_) {
    captureFailure("startRecordPath", "manual_mode_and_power_off_required", reason);
    return false;
  }
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->startRecordPath(duration_s, ec);
      if (!applyErrorCode("startRecordPath", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("startRecordPath", ex, reason);
      return false;
    }
  }
#endif
  appendLog("startRecordPath(duration_s=" + std::to_string(duration_s) + ") accepted");
  return true;
}


bool SdkRobotFacade::stopRecordPath(std::string* reason) {
  if (!ensureConnected(reason)) return false;
  if (powered_ || auto_mode_) {
    captureFailure("stopRecordPath", "manual_mode_and_power_off_required", reason);
    return false;
  }
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->stopRecordPath(ec);
      if (!applyErrorCode("stopRecordPath", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("stopRecordPath", ex, reason);
      return false;
    }
  }
#endif
  appendLog("stopRecordPath accepted");
  return true;
}


bool SdkRobotFacade::cancelRecordPath(std::string* reason) {
  if (!ensureConnected(reason)) return false;
  if (powered_ || auto_mode_) {
    captureFailure("cancelRecordPath", "manual_mode_and_power_off_required", reason);
    return false;
  }
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->cancelRecordPath(ec);
      if (!applyErrorCode("cancelRecordPath", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("cancelRecordPath", ex, reason);
      return false;
    }
  }
#endif
  appendLog("cancelRecordPath accepted");
  return true;
}


bool SdkRobotFacade::saveRecordPath(const std::string& name, const std::string& save_as, std::string* reason) {
  if (!ensureConnected(reason)) return false;
  if (powered_ || auto_mode_) {
    captureFailure("saveRecordPath", "manual_mode_and_power_off_required", reason);
    return false;
  }
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::error_code ec;
      robot_->saveRecordPath(name, ec, save_as);
      if (!applyErrorCode("saveRecordPath", ec, reason)) return false;
    } catch (const std::exception& ex) {
      captureException("saveRecordPath", ex, reason);
      return false;
    }
  }
#endif
  appendLog("saveRecordPath(name=" + name + ",save_as=" + save_as + ") accepted");
  return true;
}


bool SdkRobotFacade::beginNrtProfile(const std::string& profile, const std::string& sdk_command, bool requires_auto_mode, std::string* reason) {
  if (requires_auto_mode ? !ensurePoweredAuto(reason) : !ensureConnected(reason)) {
    binding_detail_ = "nrt_preconditions_failed";
    refreshBindingTruth();
    return false;
  }
  if (!control_source_exclusive_) {
    captureFailure("beginNrtProfile", "single_control_source_required", reason);
    return false;
  }
  active_nrt_profile_ = profile;
  binding_detail_ = "nrt_profile_ready:" + sdk_command;
  appendLog("beginNrtProfile(profile=" + profile + ",command=" + sdk_command + ")");
  refreshBindingTruth();
  return true;
}

void SdkRobotFacade::finishNrtProfile(const std::string& profile, bool success, const std::string& detail) {
  if (active_nrt_profile_ == profile) active_nrt_profile_ = "idle";
  binding_detail_ = success ? "nrt_profile_finished" : "nrt_profile_failed";
  appendLog("finishNrtProfile(profile=" + profile + ",success=" + std::string(success ? "true" : "false") + (detail.empty() ? "" : ",detail=" + detail) + ")");
  refreshBindingTruth();
}

std::array<double, 16> SdkRobotFacade::defaultPoseMatrix() {
  return identityPoseMatrix();
}

double SdkRobotFacade::measuredNormalForce(const RtObservedState& state) const {
  return normal_force_estimator_.lastEstimate().estimated_force_n;
}

void SdkRobotFacade::configureContactControllersFromRuntimeConfig() {
  contact_control_contract_ = buildContactControlContract(rt_config_);
  normal_force_estimator_.configure(contact_control_contract_.force_estimator);
  normal_admittance_controller_.configure(contact_control_contract_.seek_contact_admittance);
  tangential_scan_controller_.configure(contact_control_contract_.tangential_scan);
  orientation_trim_controller_.configure(contact_control_contract_.orientation_trim);
  rt_config_.contact_control.mode = "normal_axis_admittance";
  rt_config_.contact_control.virtual_mass = contact_control_contract_.seek_contact_admittance.virtual_mass;
  rt_config_.contact_control.virtual_damping = contact_control_contract_.seek_contact_admittance.virtual_damping;
  rt_config_.contact_control.virtual_stiffness = contact_control_contract_.seek_contact_admittance.virtual_stiffness;
  rt_config_.contact_control.force_deadband_n = contact_control_contract_.seek_contact_admittance.force_deadband_n;
  rt_config_.contact_control.max_normal_step_mm = contact_control_contract_.seek_contact_admittance.max_step_mm;
  rt_config_.contact_control.max_normal_velocity_mm_s = contact_control_contract_.seek_contact_admittance.max_velocity_mm_s;
  rt_config_.contact_control.max_normal_acc_mm_s2 = contact_control_contract_.seek_contact_admittance.max_acceleration_mm_s2;
  rt_config_.contact_control.max_normal_travel_mm = contact_control_contract_.seek_contact_admittance.max_displacement_mm;
  rt_config_.contact_control.anti_windup_limit_n = contact_control_contract_.seek_contact_admittance.integrator_limit_n;
  rt_config_.contact_control.integrator_leak = contact_control_contract_.pause_hold_admittance.integrator_leak;
  rt_config_.force_estimator.preferred_source = contact_control_contract_.force_estimator.preferred_source;
  rt_config_.force_estimator.pressure_weight = contact_control_contract_.force_estimator.pressure_weight;
  rt_config_.force_estimator.wrench_weight = contact_control_contract_.force_estimator.wrench_weight;
  rt_config_.force_estimator.stale_timeout_ms = static_cast<int>(contact_control_contract_.force_estimator.stale_timeout_ms);
  rt_config_.force_estimator.timeout_ms = static_cast<int>(contact_control_contract_.force_estimator.timeout_ms);
  rt_config_.force_estimator.auto_bias_zero = contact_control_contract_.force_estimator.auto_bias_zero;
  rt_config_.force_estimator.min_confidence = contact_control_contract_.force_estimator.min_confidence;
  rt_config_.orientation_trim.gain = contact_control_contract_.orientation_trim.gain;
  rt_config_.orientation_trim.max_trim_deg = contact_control_contract_.orientation_trim.max_trim_deg;
  rt_config_.orientation_trim.lowpass_hz = contact_control_contract_.orientation_trim.lowpass_hz;
}

double SdkRobotFacade::measuredNormalVelocity(const RtObservedState& state) const {
  return state.normal_axis_velocity_m_s;
}

void SdkRobotFacade::clampCommandPose(std::array<double, 16>& pose, const std::array<double, 16>& anchor) {
  const double dt = 1.0 / std::max(1, nominal_rt_loop_hz_);
  const double max_step_m = mmToM(std::max(0.01, rt_phase_contract_.common.max_cart_step_mm));
  const double max_vel_m_s = mmToM(std::max(0.01, rt_phase_contract_.common.max_cart_vel_mm_s));
  const double max_acc_m_s2 = mmToM(std::max(1.0, rt_phase_contract_.common.max_cart_acc_mm_s2));
  const double prev_vel_m_s = rt_phase_loop_state_.last_command_step_m > 0.0 ? (rt_phase_loop_state_.last_command_step_m / dt) : 0.0;
  const double accel_limited_vel_m_s = std::min(max_vel_m_s, prev_vel_m_s + max_acc_m_s2 * dt);
  const double allowed_m = std::min(max_step_m, std::max(mmToM(0.01), accel_limited_vel_m_s * dt));
  double max_applied_delta_m = 0.0;
  for (const auto idx : kTranslationIndices) {
    const double delta = pose[idx] - anchor[idx];
    if (!std::isfinite(delta)) {
      pose[idx] = anchor[idx];
      continue;
    }
    const double clamped = clampSigned(delta, allowed_m);
    pose[idx] = anchor[idx] + clamped;
    max_applied_delta_m = std::max(max_applied_delta_m, std::abs(clamped));
  }
  rt_phase_loop_state_.last_command_step_m = max_applied_delta_m;
}

void SdkRobotFacade::clampPoseTrim(std::array<double, 16>& pose, const std::array<double, 16>& anchor) const {
  (void)anchor;
  for (auto& item : pose) {
    if (!std::isfinite(item)) item = 0.0;
  }
  pose[15] = 1.0;
}

void SdkRobotFacade::applyLocalPitchTrim(std::array<double, 16>& pose, const std::array<double, 16>& anchor, double trim_rad) const {
  const double c = std::cos(trim_rad);
  const double s = std::sin(trim_rad);
  pose = anchor;
  pose[0] = anchor[0] * c - anchor[2] * s;
  pose[1] = anchor[1];
  pose[2] = anchor[0] * s + anchor[2] * c;
  pose[4] = anchor[4] * c - anchor[6] * s;
  pose[5] = anchor[5];
  pose[6] = anchor[4] * s + anchor[6] * c;
  pose[8] = anchor[8] * c - anchor[10] * s;
  pose[9] = anchor[9];
  pose[10] = anchor[8] * s + anchor[10] * c;
  pose[3] = anchor[3];
  pose[7] = anchor[7];
  pose[11] = anchor[11];
  pose[12] = 0.0; pose[13] = 0.0; pose[14] = 0.0; pose[15] = 1.0;
}

void SdkRobotFacade::resetRtPhaseIntegrators() {
  rt_phase_loop_state_ = {};
  rt_phase_loop_state_.contact_axis_index = translationIndexForAxis(2);
  rt_phase_loop_state_.scan_axis_index = translationIndexForAxis(0);
  rt_phase_loop_state_.lateral_axis_index = translationIndexForAxis(1);
  rt_phase_loop_state_.contact_direction_sign = (rt_config_.desired_wrench_n[2] < 0.0) ? -1.0 : 1.0;
  normal_force_estimator_.reset();
  normal_admittance_controller_.reset();
  tangential_scan_controller_.reset();
  orientation_trim_controller_.reset();
  last_phase_telemetry_ = {};
}

void SdkRobotFacade::setRtPhaseControlContract(const RtPhaseControlContract& contract) {
  rt_phase_contract_ = contract;
  configureContactControllersFromRuntimeConfig();
}

bool SdkRobotFacade::validateRtControlContract(std::string* reason) const {
  if (rt_phase_contract_.common.max_cart_step_mm <= 0.0 ||
      rt_phase_contract_.common.max_cart_vel_mm_s <= 0.0 ||
      rt_phase_contract_.common.max_cart_acc_mm_s2 <= 0.0 ||
      rt_phase_contract_.common.max_pose_trim_deg <= 0.0 ||
      rt_phase_contract_.common.stale_state_timeout_ms <= 0.0 ||
      rt_phase_contract_.seek_contact.establish_cycles < 1 ||
      rt_phase_contract_.scan_follow.tangent_speed_min_mm_s <= 0.0 ||
      rt_phase_contract_.scan_follow.tangent_speed_max_mm_s < rt_phase_contract_.scan_follow.tangent_speed_min_mm_s ||
      rt_phase_contract_.controlled_retract.release_cycles < 1 ||
      rt_phase_contract_.controlled_retract.timeout_ms <= 0.0 ||
      rt_phase_contract_.controlled_retract.release_force_n > rt_phase_contract_.seek_contact.force_target_n) {
    if (reason != nullptr) {
      *reason = "invalid_rt_phase_control_contract";
    }
    return false;
  }
  return validateContactControlContract(contact_control_contract_, reason);
}

bool SdkRobotFacade::populateObservedState(RtObservedState& out, std::string* reason) {
  out = {};
  out.tcp_pose = postureVectorToMatrix(tcp_pose_);
  for (std::size_t idx = 0; idx < std::min<std::size_t>(6, joint_pos_.size()); ++idx) out.joint_pos[idx] = joint_pos_[idx];
  for (std::size_t idx = 0; idx < std::min<std::size_t>(6, joint_vel_.size()); ++idx) out.joint_vel[idx] = joint_vel_[idx];
  for (std::size_t idx = 0; idx < std::min<std::size_t>(6, joint_torque_.size()); ++idx) out.joint_torque[idx] = joint_torque_[idx];
  const double now_s = std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
  out.monotonic_time_s = now_s;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::array<double, 16> tcp_pose{};
      std::array<double, 6> joint_pos{};
      std::array<double, 6> joint_vel{};
      std::array<double, 6> joint_tau{};
      std::array<double, 6> ext_tau{};
      const bool got_pose = (robot_->getStateData(rokae::RtSupportedFields::tcpPose_m, tcp_pose) == 0);
      const bool got_joints = (robot_->getStateData(rokae::RtSupportedFields::jointPos_m, joint_pos) == 0);
      const bool got_joint_vel = (robot_->getStateData(rokae::RtSupportedFields::jointVel_m, joint_vel) == 0);
      const bool got_tau = (robot_->getStateData(rokae::RtSupportedFields::tau_m, joint_tau) == 0);
      const bool got_ext = (robot_->getStateData(rokae::RtSupportedFields::tauExt_inBase, ext_tau) == 0);
      if (got_pose) out.tcp_pose = tcp_pose;
      if (got_joints) out.joint_pos = joint_pos;
      if (got_joint_vel) out.joint_vel = joint_vel;
      if (got_tau) out.joint_torque = joint_tau;
      if (got_ext) out.external_wrench = ext_tau;
      out.valid = got_pose && got_joints;
      if (out.valid) {
        last_rt_state_sample_time_s_ = now_s;
        const std::size_t axis = std::min<std::size_t>(11, rt_phase_loop_state_.contact_axis_index);
        if (last_rt_observed_pose_initialized_ && now_s > last_rt_observed_time_s_) {
          const double dt = now_s - last_rt_observed_time_s_;
          out.normal_axis_velocity_m_s = (out.tcp_pose[axis] - last_rt_observed_pose_[axis]) / std::max(1e-6, dt);
        }
        last_rt_observed_pose_ = out.tcp_pose;
        last_rt_observed_pose_initialized_ = true;
        last_rt_observed_time_s_ = now_s;
      }
    } catch (const std::exception& ex) {
      if (reason != nullptr) *reason = ex.what();
      out.valid = false;
    }
    out.age_ms = last_rt_state_sample_time_s_ > 0.0 ? (now_s - last_rt_state_sample_time_s_) * 1000.0 : rt_phase_contract_.common.stale_state_timeout_ms + 1.0;
    out.pressure_force_n = ai_.count("board0_port0") ? ai_.at("board0_port0") : 0.0;
    out.pressure_age_ms = out.age_ms;
    out.pressure_valid = ai_.count("board0_port0") > 0;
    out.stale = out.age_ms > rt_phase_contract_.common.stale_state_timeout_ms;
    return out.valid;
  }
#endif
  out.valid = connected_;
  out.age_ms = 0.0;
  out.normal_axis_velocity_m_s = 0.0;
  out.pressure_force_n = ai_.count("board0_port0") ? ai_.at("board0_port0") : 0.0;
  out.pressure_age_ms = 0.0;
  out.pressure_valid = ai_.count("board0_port0") > 0;
  out.stale = false;
  return out.valid;
}

RtPhaseStepResult SdkRobotFacade::stepSeekContact(const RtObservedState& state) {
  RtPhaseStepResult result{};
  result.telemetry.phase_name = "seek_contact";
  if (!state.valid || state.stale) {
    result.verdict = RtPhaseVerdict::StaleState;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  auto& loop = rt_phase_loop_state_;
  if (!loop.anchor_initialized) {
    loop.anchor_pose = state.tcp_pose;
    loop.hold_reference_pose = state.tcp_pose;
    loop.anchor_initialized = true;
  }
  const double dt = 1.0 / std::max(1, nominal_rt_loop_hz_);
  loop.phase_time_s += dt;
  normal_admittance_controller_.configure(contact_control_contract_.seek_contact_admittance);
  NormalForceEstimatorInput input{};
  const std::size_t axis = std::min<std::size_t>(5, loop.contact_axis_index == translationIndexForAxis(0) ? 0 : (loop.contact_axis_index == translationIndexForAxis(1) ? 1 : 2));
  input.pressure_force_n = state.pressure_force_n;
  input.pressure_valid = state.pressure_valid;
  input.pressure_age_ms = state.pressure_age_ms;
  input.wrench_force_n = state.external_wrench[axis];
  input.wrench_valid = true;
  input.wrench_age_ms = state.age_ms;
  input.contact_direction_sign = loop.contact_direction_sign;
  const auto estimate = normal_force_estimator_.estimate(input);
  if (!estimate.valid) {
    result.verdict = RtPhaseVerdict::StaleState;
    result.telemetry.normal_force_source = estimate.source;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  const auto command = normal_admittance_controller_.step(rt_phase_contract_.seek_contact.force_target_n, estimate.estimated_force_n, dt);
  const double velocity = measuredNormalVelocity(state);
  const double error = command.state.force_error_n;
  loop.last_normal_error_n = error;
  if (std::abs(error) <= rt_phase_contract_.seek_contact.force_tolerance_n &&
      std::abs(velocity) <= mmToM(rt_phase_contract_.seek_contact.quiet_velocity_mm_s)) {
    ++loop.stable_cycles;
  } else {
    loop.stable_cycles = 0;
  }
  result.telemetry.normal_force_error_n = error;
  result.telemetry.estimated_normal_force_n = estimate.estimated_force_n;
  result.telemetry.normal_force_confidence = estimate.confidence;
  result.telemetry.normal_force_source = estimate.source;
  result.telemetry.admittance_displacement_m = command.state.x_m;
  result.telemetry.admittance_velocity_m_s = command.state.v_m_s;
  result.telemetry.admittance_saturated = command.state.saturated;
  result.telemetry.stable_cycles = loop.stable_cycles;
  if (loop.stable_cycles >= static_cast<unsigned>(std::max(1, rt_phase_contract_.seek_contact.establish_cycles))) {
    result.command_pose = state.tcp_pose;
    result.verdict = RtPhaseVerdict::PhaseCompleted;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  loop.seek_progress_m = std::clamp(loop.seek_progress_m + command.delta_normal_m, -mmToM(rt_phase_contract_.seek_contact.max_travel_mm), mmToM(rt_phase_contract_.seek_contact.max_travel_mm));
  result.command_pose = loop.anchor_pose;
  result.command_pose[loop.contact_axis_index] = loop.anchor_pose[loop.contact_axis_index] + loop.contact_direction_sign * loop.seek_progress_m;
  result.telemetry.tangent_progress_m = loop.seek_progress_m;
  if (std::abs(error) > rt_phase_contract_.common.max_force_error_n) {
    result.verdict = RtPhaseVerdict::ExceededForce;
  }
  last_phase_telemetry_ = result.telemetry;
  return result;
}

RtPhaseStepResult SdkRobotFacade::stepScanFollow(const RtObservedState& state) {
  RtPhaseStepResult result{};
  result.telemetry.phase_name = "scan_follow";
  if (!state.valid || state.stale) {
    result.verdict = RtPhaseVerdict::StaleState;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  auto& loop = rt_phase_loop_state_;
  if (!loop.anchor_initialized) {
    loop.anchor_pose = state.tcp_pose;
    loop.hold_reference_pose = state.tcp_pose;
    loop.anchor_initialized = true;
  }
  const double dt = 1.0 / std::max(1, nominal_rt_loop_hz_);
  loop.phase_time_s += dt;
  normal_admittance_controller_.configure(contact_control_contract_.scan_follow_admittance);
  tangential_scan_controller_.configure(contact_control_contract_.tangential_scan);
  orientation_trim_controller_.configure(contact_control_contract_.orientation_trim);
  const std::size_t axis = std::min<std::size_t>(5, loop.contact_axis_index == translationIndexForAxis(0) ? 0 : (loop.contact_axis_index == translationIndexForAxis(1) ? 1 : 2));
  NormalForceEstimatorInput input{};
  input.pressure_force_n = state.pressure_force_n;
  input.pressure_valid = state.pressure_valid;
  input.pressure_age_ms = state.pressure_age_ms;
  input.wrench_force_n = state.external_wrench[axis];
  input.wrench_valid = true;
  input.wrench_age_ms = state.age_ms;
  input.contact_direction_sign = loop.contact_direction_sign;
  const auto estimate = normal_force_estimator_.estimate(input);
  if (!estimate.valid) {
    result.verdict = RtPhaseVerdict::NeedPauseHold;
    result.telemetry.normal_force_source = estimate.source;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  const auto normal = normal_admittance_controller_.step(rt_phase_contract_.scan_follow.force_target_n, estimate.estimated_force_n, dt);
  const auto tangent = tangential_scan_controller_.advance(rt_config_.scan_speed_mm_s, dt);
  const auto trim = orientation_trim_controller_.step(normal.state.force_error_n / std::max(0.1, rt_phase_contract_.common.max_force_error_n), dt);
  loop.scan_progress_m = tangent.progress_m;
  result.command_pose = loop.anchor_pose;
  result.command_pose[loop.scan_axis_index] = loop.anchor_pose[loop.scan_axis_index] + tangent.progress_m;
  result.command_pose[loop.contact_axis_index] = loop.anchor_pose[loop.contact_axis_index] + loop.contact_direction_sign * normal.state.x_m;
  result.command_pose[loop.lateral_axis_index] = loop.anchor_pose[loop.lateral_axis_index] + tangent.lateral_offset_m;
  const auto trim_anchor_pose = result.command_pose;
  applyLocalPitchTrim(result.command_pose, trim_anchor_pose, trim.trim_rad);
  result.telemetry.normal_force_error_n = normal.state.force_error_n;
  result.telemetry.estimated_normal_force_n = estimate.estimated_force_n;
  result.telemetry.normal_force_confidence = estimate.confidence;
  result.telemetry.normal_force_source = estimate.source;
  result.telemetry.tangent_progress_m = tangent.progress_m;
  result.telemetry.pose_trim_rad = trim.trim_rad;
  result.telemetry.orientation_trim_saturated = trim.saturated;
  result.telemetry.admittance_displacement_m = normal.state.x_m;
  result.telemetry.admittance_velocity_m_s = normal.state.v_m_s;
  result.telemetry.admittance_saturated = normal.state.saturated;
  if (tangent.saturated || tangent.progress_m >= mmToM(rt_phase_contract_.scan_follow.max_travel_mm)) {
    result.finished = true;
    result.verdict = RtPhaseVerdict::PhaseCompleted;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  if (std::abs(normal.state.force_error_n) > rt_phase_contract_.common.max_force_error_n || normal.state.saturated) {
    result.verdict = RtPhaseVerdict::NeedPauseHold;
  }
  last_phase_telemetry_ = result.telemetry;
  return result;
}

RtPhaseStepResult SdkRobotFacade::stepPauseHold(const RtObservedState& state) {
  RtPhaseStepResult result{};
  result.telemetry.phase_name = "pause_hold";
  if (!state.valid || state.stale) {
    result.verdict = RtPhaseVerdict::StaleState;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  auto& loop = rt_phase_loop_state_;
  if (!loop.hold_reference_initialized) {
    loop.hold_reference_pose = state.tcp_pose;
    loop.hold_reference_initialized = true;
  }
  const double dt = 1.0 / std::max(1, nominal_rt_loop_hz_);
  normal_admittance_controller_.configure(contact_control_contract_.pause_hold_admittance);
  const std::size_t axis = std::min<std::size_t>(5, loop.contact_axis_index == translationIndexForAxis(0) ? 0 : (loop.contact_axis_index == translationIndexForAxis(1) ? 1 : 2));
  NormalForceEstimatorInput input{};
  input.pressure_force_n = state.pressure_force_n;
  input.pressure_valid = state.pressure_valid;
  input.pressure_age_ms = state.pressure_age_ms;
  input.wrench_force_n = state.external_wrench[axis];
  input.wrench_valid = true;
  input.wrench_age_ms = state.age_ms;
  input.contact_direction_sign = loop.contact_direction_sign;
  const auto estimate = normal_force_estimator_.estimate(input);
  if (!estimate.valid) {
    result.verdict = RtPhaseVerdict::NeedRetreat;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  const auto command = normal_admittance_controller_.step(rt_phase_contract_.scan_follow.force_target_n, estimate.estimated_force_n, dt);
  result.command_pose = loop.hold_reference_pose;
  result.command_pose[loop.contact_axis_index] = loop.hold_reference_pose[loop.contact_axis_index] + loop.contact_direction_sign * command.state.x_m;
  result.telemetry.normal_force_error_n = command.state.force_error_n;
  result.telemetry.estimated_normal_force_n = estimate.estimated_force_n;
  result.telemetry.normal_force_confidence = estimate.confidence;
  result.telemetry.normal_force_source = estimate.source;
  result.telemetry.admittance_displacement_m = command.state.x_m;
  result.telemetry.admittance_velocity_m_s = command.state.v_m_s;
  result.telemetry.admittance_saturated = command.state.saturated;
  if (std::abs(command.state.force_error_n) > rt_phase_contract_.pause_hold.force_guard_n || command.state.saturated) {
    result.verdict = RtPhaseVerdict::NeedRetreat;
  }
  last_phase_telemetry_ = result.telemetry;
  return result;
}

RtPhaseStepResult SdkRobotFacade::stepControlledRetract(const RtObservedState& state) {
  RtPhaseStepResult result{};
  result.telemetry.phase_name = "controlled_retract";
  if (!state.valid || state.stale) {
    result.verdict = RtPhaseVerdict::StaleState;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  auto& loop = rt_phase_loop_state_;
  if (!loop.anchor_initialized) {
    loop.anchor_pose = state.tcp_pose;
    loop.anchor_initialized = true;
  }
  const double dt = 1.0 / std::max(1, nominal_rt_loop_hz_);
  loop.phase_time_s += dt;
  const std::size_t axis = std::min<std::size_t>(5, loop.contact_axis_index == translationIndexForAxis(0) ? 0 : (loop.contact_axis_index == translationIndexForAxis(1) ? 1 : 2));
  NormalForceEstimatorInput input{};
  input.pressure_force_n = state.pressure_force_n;
  input.pressure_valid = state.pressure_valid;
  input.pressure_age_ms = state.pressure_age_ms;
  input.wrench_force_n = state.external_wrench[axis];
  input.wrench_valid = true;
  input.wrench_age_ms = state.age_ms;
  input.contact_direction_sign = loop.contact_direction_sign;
  const auto estimate = normal_force_estimator_.estimate(input);
  const double target_velocity_mm_s = std::max(0.1, rt_config_.retreat_speed_mm_s);
  loop.retract_accel_mm_s2 = std::min(rt_phase_contract_.common.max_cart_acc_mm_s2,
                                      loop.retract_accel_mm_s2 + rt_phase_contract_.controlled_retract.jerk_limit_mm_s3 * dt);
  loop.retract_velocity_mm_s = std::min(target_velocity_mm_s,
                                        loop.retract_velocity_mm_s + loop.retract_accel_mm_s2 * dt);
  const double retract_step_m = mmToM(loop.retract_velocity_mm_s) * dt;
  const double release_force = std::abs(estimate.estimated_force_n);
  result.command_pose = loop.anchor_pose;
  if (!loop.retract_released) {
    loop.retract_progress_m += retract_step_m;
    result.command_pose[loop.contact_axis_index] = loop.anchor_pose[loop.contact_axis_index] - loop.contact_direction_sign * loop.retract_progress_m;
    if (release_force <= rt_phase_contract_.controlled_retract.release_force_n) {
      ++loop.release_cycles;
    } else {
      loop.release_cycles = 0;
    }
    if (loop.release_cycles >= static_cast<unsigned>(rt_phase_contract_.controlled_retract.release_cycles)) {
      loop.retract_released = true;
    }
    if (loop.retract_progress_m >= mmToM(rt_phase_contract_.controlled_retract.max_travel_mm)) {
      result.finished = true;
      result.verdict = RtPhaseVerdict::ExceededTravel;
      last_phase_telemetry_ = result.telemetry;
      return result;
    }
  } else {
    loop.retract_safe_gap_progress_m += retract_step_m;
    const double total = loop.retract_progress_m + loop.retract_safe_gap_progress_m;
    result.command_pose[loop.contact_axis_index] = loop.anchor_pose[loop.contact_axis_index] - loop.contact_direction_sign * total;
    if (loop.retract_safe_gap_progress_m >= mmToM(rt_phase_contract_.controlled_retract.safe_gap_mm)) {
      result.finished = true;
      result.verdict = RtPhaseVerdict::PhaseCompleted;
      last_phase_telemetry_ = result.telemetry;
      return result;
    }
  }
  result.telemetry.estimated_normal_force_n = estimate.estimated_force_n;
  result.telemetry.normal_force_confidence = estimate.confidence;
  result.telemetry.normal_force_source = estimate.source;
  result.telemetry.retract_progress_m = loop.retract_progress_m + loop.retract_safe_gap_progress_m;
  if (loop.phase_time_s * 1000.0 >= rt_phase_contract_.controlled_retract.timeout_ms) {
    result.finished = true;
    result.verdict = RtPhaseVerdict::NeedFaultStop;
  }
  last_phase_telemetry_ = result.telemetry;
  return result;
}

bool SdkRobotFacade::beginRtMainline(const std::string& phase, int nominal_loop_hz, std::string* reason) {
  const int phase_loop_hz = nominal_loop_hz > 0 ? nominal_loop_hz : nominal_rt_loop_hz_;
  if (!ensurePoweredAuto(reason)) return false;
  if (!ensureRtController(reason)) return false;
  rt_phase_contract_.common.max_cart_step_mm = rt_config_.rt_max_cart_step_mm;
  rt_phase_contract_.common.max_cart_vel_mm_s = rt_config_.rt_max_cart_vel_mm_s;
  rt_phase_contract_.common.max_cart_acc_mm_s2 = rt_config_.rt_max_cart_acc_mm_s2;
  rt_phase_contract_.common.max_pose_trim_deg = rt_config_.rt_max_pose_trim_deg;
  rt_phase_contract_.common.stale_state_timeout_ms = rt_config_.rt_stale_state_timeout_ms;
  rt_phase_contract_.common.phase_transition_debounce_cycles = rt_config_.rt_phase_transition_debounce_cycles;
  rt_phase_contract_.common.max_force_error_n = rt_config_.rt_max_force_error_n;
  rt_phase_contract_.common.max_integrator_n = rt_config_.rt_integrator_limit_n;
  rt_phase_contract_.seek_contact.force_target_n = rt_config_.contact_force_target_n;
  rt_phase_contract_.seek_contact.force_tolerance_n = rt_config_.contact_force_tolerance_n;
  rt_phase_contract_.seek_contact.establish_cycles = rt_config_.contact_establish_cycles;
  rt_phase_contract_.seek_contact.admittance_gain = rt_config_.normal_admittance_gain;
  rt_phase_contract_.seek_contact.damping_gain = rt_config_.normal_damping_gain;
  rt_phase_contract_.seek_contact.max_step_mm = rt_config_.seek_contact_max_step_mm;
  rt_phase_contract_.seek_contact.max_travel_mm = rt_config_.seek_contact_max_travel_mm;
  rt_phase_contract_.seek_contact.quiet_velocity_mm_s = rt_config_.normal_velocity_quiet_threshold_mm_s;
  rt_phase_contract_.scan_follow.force_target_n = rt_config_.scan_force_target_n;
  rt_phase_contract_.scan_follow.force_tolerance_n = rt_config_.scan_force_tolerance_n;
  rt_phase_contract_.scan_follow.normal_pi_kp = rt_config_.scan_normal_pi_kp;
  rt_phase_contract_.scan_follow.normal_pi_ki = rt_config_.scan_normal_pi_ki;
  rt_phase_contract_.scan_follow.tangent_speed_min_mm_s = rt_config_.scan_tangent_speed_min_mm_s;
  rt_phase_contract_.scan_follow.tangent_speed_max_mm_s = rt_config_.scan_tangent_speed_max_mm_s;
  rt_phase_contract_.scan_follow.pose_trim_gain = rt_config_.scan_pose_trim_gain;
  rt_phase_contract_.scan_follow.enable_lateral_modulation = rt_config_.scan_follow_enable_lateral_modulation;
  rt_phase_contract_.scan_follow.max_travel_mm = rt_config_.scan_follow_max_travel_mm;
  rt_phase_contract_.scan_follow.lateral_amplitude_mm = rt_config_.scan_follow_lateral_amplitude_mm;
  rt_phase_contract_.scan_follow.modulation_frequency_hz = rt_config_.scan_follow_frequency_hz;
  rt_phase_contract_.pause_hold.position_guard_mm = rt_config_.pause_hold_position_guard_mm;
  rt_phase_contract_.pause_hold.force_guard_n = rt_config_.pause_hold_force_guard_n;
  rt_phase_contract_.pause_hold.drift_kp = rt_config_.pause_hold_drift_kp;
  rt_phase_contract_.pause_hold.drift_ki = rt_config_.pause_hold_drift_ki;
  rt_phase_contract_.pause_hold.integrator_leak = rt_config_.pause_hold_integrator_leak;
  rt_phase_contract_.controlled_retract.release_force_n = rt_config_.retract_release_force_n;
  rt_phase_contract_.controlled_retract.release_cycles = rt_config_.retract_release_cycles;
  rt_phase_contract_.controlled_retract.safe_gap_mm = rt_config_.retract_safe_gap_mm;
  rt_phase_contract_.controlled_retract.max_travel_mm = rt_config_.retract_max_travel_mm;
  rt_phase_contract_.controlled_retract.jerk_limit_mm_s3 = rt_config_.retract_jerk_limit_mm_s3;
  rt_phase_contract_.controlled_retract.timeout_ms = rt_config_.retract_timeout_ms;
  rt_phase_contract_.controlled_retract.retract_travel_mm = rt_config_.retract_travel_mm;
  configureContactControllersFromRuntimeConfig();
  if (!validateRtControlContract(reason)) return false;
  std::vector<std::string> rt_fields = {"q_m", "dq_m", "tau_m", "pos_m", "tau_ext_base"};
  if (!ensureRtStateStream(rt_fields, reason)) return false;
  if (!applyRtConfig(rt_config_, reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && rt_controller_ != nullptr) {
    try {
      if (rt_loop_active_) {
        try { rt_controller_->stopLoop(); } catch (...) {}
        try { rt_controller_->stopMove(); } catch (...) {}
        rt_loop_active_ = false;
      }
      auto phase_impedance = rt_config_.cartesian_impedance;
      auto phase_wrench = rt_config_.desired_wrench_n;
      if (phase == "seek_contact") {
        phase_impedance[2] = std::min(phase_impedance[2], 800.0);
      } else if (phase == "pause_hold" || phase == "controlled_retract") {
        phase_wrench = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
      }
      std::error_code phase_ec;
      rt_controller_->setCartesianImpedance(phase_impedance, phase_ec);
      if (!applyErrorCode("setCartesianImpedance(phase override)", phase_ec, reason)) return false;
      rt_controller_->setCartesianImpedanceDesiredTorque(phase_wrench, phase_ec);
      if (!applyErrorCode("setCartesianImpedanceDesiredTorque(phase override)", phase_ec, reason)) return false;
      resetRtPhaseIntegrators();
      active_rt_phase_ = phase;
      setRtPhaseCode(phase);
      rt_controller_->startMove(rokae::RtControllerMode::cartesianImpedance);
      auto phase_callback = [this, phase]() mutable {
        RtObservedState observed{};
        populateObservedState(observed, nullptr);
        RtPhaseStepResult result{};
        if (active_rt_phase_ == "seek_contact") {
          result = stepSeekContact(observed);
        } else if (active_rt_phase_ == "scan_follow") {
          result = stepScanFollow(observed);
        } else if (active_rt_phase_ == "pause_hold") {
          result = stepPauseHold(observed);
        } else if (active_rt_phase_ == "controlled_retract") {
          result = stepControlledRetract(observed);
        } else {
          result.command_pose = observed.valid ? observed.tcp_pose : defaultPoseMatrix();
          result.finished = true;
          result.verdict = RtPhaseVerdict::PhaseCompleted;
        }
        if (result.verdict != RtPhaseVerdict::Continue &&
            result.verdict != RtPhaseVerdict::PhaseCompleted &&
            result.verdict != RtPhaseVerdict::StaleState) {
          if (rt_phase_loop_state_.pending_transition_verdict == result.verdict) {
            ++rt_phase_loop_state_.pending_transition_cycles;
          } else {
            rt_phase_loop_state_.pending_transition_verdict = result.verdict;
            rt_phase_loop_state_.pending_transition_cycles = 1;
          }
          if (rt_phase_loop_state_.pending_transition_cycles < static_cast<unsigned>(std::max(1, rt_phase_contract_.common.phase_transition_debounce_cycles))) {
            result.verdict = RtPhaseVerdict::Continue;
          } else {
            rt_phase_loop_state_.pending_transition_verdict = RtPhaseVerdict::Continue;
            rt_phase_loop_state_.pending_transition_cycles = 0;
          }
        } else {
          rt_phase_loop_state_.pending_transition_verdict = RtPhaseVerdict::Continue;
          rt_phase_loop_state_.pending_transition_cycles = 0;
        }
        last_phase_telemetry_ = result.telemetry;
        rokae::CartesianPosition output{};
        if (result.command_pose == std::array<double, 16>{}) {
          result.command_pose = observed.valid ? observed.tcp_pose : defaultPoseMatrix();
        }
        clampCommandPose(result.command_pose, observed.valid ? observed.tcp_pose : defaultPoseMatrix());
        clampPoseTrim(result.command_pose, observed.valid ? observed.tcp_pose : defaultPoseMatrix());
        output.pos = result.command_pose;
        switch (result.verdict) {
          case RtPhaseVerdict::Continue:
            break;
          case RtPhaseVerdict::PhaseCompleted:
            output.setFinished();
            rt_loop_active_ = false;
            active_rt_phase_ = "idle";
            setRtPhaseCode("idle");
            break;
          case RtPhaseVerdict::NeedPauseHold:
            active_rt_phase_ = "pause_hold";
            resetRtPhaseIntegrators();
            setRtPhaseCode("pause_hold");
            break;
          case RtPhaseVerdict::NeedRetreat:
            active_rt_phase_ = "controlled_retract";
            resetRtPhaseIntegrators();
            setRtPhaseCode("controlled_retract");
            break;
          case RtPhaseVerdict::StaleState:
          case RtPhaseVerdict::NeedFaultStop:
          case RtPhaseVerdict::ExceededTravel:
          case RtPhaseVerdict::ExceededForce:
          case RtPhaseVerdict::InstabilityDetected:
            output.setFinished();
            rt_loop_active_ = false;
            active_rt_phase_ = "idle";
            binding_detail_ = "rt_fault_verdict";
            setRtPhaseCode("idle");
            break;
        }
        if (result.finished) {
          output.setFinished();
        }
        return output;
      };
      rt_controller_->setControlLoop<rokae::CartesianPosition>(phase_callback, 0, true);
      rt_controller_->startLoop(false);
      rt_loop_active_ = true;
    } catch (const std::exception& ex) {
      captureException("startMove(cartesianImpedance)", ex, reason);
      return false;
    }
  }
#endif
  active_rt_phase_ = phase;
  nominal_rt_loop_hz_ = phase_loop_hz;
  ++command_sequence_;
  registers_["spine.command.sequence"] = command_sequence_;
  setRtPhaseCode(phase);
  binding_detail_ = live_binding_established_ ? "rt_live_active" : "rt_contract_active";
  appendLog("beginRtMainline(phase=" + phase + ",nominal_loop_hz=" + std::to_string(nominal_rt_loop_hz_) + ")");
  refreshBindingTruth();
  return true;
}

void SdkRobotFacade::updateRtPhase(const std::string& phase, const std::string& detail) {
  active_rt_phase_ = phase;
  setRtPhaseCode(phase);
  appendLog("updateRtPhase(phase=" + phase + (detail.empty() ? "" : ",detail=" + detail) + ")");
}

void SdkRobotFacade::finishRtMainline(const std::string& phase, const std::string& detail) {
  std::string ignored;
  stopRt(&ignored);
  if (active_rt_phase_ == phase) active_rt_phase_ = "idle";
  binding_detail_ = "rt_finished";
  appendLog("finishRtMainline(phase=" + phase + (detail.empty() ? "" : ",detail=" + detail) + ")");
  refreshBindingTruth();
}

std::vector<double> SdkRobotFacade::zeroVector(std::size_t count) {
  return std::vector<double>(count, 0.0);
}

void SdkRobotFacade::appendLog(const std::string& message) {
  configuration_log_.push_back(message);
  controller_logs_.insert(controller_logs_.begin(), message);
  if (controller_logs_.size() > 40) controller_logs_.resize(40);
}

void SdkRobotFacade::refreshStateVectors(std::size_t axis_count) {
  joint_pos_ = zeroVector(axis_count);
  joint_vel_ = zeroVector(axis_count);
  joint_torque_ = zeroVector(axis_count);
}

void SdkRobotFacade::refreshInventoryForAxisCount(std::size_t axis_count) {
  path_library_.clear();
  path_library_.push_back({"spine_demo_path", 0.5, std::max<int>(static_cast<int>(axis_count) * 20, 128)});
  path_library_.push_back({"thoracic_followup", 0.4, std::max<int>(static_cast<int>(axis_count) * 15, 92)});
}

void SdkRobotFacade::refreshRuntimeCaches() {
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (!live_binding_established_ || robot_ == nullptr) return;
  try {
    std::error_code ec;
    const auto joints = robot_->jointPos(ec);
    if (!ec) {
      joint_pos_.assign(joints.begin(), joints.end());
    }
    const auto vels = robot_->jointVel(ec);
    if (!ec) {
      joint_vel_.assign(vels.begin(), vels.end());
    }
    const auto torques = robot_->jointTorque(ec);
    if (!ec) {
      joint_torque_.assign(torques.begin(), torques.end());
    }
    const auto tcp = robot_->posture(rokae::CoordinateType::endInRef, ec);
    if (!ec) {
      tcp_pose_.assign(tcp.begin(), tcp.end());
    }
    refreshRlProjects();
    refreshPathLibrary();
    refreshIoSnapshots();
  } catch (const std::exception& ex) {
    captureException("refreshRuntimeCaches", ex);
  }
#endif
}

void SdkRobotFacade::refreshRlProjects() {
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (!live_binding_established_ || robot_ == nullptr) return;
  try {
    std::error_code ec;
    const auto projects = robot_->projectsInfo(ec);
    if (!ec) {
      rl_projects_.clear();
      for (const auto& item : projects) {
        rl_projects_.push_back({item.name, item.taskList});
      }
    }
  } catch (...) {
  }
#endif
}

void SdkRobotFacade::refreshPathLibrary() {
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (!live_binding_established_ || robot_ == nullptr) return;
  try {
    std::error_code ec;
    const auto names = robot_->queryPathLists(ec);
    if (!ec) {
      path_library_.clear();
      for (const auto& name : names) {
        path_library_.push_back({name, 1.0, 0});
      }
    }
  } catch (...) {
  }
#endif
}

void SdkRobotFacade::refreshIoSnapshots() {
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (!live_binding_established_ || robot_ == nullptr) return;
  try {
    std::error_code ec;
    di_["board0_port0"] = robot_->getDI(0, 0, ec);
    do_["board0_port0"] = robot_->getDO(0, 0, ec);
    ai_["board0_port0"] = robot_->getAI(0, 0, ec);
  } catch (...) {
  }
#endif
}

void SdkRobotFacade::refreshBindingTruth() {
  vendored_sdk_detected_ = sdkAvailable();
  if (!vendored_sdk_detected_) {
    backend_kind_ = "contract_sim";
    live_binding_established_ = false;
  } else if (live_binding_established_ && robot_ != nullptr) {
    backend_kind_ = "xcore_sdk_live_binding";
  } else {
    backend_kind_ = "vendored_sdk_contract_shell";
  }
}

void SdkRobotFacade::setRtPhaseCode(const std::string& phase) {
  registers_["spine.rt.phase_code"] =
      (phase == "seek_contact" ? 1 : (phase == "scan_follow" ? 2 : (phase == "pause_hold" ? 3 : (phase == "controlled_retract" ? 4 : 0))));
}

bool SdkRobotFacade::applyErrorCode(const std::string& prefix, const std::error_code& ec, std::string* reason) {
  if (!ec) return true;
  captureFailure(prefix, ec.message(), reason);
  return false;
}

void SdkRobotFacade::captureException(const std::string& prefix, const std::exception& ex, std::string* reason) {
  captureFailure(prefix, ex.what(), reason);
}

void SdkRobotFacade::captureFailure(const std::string& prefix, const std::string& detail, std::string* reason) {
  binding_detail_ = prefix + ":" + detail;
  if (reason != nullptr) *reason = detail;
  appendLog(prefix + " failed: " + detail);
}

}  // namespace robot_core
