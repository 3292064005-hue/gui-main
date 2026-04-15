#include "robot_core/core_runtime_contract_publisher.h"

#include "robot_core/core_runtime.h"

namespace robot_core {

CoreRuntimeContractPublisher::CoreRuntimeContractPublisher(const CoreRuntime& owner) : owner_(owner) {}

std::string CoreRuntimeContractPublisher::authoritativeRuntimeEnvelopeJsonLocked() const {
  std::lock_guard<std::mutex> state_lock(owner_.state_mutex_);
  return owner_.authoritativeRuntimeEnvelopeJsonInternal();
}

std::string CoreRuntimeContractPublisher::controlGovernanceContractJsonLocked() const {
  std::lock_guard<std::mutex> state_lock(owner_.state_mutex_);
  return owner_.controlGovernanceContractJsonInternal();
}

std::string CoreRuntimeContractPublisher::controllerEvidenceJsonLocked() const {
  std::lock_guard<std::mutex> state_lock(owner_.state_mutex_);
  return owner_.controllerEvidenceJsonInternal();
}

std::string CoreRuntimeContractPublisher::releaseContractJsonLocked() const {
  std::lock_guard<std::mutex> state_lock(owner_.state_mutex_);
  return owner_.releaseContractJsonInternal();
}

std::string CoreRuntimeContractPublisher::deploymentContractJsonLocked() const {
  std::lock_guard<std::mutex> state_lock(owner_.state_mutex_);
  return owner_.deploymentContractJsonInternal();
}

}  // namespace robot_core
