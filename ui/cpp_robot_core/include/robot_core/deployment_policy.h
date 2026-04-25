#pragma once

#include <string>

namespace robot_core {

/**
 * @brief Resolve the normalized deployment profile used by runtime write-policy gates.
 * @return Normalized deployment profile name, defaulting to ``dev`` when the environment is unset.
 * @throws No exceptions are thrown.
 * @boundary Reads process environment only; it does not inspect runtime mutable state.
 */
std::string runtimeDeploymentProfile();

/**
 * @brief Determine whether contract-shell writes are forbidden for the current process deployment profile.
 * @return ``true`` when only live SDK writes are allowed on this surface.
 * @throws No exceptions are thrown.
 * @boundary Implements the single authoritative profile/env gate shared by lifecycle, NRT, RT and contract-projection surfaces.
 */
bool deploymentProfileForbidsContractShellWrites();

}  // namespace robot_core
