#include "robot_core/sdk_robot_facade_internal.h"

#include <sstream>
#include <stdexcept>

namespace robot_core {

using namespace sdk_robot_facade_internal;

class NrtExecutionAdapter {
public:
  explicit NrtExecutionAdapter(SdkRobotFacade& owner) : owner_(owner) {}

  bool executeMoveAbsJ(const std::vector<double>& joints_rad, int speed_mm_s, int zone_mm, std::string* reason) {
    if (!owner_.ensureNrtMode(reason)) return false;
    if (!owner_.requireLiveWrite("executeMoveAbsJ", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->setDefaultSpeed(speed_mm_s, ec);
        if (!owner_.applyErrorCode("setDefaultSpeed", ec, reason)) return false;
        owner_.robot_->setDefaultZone(zone_mm, ec);
        if (!owner_.applyErrorCode("setDefaultZone", ec, reason)) return false;
        owner_.robot_->moveReset(ec);
        if (!owner_.applyErrorCode("moveReset", ec, reason)) return false;
        owner_.robot_->moveAppend({rokae::MoveAbsJCommand(rokae::JointPosition(joints_rad))}, owner_.active_nrt_profile_, ec);
        if (!owner_.applyErrorCode("moveAppend(MoveAbsJ)", ec, reason)) return false;
        owner_.robot_->moveStart(ec);
        if (!owner_.applyErrorCode("moveStart", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("executeMoveAbsJ", ex, reason);
        return false;
      }
    }
#endif
    ++owner_.command_sequence_;
    owner_.registers_["spine.command.sequence"] = owner_.command_sequence_;
    owner_.refreshRuntimeCaches();
    return true;
  }

  bool executeMoveL(const std::vector<double>& tcp_xyzabc_m_rad, int speed_mm_s, int zone_mm, std::string* reason) {
    if (!owner_.ensureNrtMode(reason)) return false;
    if (!owner_.requireLiveWrite("executeMoveL", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->setDefaultSpeed(speed_mm_s, ec);
        if (!owner_.applyErrorCode("setDefaultSpeed", ec, reason)) return false;
        owner_.robot_->setDefaultZone(zone_mm, ec);
        if (!owner_.applyErrorCode("setDefaultZone", ec, reason)) return false;
        owner_.robot_->moveReset(ec);
        if (!owner_.applyErrorCode("moveReset", ec, reason)) return false;
        rokae::CartesianPosition target(toArray6(tcp_xyzabc_m_rad));
        owner_.robot_->moveAppend({rokae::MoveLCommand(target)}, owner_.active_nrt_profile_, ec);
        if (!owner_.applyErrorCode("moveAppend(MoveL)", ec, reason)) return false;
        owner_.robot_->moveStart(ec);
        if (!owner_.applyErrorCode("moveStart", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("executeMoveL", ex, reason);
        return false;
      }
    }
#endif
    ++owner_.command_sequence_;
    owner_.registers_["spine.command.sequence"] = owner_.command_sequence_;
    owner_.refreshRuntimeCaches();
    return true;
  }

  bool stop(std::string* reason) {
    std::string gate_reason;
    bool live_write_allowed = owner_.requireLiveWrite("stop", &gate_reason);
    bool live_stop_ok = true;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (live_write_allowed && owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->stop(ec);
        if (!owner_.applyErrorCode("stop", ec, reason)) {
          live_stop_ok = false;
        }
      } catch (const std::exception& ex) {
        owner_.captureException("stop", ex, reason);
        live_stop_ok = false;
      }
    }
#endif
    if (!live_write_allowed && reason != nullptr && reason->empty()) {
      *reason = gate_reason;
    }
    owner_.finalizeNrtStopLocal(live_write_allowed && live_stop_ok ? std::string{} : (gate_reason.empty() ? "live_stop_failed" : gate_reason));
    if (live_write_allowed && live_stop_ok) {
      owner_.appendLog("stop() accepted");
    }
    return live_write_allowed && live_stop_ok;
  }

  bool beginProfile(const std::string& profile, const std::string& sdk_command, bool requires_auto_mode, std::string* reason) {
    if (requires_auto_mode ? !owner_.ensurePoweredAuto(reason) : !owner_.ensureConnected(reason)) {
      owner_.binding_detail_ = "nrt_preconditions_failed";
      owner_.refreshBindingTruth();
      return false;
    }
    if (!owner_.control_source_exclusive_) {
      owner_.captureFailure("beginNrtProfile", "single_control_source_required", reason);
      return false;
    }
    owner_.active_nrt_profile_ = profile;
    owner_.binding_detail_ = "nrt_profile_ready:" + sdk_command;
    owner_.appendLog("beginNrtProfile(profile=" + profile + ",command=" + sdk_command + ")");
    owner_.refreshBindingTruth();
    return true;
  }

  void finishProfile(const std::string& profile, bool success, const std::string& detail) {
    if (owner_.active_nrt_profile_ == profile) owner_.active_nrt_profile_ = "idle";
    owner_.binding_detail_ = success ? "nrt_profile_finished" : "nrt_profile_failed";
    owner_.appendLog("finishNrtProfile(profile=" + profile + ",success=" + std::string(success ? "true" : "false") + (detail.empty() ? "" : ",detail=" + detail) + ")");
    owner_.refreshBindingTruth();
  }

private:
  SdkRobotFacade& owner_;
};

class CollaborationAdapter {
public:
  explicit CollaborationAdapter(SdkRobotFacade& owner) : owner_(owner) {}

  bool runRlProject(const std::string& project, const std::string& task, std::string* reason) {
    if (!owner_.ensurePoweredAuto(reason)) return false;
    if (!owner_.requireLiveWrite("runRlProject", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->loadProject(project, {task}, ec);
        if (!owner_.applyErrorCode("loadProject", ec, reason)) return false;
        owner_.robot_->ppToMain(ec);
        if (!owner_.applyErrorCode("ppToMain", ec, reason)) return false;
        owner_.robot_->runProject(ec);
        if (!owner_.applyErrorCode("runProject", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("runRlProject", ex, reason);
        return false;
      }
    }
#endif
    owner_.rl_status_.loaded_project = project;
    owner_.rl_status_.loaded_task = task;
    owner_.rl_status_.running = true;
    owner_.appendLog("runRlProject(project=" + project + ",task=" + task + ") accepted");
    return true;
  }

  bool pauseRlProject(std::string* reason) {
    if (!owner_.ensurePoweredAuto(reason)) return false;
    if (!owner_.requireLiveWrite("pauseRlProject", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->pauseProject(ec);
        if (!owner_.applyErrorCode("pauseProject", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("pauseRlProject", ex, reason);
        return false;
      }
    }
#endif
    owner_.rl_status_.running = false;
    owner_.appendLog("pauseRlProject accepted");
    return true;
  }

  bool enableDrag(const std::string& space, const std::string& type, std::string* reason) {
    if (!owner_.ensureConnected(reason)) return false;
    if (owner_.powered_ || owner_.auto_mode_) {
      owner_.captureFailure("enableDrag", "manual_mode_and_power_off_required", reason);
      return false;
    }
    if (!owner_.requireLiveWrite("enableDrag", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        const auto drag_space = (space == "joint") ? rokae::DragParameter::Space::jointSpace : rokae::DragParameter::Space::cartesianSpace;
        const auto drag_type = (type == "translation_only") ? rokae::DragParameter::Type::translationOnly : ((type == "rotation_only") ? rokae::DragParameter::Type::rotationOnly : rokae::DragParameter::Type::freely);
        owner_.robot_->enableDrag(drag_space, drag_type, ec);
        if (!owner_.applyErrorCode("enableDrag", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("enableDrag", ex, reason);
        return false;
      }
    }
#endif
    owner_.drag_state_ = {true, space, type};
    owner_.appendLog("enableDrag(space=" + space + ",type=" + type + ") accepted");
    return true;
  }

  bool disableDrag(std::string* reason) {
    if (!owner_.ensureConnected(reason)) return false;
    if (!owner_.requireLiveWrite("disableDrag", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->disableDrag(ec);
        if (!owner_.applyErrorCode("disableDrag", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("disableDrag", ex, reason);
        return false;
      }
    }
#endif
    owner_.drag_state_.enabled = false;
    owner_.appendLog("disableDrag accepted");
    return true;
  }

  bool replayPath(const std::string& name, double rate, std::string* reason) {
    if (!owner_.ensurePoweredAuto(reason)) return false;
    if (!owner_.requireLiveWrite("replayPath", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->replayPath(name, rate, ec);
        if (!owner_.applyErrorCode("replayPath", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("replayPath", ex, reason);
        return false;
      }
    }
#endif
    owner_.appendLog("replayPath(name=" + name + ",rate=" + std::to_string(rate) + ") accepted");
    return true;
  }

  bool startRecordPath(int duration_s, std::string* reason) {
    if (!owner_.ensureConnected(reason)) return false;
    if (!owner_.requireLiveWrite("startRecordPath", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->startRecordPath(duration_s, ec);
        if (!owner_.applyErrorCode("startRecordPath", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("startRecordPath", ex, reason);
        return false;
      }
    }
#endif
    owner_.appendLog("startRecordPath(duration_s=" + std::to_string(duration_s) + ") accepted");
    return true;
  }

  bool stopRecordPath(std::string* reason) {
    if (!owner_.ensureConnected(reason)) return false;
    if (!owner_.requireLiveWrite("stopRecordPath", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->stopRecordPath(ec);
        if (!owner_.applyErrorCode("stopRecordPath", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("stopRecordPath", ex, reason);
        return false;
      }
    }
#endif
    owner_.appendLog("stopRecordPath accepted");
    return true;
  }

  bool cancelRecordPath(std::string* reason) {
    if (!owner_.ensureConnected(reason)) return false;
    if (!owner_.requireLiveWrite("cancelRecordPath", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->cancelRecordPath(ec);
        if (!owner_.applyErrorCode("cancelRecordPath", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("cancelRecordPath", ex, reason);
        return false;
      }
    }
#endif
    owner_.appendLog("cancelRecordPath accepted");
    return true;
  }

  bool saveRecordPath(const std::string& name, const std::string& save_as, std::string* reason) {
    if (!owner_.ensureConnected(reason)) return false;
    if (!owner_.requireLiveWrite("saveRecordPath", reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (owner_.live_binding_established_ && owner_.robot_ != nullptr) {
      try {
        std::error_code ec;
        owner_.robot_->saveRecordPath(name, ec, save_as);
        if (!owner_.applyErrorCode("saveRecordPath", ec, reason)) return false;
      } catch (const std::exception& ex) {
        owner_.captureException("saveRecordPath", ex, reason);
        return false;
      }
    }
#endif
    owner_.appendLog("saveRecordPath(name=" + name + ",save_as=" + save_as + ") accepted");
    return true;
  }

private:
  SdkRobotFacade& owner_;
};

bool SdkRobotFacade::executeMoveAbsJ(const std::vector<double>& joints_rad, int speed_mm_s, int zone_mm, std::string* reason) { return NrtExecutionAdapter(*this).executeMoveAbsJ(joints_rad, speed_mm_s, zone_mm, reason); }
bool SdkRobotFacade::executeMoveL(const std::vector<double>& tcp_xyzabc_m_rad, int speed_mm_s, int zone_mm, std::string* reason) { return NrtExecutionAdapter(*this).executeMoveL(tcp_xyzabc_m_rad, speed_mm_s, zone_mm, reason); }
bool SdkRobotFacade::stopNrt(std::string* reason) { return NrtExecutionAdapter(*this).stop(reason); }
bool SdkRobotFacade::beginNrtProfile(const std::string& profile, const std::string& sdk_command, bool requires_auto_mode, std::string* reason) { return NrtExecutionAdapter(*this).beginProfile(profile, sdk_command, requires_auto_mode, reason); }
void SdkRobotFacade::finishNrtProfile(const std::string& profile, bool success, const std::string& detail) { NrtExecutionAdapter(*this).finishProfile(profile, success, detail); }

bool SdkRobotFacade::runRlProject(const std::string& project, const std::string& task, std::string* reason) { return CollaborationAdapter(*this).runRlProject(project, task, reason); }
bool SdkRobotFacade::pauseRlProject(std::string* reason) { return CollaborationAdapter(*this).pauseRlProject(reason); }
bool SdkRobotFacade::enableDrag(const std::string& space, const std::string& type, std::string* reason) { return CollaborationAdapter(*this).enableDrag(space, type, reason); }
bool SdkRobotFacade::disableDrag(std::string* reason) { return CollaborationAdapter(*this).disableDrag(reason); }
bool SdkRobotFacade::replayPath(const std::string& name, double rate, std::string* reason) { return CollaborationAdapter(*this).replayPath(name, rate, reason); }
bool SdkRobotFacade::startRecordPath(int duration_s, std::string* reason) { return CollaborationAdapter(*this).startRecordPath(duration_s, reason); }
bool SdkRobotFacade::stopRecordPath(std::string* reason) { return CollaborationAdapter(*this).stopRecordPath(reason); }
bool SdkRobotFacade::cancelRecordPath(std::string* reason) { return CollaborationAdapter(*this).cancelRecordPath(reason); }
bool SdkRobotFacade::saveRecordPath(const std::string& name, const std::string& save_as, std::string* reason) { return CollaborationAdapter(*this).saveRecordPath(name, save_as, reason); }

}  // namespace robot_core
