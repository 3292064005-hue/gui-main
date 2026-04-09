#include "robot_core/sdk_robot_facade_internal.h"

#include <sstream>
#include <stdexcept>

namespace robot_core {

using namespace sdk_robot_facade_internal;

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



}  // namespace robot_core
