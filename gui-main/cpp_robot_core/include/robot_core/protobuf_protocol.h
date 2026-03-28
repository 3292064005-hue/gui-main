#pragma once

#include "ipc_messages.pb.h"
#include "robot_core/core_runtime.h"

namespace robot_core {

constexpr int kIpcProtocolVersion = 1;

spine_core::Reply dispatchProtobufCommand(CoreRuntime& runtime, const spine_core::Command& cmd);

}  // namespace robot_core
