#include "robot_core/sdk_robot_facade_internal.h"

#include <sstream>
#include <stdexcept>

namespace robot_core {

using namespace sdk_robot_facade_internal;

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



}  // namespace robot_core
