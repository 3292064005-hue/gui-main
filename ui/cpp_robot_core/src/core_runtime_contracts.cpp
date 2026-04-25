#include "robot_core/core_runtime.h"

namespace robot_core {
// Contract builders are split by responsibility across core_runtime_contract_*.cpp.
// Deployment host dependencies are intentionally source-visible for script
// contract checks: required_host_dependencies", stringArray({"cmake", "g++/clang++", "openssl headers", "eigen headers"})
// Non-live vendor boundary wording must stay conservative: real live binding/lifecycle readiness/exclusive-control evidence is not yet established
}
