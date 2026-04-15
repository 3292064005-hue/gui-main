#pragma once

#include <string>

namespace robot_core {

class CoreRuntime;

class CoreRuntimeContractPublisher {
public:
  explicit CoreRuntimeContractPublisher(const CoreRuntime& owner);
  std::string authoritativeRuntimeEnvelopeJsonLocked() const;
  std::string controlGovernanceContractJsonLocked() const;
  std::string controllerEvidenceJsonLocked() const;
  std::string releaseContractJsonLocked() const;
  std::string deploymentContractJsonLocked() const;

private:
  const CoreRuntime& owner_;
};

}  // namespace robot_core
