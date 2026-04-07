#pragma once

#include <string>

#include "robot_core/normal_axis_admittance_controller.h"
#include "robot_core/normal_force_estimator.h"
#include "robot_core/orientation_trim_controller.h"
#include "robot_core/tangential_scan_controller.h"
#include "robot_core/runtime_types.h"

namespace robot_core {

struct SdkRobotRuntimeConfig;

/**
 * @brief Project-side contact-control contract assembled from runtime config.
 */
struct ContactControlContract {
  std::string mode{"normal_axis_admittance"};
  AdmittanceControllerConfig seek_contact_admittance{};
  AdmittanceControllerConfig scan_follow_admittance{};
  AdmittanceControllerConfig pause_hold_admittance{};
  TangentialScanConfig tangential_scan{};
  OrientationTrimConfig orientation_trim{};
  NormalForceEstimatorConfig force_estimator{};
};

ContactControlContract buildContactControlContract(const RuntimeConfig& config);
ContactControlContract buildContactControlContract(const SdkRobotRuntimeConfig& config);
bool validateContactControlContract(const ContactControlContract& contract, std::string* reason = nullptr);

}  // namespace robot_core
