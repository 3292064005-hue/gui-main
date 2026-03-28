#pragma once
#include "robot_core/runtime_types.h"
#include "ipc_messages.pb.h"
#include <string>
#include <vector>
namespace robot_core {
class TelemetryPublisher {
public:
  std::vector<std::string> buildLines(const TelemetrySnapshot& snapshot) const;
  std::vector<spine_core::TelemetryEnvelope> buildProtobufMessages(const TelemetrySnapshot& snapshot) const;
};
}
