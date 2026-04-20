#include "robot_core/model_authority.h"

#include <algorithm>
#include <cmath>

#include "robot_core/robot_family_descriptor.h"
#include "robot_core/sdk_robot_facade.h"

namespace robot_core {

ModelAuthoritySnapshot ModelAuthority::snapshot(const RuntimeConfig& config, const SdkRobotFacade& sdk) const {
  const auto family = resolveRobotFamilyDescriptor(config.robot_model, config.sdk_robot_class, config.axis_count);
  ModelAuthoritySnapshot out;
  out.runtime_source = sdk.runtimeSource();
  out.family_key = family.family_key;
  out.family_label = family.family_label;
  out.robot_model = family.robot_model;
  out.sdk_robot_class = family.sdk_robot_class;
  out.planner_supported = family.supports_planner;
  out.xmate_model_supported = family.supports_xmate_model;
  out.authoritative_precheck = sdk.sdkAvailable() && sdk.xmateModelAvailable() && family.supports_xmate_model && sdk.liveBindingEstablished();
  out.authoritative_runtime = sdk.sdkAvailable() && sdk.liveBindingEstablished() && sdk.controlSourceExclusive() && sdk.connected() && sdk.powered() && sdk.automaticMode() && sdk.rtMainlineConfigured();
  if (!sdk.sdkAvailable()) {
    out.warnings.push_back("vendored xCore SDK is not linked; authoritative runtime is unavailable");
  }
  if (!sdk.xmateModelAvailable()) {
    out.warnings.push_back("xMateModel library is unavailable; planner/model authority is degraded");
  }
  if (!sdk.liveBindingEstablished()) {
    out.warnings.push_back("live xMateRobot binding is not established; runtime authority remains degraded");
  }
  return out;
}


bool ModelAuthority::validateRtPhaseTargetDelta(const RuntimeConfig& config, const SdkRobotFacade& sdk, std::string* reason) const {
  const bool scan_speed_ok = config.scan_tangent_speed_min_mm_s > 0.0 &&
                             config.scan_tangent_speed_max_mm_s >= config.scan_tangent_speed_min_mm_s;
  const bool travel_ok = config.seek_contact_max_travel_mm > 0.0 &&
                         config.retract_travel_mm > 0.0 &&
                         config.segment_length_mm > 0.0 &&
                         config.sample_step_mm > 0.0;
  const bool step_ok = config.rt_max_cart_step_mm > 0.0 && config.rt_max_cart_vel_mm_s > 0.0 && config.rt_max_cart_acc_mm_s2 > 0.0;
  const bool plan_driven_ok = sdk.plannedWaypointCount() == 0 || sdk.plannedSegmentId() > 0;
  const bool ok = scan_speed_ok && travel_ok && step_ok && plan_driven_ok;
  if (!ok && reason != nullptr) {
    *reason = !plan_driven_ok ? "rt_phase_plan_segment_unavailable" : "rt_phase_target_delta_invalid";
  }
  return ok;
}

bool ModelAuthority::validateRtPhaseWorkspace(const RuntimeConfig& config, const SdkRobotFacade& sdk, std::string* reason) const {
  const auto pose = sdk.tcpPose();
  const bool pose_ok = pose.size() >= 6 && std::all_of(pose.begin(), pose.begin() + 6, [](double value) { return std::isfinite(value); });
  const bool workspace_ok = !pose_ok ? !sdk.liveBindingEstablished() :
      std::fabs(pose[0]) <= std::max(800.0, config.segment_length_mm * 8.0) &&
      std::fabs(pose[1]) <= std::max(800.0, config.segment_length_mm * 8.0) &&
      std::fabs(pose[2]) <= 1200.0;
  if ((!pose_ok || !workspace_ok) && reason != nullptr) {
    *reason = !pose_ok ? "rt_phase_workspace_pose_unavailable" : "rt_phase_workspace_violation";
  }
  return workspace_ok;
}

bool ModelAuthority::validateRtPhaseSingularityMargin(const RuntimeConfig& config, const SdkRobotFacade& sdk, std::string* reason) const {
  if (!sdk.liveBindingEstablished() || !sdk.xmateModelAvailable()) {
    return true;
  }
  const auto pose = sdk.tcpPose();
  const bool pose_ok = pose.size() >= 6 && std::all_of(pose.begin(), pose.begin() + 6, [](double value) { return std::isfinite(value); });
  const bool margin_ok = config.singularity_avoidance_enabled && pose_ok && std::fabs(pose[4]) < (1.45 * M_PI);
  if (!margin_ok && reason != nullptr) {
    *reason = "rt_phase_singularity_margin_insufficient";
  }
  return margin_ok;
}

}  // namespace robot_core
