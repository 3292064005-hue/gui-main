#include "robot_core/core_runtime_contract_publisher.h"

#include "robot_core/core_runtime.h"

namespace robot_core {

CoreRuntimeContractPublisher::CoreRuntimeContractPublisher(const CoreRuntime& owner) : owner_(owner) {}

// Contract publisher access remains protected by the runtime state_mutex_ surface.
std::string CoreRuntimeContractPublisher::authoritativeRuntimeEnvelopeJsonLocked() const {
  std::lock_guard<std::mutex> state_lock(owner_.state_store_.mutex);
  return owner_.authoritativeRuntimeEnvelopeJsonInternal();
}

std::string CoreRuntimeContractPublisher::controlGovernanceContractJsonLocked() const {
  std::lock_guard<std::mutex> state_lock(owner_.state_store_.mutex);
  return owner_.controlGovernanceContractJsonInternal();
}

std::string CoreRuntimeContractPublisher::controllerEvidenceJsonLocked() const {
  std::lock_guard<std::mutex> state_lock(owner_.state_store_.mutex);
  return owner_.controllerEvidenceJsonInternal();
}

std::string CoreRuntimeContractPublisher::releaseContractJsonLocked() const {
  std::lock_guard<std::mutex> state_lock(owner_.state_store_.mutex);
  return owner_.releaseContractJsonInternal();
}

std::string CoreRuntimeContractPublisher::deploymentContractJsonLocked() const {
  std::lock_guard<std::mutex> state_lock(owner_.state_store_.mutex);
  return owner_.deploymentContractJsonInternal();
}

}  // namespace robot_core
