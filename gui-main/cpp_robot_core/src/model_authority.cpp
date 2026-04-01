#include "robot_core/model_authority.h"

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
  out.authoritative_precheck = sdk.sdkAvailable() && sdk.xmateModelAvailable() && family.supports_xmate_model;
  out.authoritative_runtime = sdk.sdkAvailable() && sdk.controlSourceExclusive() && sdk.connected() && sdk.powered() && sdk.automaticMode() && sdk.rtMainlineConfigured();
  if (!sdk.sdkAvailable()) {
    out.warnings.push_back("vendored xCore SDK is not linked; authoritative runtime is unavailable");
  }
  if (!sdk.xmateModelAvailable() && family.supports_xmate_model) {
    out.warnings.push_back("xMateModel library is unavailable; planner/model authority is degraded");
  }
  if (!family.supports_planner) {
    out.warnings.push_back("selected robot family does not expose planner primitives in the frozen capability matrix");
  }
  if (!family.supports_xmate_model) {
    out.warnings.push_back("selected robot family does not expose xMateModel authority in the frozen capability matrix");
  }
  return out;
}

}  // namespace robot_core
