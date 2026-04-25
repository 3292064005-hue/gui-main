#include "robot_core/core_runtime.h"

#include <mutex>

namespace robot_core {

std::string CoreRuntime::handleQueryCommand(const RuntimeCommandInvocation& invocation) {
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  if (const auto reply = handleOperationalQueryCommandLocked(invocation); !reply.empty()) return reply;
  if (const auto reply = handleMotionQueryCommandLocked(invocation); !reply.empty()) return reply;
  if (const auto reply = handleIdentityQueryCommandLocked(invocation); !reply.empty()) return reply;
  if (const auto reply = handleContractQueryCommandLocked(invocation); !reply.empty()) return reply;
  return replyJson(invocation.request_id, false, "unsupported command: " + invocation.command);
}

}  // namespace robot_core
