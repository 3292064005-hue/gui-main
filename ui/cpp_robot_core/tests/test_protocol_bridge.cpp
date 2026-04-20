#include "robot_core/protobuf_protocol.h"

#include <cstdlib>
#include <iostream>
#include <string>

namespace {

bool require(bool condition, const std::string& message) {
  if (!condition) {
    std::cerr << "[FAIL] " << message << std::endl;
    return false;
  }
  return true;
}

}  // namespace

int main() {
  robot_core::CoreRuntime runtime;

  spine_core::Command command;
  command.set_protocol_version(robot_core::kIpcProtocolVersion);
  command.set_command("connect_robot");
  command.set_payload_json("{}");
  command.set_request_id("req-connect");

  std::string encoded_command;
  if (!require(command.SerializeToString(&encoded_command), "command protobuf serialization failed")) {
    return 1;
  }

  spine_core::Command decoded_command;
  if (!require(decoded_command.ParseFromString(encoded_command), "command protobuf parsing failed")) {
    return 1;
  }

  const auto reply = robot_core::dispatchProtobufCommand(runtime, decoded_command);
  if (!require(reply.ok(), "connect_robot should succeed through protobuf bridge")) {
    return 1;
  }
  if (!require(reply.protocol_version() == robot_core::kIpcProtocolVersion, "reply protocol version should stay canonical")) {
    return 1;
  }
  if (!require(reply.request_id() == "req-connect", "reply should preserve request id")) {
    return 1;
  }

  std::string encoded_reply;
  if (!require(reply.SerializeToString(&encoded_reply), "reply protobuf serialization failed")) {
    return 1;
  }

  spine_core::Reply decoded_reply;
  if (!require(decoded_reply.ParseFromString(encoded_reply), "reply protobuf parsing failed")) {
    return 1;
  }
  if (!require(decoded_reply.ok(), "decoded reply should remain successful")) {
    return 1;
  }

  const auto snapshot = runtime.takeTelemetrySnapshot();
  bool saw_camera = false;
  bool saw_pressure = false;
  bool saw_ultrasound = false;
  for (const auto& device : snapshot.devices) {
    if (device.device_name == "camera") {
      saw_camera = true;
      if (!require(!device.connected && !device.authoritative, "camera must not become connected/authoritative from robot connect alone")) return 1;
    }
    if (device.device_name == "pressure") {
      saw_pressure = true;
      if (!require(!device.connected, "pressure must not become connected from robot connect alone")) return 1;
    }
    if (device.device_name == "ultrasound") {
      saw_ultrasound = true;
      if (!require(!device.connected, "ultrasound must not become connected from robot connect alone")) return 1;
    }
  }
  if (!require(saw_camera && saw_pressure && saw_ultrasound, "device roster must include camera/pressure/ultrasound")) return 1;

  spine_core::Command bad_version;
  bad_version.set_protocol_version(robot_core::kIpcProtocolVersion + 1);
  bad_version.set_command("connect_robot");
  bad_version.set_payload_json("{}");
  bad_version.set_request_id("req-bad-version");

  const auto rejected = robot_core::dispatchProtobufCommand(runtime, bad_version);
  if (!require(!rejected.ok(), "mismatched protocol version must be rejected")) {
    return 1;
  }
  if (!require(rejected.message() == "protocol version mismatch", "rejection reason should be explicit")) {
    return 1;
  }
  if (!require(rejected.request_id() == "req-bad-version", "rejected reply should preserve request id")) {
    return 1;
  }

  std::cout << "Protocol bridge smoke test passed." << std::endl;
  std::cout.flush();
  std::fflush(nullptr);
  std::_Exit(0);
}
