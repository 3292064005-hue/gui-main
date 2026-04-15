#pragma once

#include <cstddef>
#include <string>
#include <type_traits>
#include <unordered_map>
#include <utility>
#include <vector>

#include "robot_core/generated_runtime_command_request_types.h"

#include "robot_core/command_registry.h"

namespace robot_core {

enum class RuntimeContractFieldType {
  Any,
  String,
  Object,
  Integer,
  Double,
  Boolean,
  Array,
};

struct RuntimeCommandFieldSpec {
  const char* name;
  bool required;
  RuntimeContractFieldType field_type;
  const char* nested_required_signature;
  RuntimeContractFieldType array_item_type;
  const char* array_item_required_signature;
};

struct RuntimeCommandRequestContract {
  const char* command;
  std::vector<RuntimeCommandFieldSpec> fields;
};

struct RuntimeCommandResponseContract {
  const char* command;
  const char* data_contract_token;
  const char* data_required_fields_signature;
  std::vector<RuntimeCommandFieldSpec> data_fields;
  bool read_only;
  const char* envelope_fields_signature;
};

struct RuntimeCommandGuardContract {
  const char* command;
  const char* allowed_states_signature;
  CommandRuntimeLane lane;
};

struct RuntimeCommandDispatchContract {
  const char* command;
  const char* canonical_command;
  const char* handler_group;
};

struct RuntimeCommandTypedContract {
  const char* command;
  RuntimeCommandRequestContract request_contract;
  RuntimeCommandResponseContract response_contract;
  RuntimeCommandGuardContract guard_contract;
  RuntimeCommandDispatchContract dispatch_contract;
};

struct RuntimeCommandRequest {
  std::string command;
  std::unordered_map<std::string, std::string> string_fields;
  std::unordered_map<std::string, std::string> object_fields;
  std::unordered_map<std::string, int> integer_fields;
  std::unordered_map<std::string, double> double_fields;
  std::unordered_map<std::string, bool> boolean_fields;

  bool hasStringField(const std::string& name) const;
  bool hasObjectField(const std::string& name) const;
  bool hasIntegerField(const std::string& name) const;
  bool hasDoubleField(const std::string& name) const;
  bool hasBooleanField(const std::string& name) const;

  std::string stringField(const std::string& name, const std::string& fallback = "") const;
  std::string objectFieldJson(const std::string& name, const std::string& fallback = "{}") const;
  int intField(const std::string& name, int fallback = 0) const;
  double doubleField(const std::string& name, double fallback = 0.0) const;
  bool boolField(const std::string& name, bool fallback = false) const;

};

struct RuntimeCommandContext {
  std::string request_id;
  std::string command;
  std::string envelope_json;
};

struct RuntimeCommandInvocation {
  std::string request_id;
  std::string command;
  std::string envelope_json;
  RuntimeCommandRequest request;
  RuntimeTypedRequestVariant typed_request;
  const RuntimeCommandTypedContract* typed_contract{nullptr};

  RuntimeCommandContext context() const { return RuntimeCommandContext{request_id, command, envelope_json}; }

  bool hasStringField(const std::string& name) const;
  bool hasObjectField(const std::string& name) const;
  bool hasIntegerField(const std::string& name) const;
  bool hasDoubleField(const std::string& name) const;
  bool hasBooleanField(const std::string& name) const;

  std::string stringField(const std::string& name, const std::string& fallback = "") const;
  std::string objectFieldJson(const std::string& name, const std::string& fallback = "{}") const;
  int intField(const std::string& name, int fallback = 0) const;
  double doubleField(const std::string& name, double fallback = 0.0) const;
  bool boolField(const std::string& name, bool fallback = false) const;


  template <typename T>
  const T* requestAs() const {
    return std::get_if<T>(&typed_request);
  }

  template <typename T>
  bool requestIs() const {
    return requestAs<T>() != nullptr;
  }
};

const RuntimeCommandTypedContract* findRuntimeCommandTypedContract(const std::string& command);
const RuntimeCommandRequestContract* findRuntimeCommandRequestContract(const std::string& command);
const RuntimeCommandResponseContract* findRuntimeCommandResponseContract(const std::string& command);
const RuntimeCommandGuardContract* findRuntimeCommandGuardContract(const std::string& command);
const RuntimeCommandDispatchContract* findRuntimeCommandDispatchContract(const std::string& command);

/**
 * @brief Parse and validate a runtime command envelope into a typed invocation.
 *
 * Args:
 *   envelope_json: Serialized command envelope containing request_id/command/payload.
 *   invocation: Optional typed invocation sink populated on success.
 *   error: Optional validation failure detail.
 *
 * Returns:
 *   ``true`` when the command is supported and the payload satisfies the typed
 *   request contract.
 */
bool buildTypedRuntimeCommandRequest(const std::string& command,
                                     const RuntimeCommandRequest& request,
                                     RuntimeTypedRequestVariant* typed_request,
                                     std::string* error);

bool buildRuntimeCommandInvocation(const std::string& envelope_json,
                                  RuntimeCommandInvocation* invocation,
                                  std::string* error);

/**
 * @brief Validate and parse a manifest-backed runtime command payload.
 *
 * Args:
 *   command: Runtime command name.
 *   payload_json: Canonical JSON payload object string.
 *   parsed: Optional parsed-field sink populated on success.
 *   error: Optional validation failure detail.
 *
 * Returns:
 *   ``true`` when the payload satisfies the typed request contract.
 *
 * Boundary behaviour:
 * - Unknown commands fail validation.
 * - Required string fields must be present and non-empty.
 * - Required object fields must be present and satisfy nested required keys.
 * - Numeric/bool fields are parsed into typed slots so handlers can avoid
 *   re-reading raw JSON payload strings.
 */
bool validateAndParseRuntimeCommandPayload(const std::string& command,
                                          const std::string& payload_json,
                                          RuntimeCommandRequest* parsed,
                                          std::string* error);


/**
 * @brief Validate the typed guard contract for a runtime command.
 *
 * Args:
 *   command: Runtime command name.
 *   state: Current runtime state.
 *   lane: Dispatcher lane chosen for the command.
 *   error: Optional validation failure detail.
 *
 * Returns:
 *   ``true`` when the guard contract allows the current state and lane.
 */
bool validateRuntimeCommandGuard(const std::string& command,
                                 RobotCoreState state,
                                 CommandRuntimeLane lane,
                                 std::string* error);

/**
 * @brief Validate the typed response-envelope contract for a runtime command.
 *
 * Args:
 *   command: Runtime command name.
 *   reply_json: Serialized JSON reply envelope.
 *   error: Optional validation failure detail.
 *
 * Returns:
 *   ``true`` when the reply envelope preserves the manifest-generated contract surface.
 */
bool validateRuntimeCommandReplyEnvelope(const std::string& command,
                                         const std::string& reply_json,
                                         std::string* error);

}  // namespace robot_core
