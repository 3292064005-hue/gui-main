#include "robot_core/sdk_robot_facade_internal.h"

#include <sstream>
#include <stdexcept>

namespace robot_core {

using namespace sdk_robot_facade_internal;

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
