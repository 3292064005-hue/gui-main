#include "robot_core/core_runtime_dispatcher.h"

#include "robot_core/core_runtime.h"

#include "json_utils.h"
#include "robot_core/command_registry.h"
#include "robot_core/runtime_command_contracts.h"

namespace robot_core {

namespace {

CommandRuntimeLane runtimeLaneForCommand(const std::string& command) {
  const auto* guard_contract = findRuntimeCommandGuardContract(command);
  if (guard_contract != nullptr) {
    return guard_contract->lane;
  }
  return commandRuntimeLane(command);
}

CoreRuntime::RuntimeLane toCoreRuntimeLane(CommandRuntimeLane lane) {
  switch (lane) {
    case CommandRuntimeLane::Query: return CoreRuntime::RuntimeLane::Query;
    case CommandRuntimeLane::RtControl: return CoreRuntime::RuntimeLane::RtControl;
    case CommandRuntimeLane::Command: default: return CoreRuntime::RuntimeLane::Command;
  }
}

}  // namespace

CoreRuntimeDispatcher::CommandHandler CoreRuntimeDispatcher::resolveHandler(const std::string& handler_group) const {
  if (handler_group == "handleConnectionCommand") return &CoreRuntime::handleConnectionCommand;
  if (handler_group == "handlePowerModeCommand") return &CoreRuntime::handlePowerModeCommand;
  if (handler_group == "handleValidationCommand") return &CoreRuntime::handleValidationCommand;
  if (handler_group == "handleQueryCommand") return &CoreRuntime::handleQueryCommand;
  if (handler_group == "handleFaultInjectionCommand") return &CoreRuntime::handleFaultInjectionCommand;
  if (handler_group == "handleSessionCommand") return &CoreRuntime::handleSessionCommand;
  if (handler_group == "handleExecutionCommand") return &CoreRuntime::handleExecutionCommand;
  return nullptr;
}

CoreRuntimeDispatcher::CoreRuntimeDispatcher(CoreRuntime& owner) : owner_(owner) {}

std::string CoreRuntimeDispatcher::handleCommandJson(const std::string& line) {
  RuntimeCommandInvocation invocation;
  std::string payload_error;
  if (!buildRuntimeCommandInvocation(line, &invocation, &payload_error)) {
    return owner_.replyJson(invocation.request_id, false, payload_error.empty() ? "invalid command payload" : payload_error);
  }
  const auto* typed_contract = invocation.typed_contract;
  const auto handler_group = typed_contract == nullptr || typed_contract->dispatch_contract.handler_group == nullptr
                                 ? commandHandlerGroup(invocation.command)
                                 : std::string(typed_contract->dispatch_contract.handler_group);
  if (resolveHandler(handler_group) == nullptr) {
    return owner_.replyJson(invocation.request_id, false, "unsupported command: " + invocation.command);
  }

  const auto command_lane = runtimeLaneForCommand(invocation.command);
  const auto lane = toCoreRuntimeLane(command_lane);
  std::string guard_error;
  if (!validateRuntimeCommandGuard(invocation.command, owner_.state(), command_lane, &guard_error)) {
    return owner_.replyJson(invocation.request_id, false, guard_error.empty() ? "command guard rejected request" : guard_error);
  }

  auto dispatch_with_contract = [&](std::mutex& lane_mutex) -> std::string {
    std::lock_guard<std::mutex> lane_lock(lane_mutex);
    {
      std::lock_guard<std::mutex> state_lock(owner_.state_store_.mutex);
      std::string authority_error;
      if (!owner_.authorizeInvocationLocked(invocation, &authority_error)) {
        return owner_.replyJson(invocation.request_id, false, authority_error.empty() ? "runtime authority rejected request" : authority_error);
      }
    }
    auto reply = owner_.dispatchTypedCommand(invocation);
    std::string response_error;
    if (!validateRuntimeCommandReplyEnvelope(invocation.command, reply, &response_error)) {
      return owner_.replyJson(invocation.request_id, false, response_error.empty() ? "invalid command reply envelope" : response_error);
    }
    return reply;
  };

  if (lane == CoreRuntime::RuntimeLane::Query) {
    return dispatch_with_contract(owner_.lanes_.query);
  }
  if (lane == CoreRuntime::RuntimeLane::RtControl) {
    return dispatch_with_contract(owner_.lanes_.rt);
  }
  return dispatch_with_contract(owner_.lanes_.command);
}

}  // namespace robot_core
