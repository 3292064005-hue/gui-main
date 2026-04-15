#include "robot_core/sdk_robot_facade_internal.h"

#include <sstream>
#include <stdexcept>

namespace robot_core {

using namespace sdk_robot_facade_internal;

class LifecycleAdapter {
public:
  explicit LifecycleAdapter(SdkRobotFacade& owner) : owner_(owner) {}

  bool setPower(bool on) {
    if (!owner_.ensureConnected(nullptr)) {
      owner_.captureFailure("setPowerState", "controller_not_connected");
      return false;
    }
    if (!owner_.requireLiveWrite("setPowerState", nullptr)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->setPowerState(on, ec);
        if (!owner_.applyErrorCode("setPowerState", ec, nullptr)) {
          owner_.powered_ = false;
          owner_.motion_channel_ready_ = false;
          owner_.refreshBindingTruth();
          return false;
        }
      } catch (const std::exception& ex) {
        owner_.captureException("setPowerState", ex);
        return false;
      }
    }
#endif
    owner_.powered_ = on;
    owner_.motion_channel_ready_ = owner_.connected_ && owner_.powered_ && owner_.network_healthy_;
    owner_.binding_detail_ = on ? "powered" : "unpowered";
    owner_.refreshRuntimeCaches();
    owner_.refreshBindingTruth();
    owner_.appendLog(std::string("setPowerState(") + (on ? "on" : "off") + ") accepted");
    return true;
  }

  bool setAutoMode() {
    if (!owner_.ensureConnected(nullptr)) {
      owner_.captureFailure("setOperateMode(auto)", "controller_not_connected");
      return false;
    }
    if (!owner_.requireLiveWrite("setOperateMode(auto)", nullptr)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->setOperateMode(rokae::OperateMode::automatic, ec);
        if (!owner_.applyErrorCode("setOperateMode(auto)", ec, nullptr)) {
          return false;
        }
      } catch (const std::exception& ex) {
        owner_.captureException("setOperateMode(auto)", ex);
        return false;
      }
    }
#endif
    owner_.auto_mode_ = true;
    owner_.binding_detail_ = "automatic_mode";
    owner_.refreshRuntimeCaches();
    owner_.refreshBindingTruth();
    owner_.appendLog("setOperateMode(auto) accepted");
    return true;
  }

  bool setManualMode() {
    if (!owner_.ensureConnected(nullptr)) {
      owner_.captureFailure("setOperateMode(manual)", "controller_not_connected");
      return false;
    }
    if (!owner_.requireLiveWrite("setOperateMode(manual)", nullptr)) return false;
    std::string ignored;
    owner_.stopRt(&ignored);
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->setOperateMode(rokae::OperateMode::manual, ec);
        if (!owner_.applyErrorCode("setOperateMode(manual)", ec, nullptr)) {
          return false;
        }
      } catch (const std::exception& ex) {
        owner_.captureException("setOperateMode(manual)", ex);
        return false;
      }
    }
#endif
    owner_.auto_mode_ = false;
    owner_.active_rt_phase_ = "idle";
    owner_.binding_detail_ = "manual_mode";
    owner_.refreshRuntimeCaches();
    owner_.refreshBindingTruth();
    owner_.appendLog("setOperateMode(manual) accepted");
    return true;
  }

  bool configureRtMainline(const SdkRobotRuntimeConfig& config) {
    owner_.rt_config_ = config;
    owner_.rt_config_.fc_frame_matrix_m = normalizeFrameMatrixMmToM(config.fc_frame_matrix);
    owner_.rt_config_.tcp_frame_matrix_m = normalizeFrameMatrixMmToM(config.tcp_frame_matrix);
    owner_.rt_config_.load_com_m = normalizeLoadComMmToM(config.load_com_mm);
    owner_.rt_config_.ui_length_unit = "mm";
    owner_.rt_config_.sdk_length_unit = "m";
    owner_.rt_config_.boundary_normalized = true;
    owner_.control_source_exclusive_ = owner_.rt_config_.requires_single_control_source;
    owner_.nominal_rt_loop_hz_ = 1000;
    const bool config_valid = owner_.rt_config_.robot_model == ROBOT_CORE_DEFAULT_ROBOT_MODEL &&
                              owner_.rt_config_.sdk_robot_class == ROBOT_CORE_DEFAULT_SDK_CLASS &&
                              owner_.rt_config_.axis_count == ROBOT_CORE_DEFAULT_AXIS_COUNT;
    owner_.configureContactControllersFromRuntimeConfig();
    owner_.rt_mainline_configured_ = owner_.connected_ && owner_.powered_ && owner_.auto_mode_ && config_valid && owner_.control_source_exclusive_;
    owner_.binding_detail_ = owner_.rt_mainline_configured_ ? "rt_configured" : "rt_configuration_blocked";
    owner_.appendLog("configureRtMainline(robot=" + owner_.rt_config_.robot_model + ",class=" + owner_.rt_config_.sdk_robot_class + ",axis_count=" + std::to_string(owner_.rt_config_.axis_count) + ",rt_network_tolerance=" + std::to_string(owner_.rt_config_.rt_network_tolerance_percent) + ")");
    owner_.refreshBindingTruth();
    return owner_.rt_mainline_configured_;
  }

  bool ensureConnected(std::string* reason) {
    if (!owner_.connected_) {
      owner_.captureFailure("ensureConnected", "controller_not_connected", reason);
      return false;
    }
    return true;
  }

  bool ensurePoweredAuto(std::string* reason) {
    if (!ensureConnected(reason)) return false;
    if (!owner_.powered_) {
      owner_.captureFailure("ensurePoweredAuto", "controller_not_powered", reason);
      return false;
    }
    if (!owner_.auto_mode_) {
      owner_.captureFailure("ensurePoweredAuto", "auto_mode_required", reason);
      return false;
    }
    return true;
  }

  bool ensureNrtMode(std::string* reason) {
    if (!ensurePoweredAuto(reason)) return false;
    if (!owner_.requireLiveWrite("setMotionControlMode(NrtCommand)", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->setMotionControlMode(rokae::MotionControlMode::NrtCommand, ec);
        if (!owner_.applyErrorCode("setMotionControlMode(NrtCommand)", ec, reason)) {
          return false;
        }
      } catch (const std::exception& ex) {
        owner_.captureException("setMotionControlMode(NrtCommand)", ex, reason);
        return false;
      }
    }
#endif
    owner_.motion_channel_ready_ = true;
    owner_.binding_detail_ = "nrt_mode_selected";
    return true;
  }

  bool ensureRtMode(std::string* reason) {
    if (!ensurePoweredAuto(reason)) return false;
    if (!owner_.rt_mainline_configured_) {
      owner_.captureFailure("ensureRtMode", "rt_mainline_not_configured", reason);
      return false;
    }
    if (!owner_.requireLiveWrite("setMotionControlMode(RtCommand)", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->setRtNetworkTolerance(static_cast<unsigned>(std::max(0, owner_.rt_config_.rt_network_tolerance_percent)), ec);
        if (!owner_.applyErrorCode("setRtNetworkTolerance", ec, reason)) {
          return false;
        }
        owner_.robot_->setMotionControlMode(rokae::MotionControlMode::RtCommand, ec);
        if (!owner_.applyErrorCode("setMotionControlMode(RtCommand)", ec, reason)) {
          return false;
        }
      } catch (const std::exception& ex) {
        owner_.captureException("setMotionControlMode(RtCommand)", ex, reason);
        return false;
      }
    }
#endif
    owner_.binding_detail_ = "rt_mode_selected";
    return true;
  }

  bool ensureRtController(std::string* reason) {
    if (!ensureRtMode(reason)) return false;
    if (!owner_.requireLiveWrite("getRtMotionController", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        owner_.rt_controller_ = owner_.robot_->getRtMotionController().lock();
        if (owner_.rt_controller_ == nullptr) {
          owner_.captureFailure("getRtMotionController", "rt_controller_unavailable", reason);
          return false;
        }
        return true;
      } catch (const std::exception& ex) {
        owner_.captureException("getRtMotionController", ex, reason);
        return false;
      }
    }
#endif
    return true;
  }

  bool ensureRtStateStream(const std::vector<std::string>& fields, std::string* reason) {
    if (!ensureRtController(reason)) return false;
    if (!owner_.requireLiveWrite("startReceiveRobotState", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      if (owner_.rt_state_stream_started_ && fields == owner_.rt_state_fields_) {
        return true;
      }
      try {
        if (owner_.rt_state_stream_started_) {
          owner_.robot_->stopReceiveRobotState();
          owner_.rt_state_stream_started_ = false;
        }
        owner_.robot_->startReceiveRobotState(std::chrono::milliseconds(1), fields);
        owner_.rt_state_stream_started_ = true;
        owner_.rt_state_fields_ = fields;
        owner_.state_channel_ready_ = true;
        return true;
      } catch (const std::exception& ex) {
        owner_.captureException("startReceiveRobotState", ex, reason);
        return false;
      }
    }
#endif
    owner_.rt_state_stream_started_ = true;
    owner_.rt_state_fields_ = fields;
    owner_.state_channel_ready_ = true;
    owner_.appendLog("rt_state_stream_contract_shell");
    return true;
  }

  bool applyRtConfig(const SdkRobotRuntimeConfig& config, std::string* reason) {
    if (!ensureRtController(reason)) return false;
    if (!owner_.requireLiveWrite("applyRtConfig", reason)) return false;
    owner_.rt_config_ = config;
    owner_.rt_config_.fc_frame_matrix_m = normalizeFrameMatrixMmToM(config.fc_frame_matrix);
    owner_.rt_config_.tcp_frame_matrix_m = normalizeFrameMatrixMmToM(config.tcp_frame_matrix);
    owner_.rt_config_.load_com_m = normalizeLoadComMmToM(config.load_com_mm);
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.rt_controller_ != nullptr) {
      try {
        std::error_code ec;
        rokae::Load load(std::max(0.0, config.load_kg), owner_.rt_config_.load_com_m, {config.load_inertia[0], config.load_inertia[1], config.load_inertia[2]});
        owner_.rt_controller_->setEndEffectorFrame(owner_.rt_config_.tcp_frame_matrix_m, ec);
        if (!owner_.applyErrorCode("setEndEffectorFrame", ec, reason)) return false;
        owner_.rt_controller_->setLoad(load, ec);
        if (!owner_.applyErrorCode("setLoad", ec, reason)) return false;
        owner_.rt_controller_->setFilterFrequency(config.joint_filter_hz, config.cart_filter_hz, config.torque_filter_hz, ec);
        if (!owner_.applyErrorCode("setFilterFrequency", ec, reason)) return false;
        owner_.rt_controller_->setCartesianImpedance(config.cartesian_impedance, ec);
        if (!owner_.applyErrorCode("setCartesianImpedance", ec, reason)) return false;
        owner_.rt_controller_->setCartesianImpedanceDesiredTorque(config.desired_wrench_n, ec);
        if (!owner_.applyErrorCode("setCartesianImpedanceDesiredTorque", ec, reason)) return false;
        owner_.rt_controller_->setFcCoor(owner_.rt_config_.fc_frame_matrix_m, rokae::FrameType::path, ec);
        if (!owner_.applyErrorCode("setFcCoor", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("applyRtConfig", ex, reason);
        return false;
      }
    }
#endif
    owner_.configureContactControllersFromRuntimeConfig();
    owner_.rt_mainline_configured_ = true;
    owner_.binding_detail_ = "rt_config_applied";
    return true;
  }

private:
  SdkRobotFacade& owner_;
};

bool SdkRobotFacade::setPower(bool on) { return LifecycleAdapter(*this).setPower(on); }
bool SdkRobotFacade::setAutoMode() { return LifecycleAdapter(*this).setAutoMode(); }
bool SdkRobotFacade::setManualMode() { return LifecycleAdapter(*this).setManualMode(); }
bool SdkRobotFacade::configureRtMainline(const SdkRobotRuntimeConfig& config) { return LifecycleAdapter(*this).configureRtMainline(config); }
bool SdkRobotFacade::ensureConnected(std::string* reason) { return LifecycleAdapter(*this).ensureConnected(reason); }
bool SdkRobotFacade::ensurePoweredAuto(std::string* reason) { return LifecycleAdapter(*this).ensurePoweredAuto(reason); }
bool SdkRobotFacade::ensureNrtMode(std::string* reason) { return LifecycleAdapter(*this).ensureNrtMode(reason); }
bool SdkRobotFacade::ensureRtMode(std::string* reason) { return LifecycleAdapter(*this).ensureRtMode(reason); }
bool SdkRobotFacade::ensureRtController(std::string* reason) { return LifecycleAdapter(*this).ensureRtController(reason); }
bool SdkRobotFacade::ensureRtStateStream(const std::vector<std::string>& fields, std::string* reason) { return LifecycleAdapter(*this).ensureRtStateStream(fields, reason); }
bool SdkRobotFacade::applyRtConfig(const SdkRobotRuntimeConfig& config, std::string* reason) { return LifecycleAdapter(*this).applyRtConfig(config, reason); }

}  // namespace robot_core
