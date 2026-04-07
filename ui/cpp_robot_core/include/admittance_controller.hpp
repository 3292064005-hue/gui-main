#pragma once

#include "robot_core/normal_axis_admittance_controller.h"

namespace robot_core {

/**
 * @brief Legacy compatibility alias for the canonical normal-axis admittance controller.
 *
 * Historical examples included this header directly. The authoritative implementation
 * now lives in robot_core/normal_axis_admittance_controller.h.
 */
using AdmittanceController = NormalAxisAdmittanceController;

}  // namespace robot_core
