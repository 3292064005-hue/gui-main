#include "robot_core/deployment_policy.h"

#include <cstdlib>

namespace robot_core {

std::string runtimeDeploymentProfile() {
  const char* profile = std::getenv("SPINE_DEPLOYMENT_PROFILE");
  if (profile == nullptr || std::string(profile).empty()) {
    return "dev";
  }
  return std::string(profile);
}

bool deploymentProfileForbidsContractShellWrites() {
  const auto profile_name = runtimeDeploymentProfile();
  if (profile_name == "research" || profile_name == "clinical") {
    return true;
  }
  const char* strict = std::getenv("SPINE_STRICT_CONTROL_AUTHORITY");
  if (strict == nullptr) {
    return false;
  }
  const std::string value(strict);
  return value == "1" || value == "true" || value == "TRUE" || value == "on" || value == "ON";
}

}  // namespace robot_core
