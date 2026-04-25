#include "robot_core/core_runtime.h"

#include <algorithm>
#include <filesystem>
#include <functional>
#include <unordered_map>

#include "json_utils.h"
#include "core_runtime_command_helpers.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {


std::string CoreRuntime::handleFaultInjectionCommand(const RuntimeCommandInvocation& invocation) {
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  const auto& command = invocation.command;
  using FaultHandler = std::function<std::string(CoreRuntime*, const RuntimeCommandInvocation&)>;
  static const std::unordered_map<std::string, FaultHandler> handlers = {
      {"inject_fault", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<InjectFaultRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: inject_fault");
         }
         const auto fault_name = request->fault_name;
         std::string error_message;
         if (!self->applyFaultInjectionLocked(fault_name, &error_message)) {
           return self->replyJson(inv.request_id, false, error_message.empty() ? "fault injection failed" : error_message);
         }
         return self->replyJson(inv.request_id, true, "inject_fault accepted", self->faultInjectionContractJsonLocked());
       }},
      {"clear_injected_faults", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ClearInjectedFaultsRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: clear_injected_faults");
         }
         (void)request;
         self->clearInjectedFaultsLocked();
         return self->replyJson(inv.request_id, true, "clear_injected_faults accepted", self->faultInjectionContractJsonLocked());
       }},
  };
  const auto it = handlers.find(command);
  if (it == handlers.end()) {
    return replyJson(invocation.request_id, false, "unsupported command: " + command);
  }
  return it->second(this, invocation);
}


}  // namespace robot_core
