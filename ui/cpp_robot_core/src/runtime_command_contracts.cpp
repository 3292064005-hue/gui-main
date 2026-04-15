#include "robot_core/runtime_command_contracts.h"

#include <algorithm>
#include <regex>
#include <sstream>
#include <string>
#include <unordered_map>
#include <utility>

#include "json_utils.h"

namespace robot_core {
namespace {

std::vector<std::string> splitSignature(const char* signature) {
  std::vector<std::string> items;
  if (signature == nullptr || *signature == '\0') return items;
  std::stringstream stream(signature);
  std::string item;
  while (std::getline(stream, item, '|')) {
    if (!item.empty()) items.push_back(item);
  }
  return items;
}

bool hasJsonKey(const std::string& json_line, const std::string& key) {
  const std::regex re("\\\"" + key + "\\\"\\s*:");
  return std::regex_search(json_line, re);
}

const std::vector<RuntimeCommandTypedContract>& typedContracts() {
  static const std::vector<RuntimeCommandTypedContract> kContracts = [] {
    std::vector<RuntimeCommandTypedContract> items = {
#include "robot_core/generated_runtime_command_contracts.inc"
    };
    return items;
  }();
  return kContracts;
}


std::vector<std::string> splitTopLevelArrayItems(const std::string& array_json) {
  std::vector<std::string> items;
  if (array_json.size() < 2 || array_json.front() != '[' || array_json.back() != ']') {
    return items;
  }
  std::size_t start = 1;
  int bracket_depth = 0;
  int brace_depth = 0;
  bool in_string = false;
  bool escaped = false;
  auto flush = [&](std::size_t end) {
    if (end <= start) return;
    auto item = array_json.substr(start, end - start);
    const auto begin = item.find_first_not_of(" \t\r\n");
    if (begin == std::string::npos) return;
    const auto finish = item.find_last_not_of(" \t\r\n");
    items.push_back(item.substr(begin, finish - begin + 1));
  };
  for (std::size_t idx = 1; idx + 1 < array_json.size(); ++idx) {
    const char ch = array_json[idx];
    if (escaped) { escaped = false; continue; }
    if (ch == '\\') { escaped = true; continue; }
    if (ch == '"') { in_string = !in_string; continue; }
    if (in_string) continue;
    if (ch == '[') ++bracket_depth;
    else if (ch == ']') --bracket_depth;
    else if (ch == '{') ++brace_depth;
    else if (ch == '}') --brace_depth;
    else if (ch == ',' && bracket_depth == 0 && brace_depth == 0) {
      flush(idx);
      start = idx + 1;
    }
  }
  flush(array_json.size() - 1);
  return items;
}

bool validateArrayItem(const RuntimeCommandFieldSpec& field, const std::string& item_json, std::string* error) {
  switch (field.array_item_type) {
    case RuntimeContractFieldType::Any:
      return true;
    case RuntimeContractFieldType::String:
      if (item_json.size() >= 2 && item_json.front() == '"' && item_json.back() == '"') return true;
      if (error) *error = "array item must be a string";
      return false;
    case RuntimeContractFieldType::Object:
      if (item_json.empty() || item_json.front() != '{' || item_json.back() != '}') {
        if (error) *error = "array item must be an object";
        return false;
      }
      for (const auto& nested : splitSignature(field.array_item_required_signature)) {
        if (!hasJsonKey(item_json, nested)) {
          if (error) *error = "array item missing required nested field: " + nested;
          return false;
        }
      }
      return true;
    case RuntimeContractFieldType::Integer: {
      const std::regex re(R"(^\s*-?[0-9]+\s*$)");
      if (std::regex_match(item_json, re)) return true;
      if (error) *error = "array item must be an integer";
      return false;
    }
    case RuntimeContractFieldType::Double: {
      const std::regex re(R"(^\s*-?[0-9]+(?:\.[0-9]+)?\s*$)");
      if (std::regex_match(item_json, re)) return true;
      if (error) *error = "array item must be a double";
      return false;
    }
    case RuntimeContractFieldType::Boolean:
      if (item_json == "true" || item_json == "false") return true;
      if (error) *error = "array item must be a boolean";
      return false;
    case RuntimeContractFieldType::Array:
      if (!item_json.empty() && item_json.front() == '[' && item_json.back() == ']') return true;
      if (error) *error = "array item must be an array";
      return false;
  }
  return true;
}

const std::unordered_map<std::string, const RuntimeCommandTypedContract*>& typedContractIndex() {
  static const std::unordered_map<std::string, const RuntimeCommandTypedContract*> kIndex = [] {
    std::unordered_map<std::string, const RuntimeCommandTypedContract*> items;
    items.reserve(typedContracts().size());
    for (const auto& contract : typedContracts()) {
      items.emplace(contract.command, &contract);
    }
    return items;
  }();
  return kIndex;
}

bool validateField(const RuntimeCommandFieldSpec& field,
                   const std::string& payload_json,
                   RuntimeCommandRequest* parsed,
                   std::string* error) {
  const std::string name = field.name == nullptr ? std::string{} : std::string(field.name);
  const bool present = hasJsonKey(payload_json, name);
  if (!present) {
    if (field.required) {
      if (error != nullptr) *error = "payload missing required field: " + name;
      return false;
    }
    return true;
  }

  switch (field.field_type) {
    case RuntimeContractFieldType::Object: {
      const auto object_json = json::extractObject(payload_json, name, "");
      if (object_json.empty()) {
        if (error != nullptr) *error = "payload field '" + name + "' must be an object";
        return false;
      }
      if (parsed != nullptr) parsed->object_fields[name] = object_json;
      for (const auto& nested : splitSignature(field.nested_required_signature)) {
        if (!hasJsonKey(object_json, nested)) {
          if (error != nullptr) *error = "payload field '" + name + "' missing required nested field: " + nested;
          return false;
        }
      }
      return true;
    }
    case RuntimeContractFieldType::String: {
      const auto value = json::extractString(payload_json, name, "");
      if (value.empty()) {
        if (error != nullptr) *error = "payload field '" + name + "' must be a non-empty string";
        return false;
      }
      if (parsed != nullptr) parsed->string_fields[name] = value;
      return true;
    }
    case RuntimeContractFieldType::Integer: {
      const auto value = json::extractInt(payload_json, name, 0);
      if (parsed != nullptr) parsed->integer_fields[name] = value;
      return true;
    }
    case RuntimeContractFieldType::Double: {
      const auto value = json::extractDouble(payload_json, name, 0.0);
      if (parsed != nullptr) parsed->double_fields[name] = value;
      return true;
    }
    case RuntimeContractFieldType::Boolean: {
      const auto value = json::extractBool(payload_json, name, false);
      if (parsed != nullptr) parsed->boolean_fields[name] = value;
      return true;
    }
    case RuntimeContractFieldType::Array: {
      const auto array_json = json::extractArray(payload_json, name, "");
      if (array_json.empty()) {
        if (error != nullptr) *error = "payload field '" + name + "' must be an array";
        return false;
      }
      const auto items = splitTopLevelArrayItems(array_json);
      for (std::size_t idx = 0; idx < items.size(); ++idx) {
        std::string item_error;
        if (!validateArrayItem(field, items[idx], &item_error)) {
          if (error != nullptr) *error = "payload field '" + name + "' item #" + std::to_string(idx) + ": " + item_error;
          return false;
        }
      }
      if (parsed != nullptr) parsed->object_fields[name] = array_json;
      return true;
    }
    case RuntimeContractFieldType::Any:
    default: {
      const auto string_value = json::extractString(payload_json, name, "");
      if (!string_value.empty()) {
        if (parsed != nullptr) parsed->string_fields[name] = string_value;
        return true;
      }
      const auto object_json = json::extractObject(payload_json, name, "");
      if (!object_json.empty()) {
        if (parsed != nullptr) parsed->object_fields[name] = object_json;
        return true;
      }
      return true;
    }
  }
}

}  // namespace

bool RuntimeCommandRequest::hasStringField(const std::string& name) const {
  return string_fields.find(name) != string_fields.end();
}

bool RuntimeCommandRequest::hasObjectField(const std::string& name) const {
  return object_fields.find(name) != object_fields.end();
}

bool RuntimeCommandRequest::hasIntegerField(const std::string& name) const {
  return integer_fields.find(name) != integer_fields.end();
}

bool RuntimeCommandRequest::hasDoubleField(const std::string& name) const {
  return double_fields.find(name) != double_fields.end();
}

bool RuntimeCommandRequest::hasBooleanField(const std::string& name) const {
  return boolean_fields.find(name) != boolean_fields.end();
}

std::string RuntimeCommandRequest::stringField(const std::string& name, const std::string& fallback) const {
  const auto it = string_fields.find(name);
  return it == string_fields.end() ? fallback : it->second;
}

std::string RuntimeCommandRequest::objectFieldJson(const std::string& name, const std::string& fallback) const {
  const auto it = object_fields.find(name);
  return it == object_fields.end() ? fallback : it->second;
}

int RuntimeCommandRequest::intField(const std::string& name, int fallback) const {
  const auto it = integer_fields.find(name);
  return it == integer_fields.end() ? fallback : it->second;
}

double RuntimeCommandRequest::doubleField(const std::string& name, double fallback) const {
  const auto it = double_fields.find(name);
  return it == double_fields.end() ? fallback : it->second;
}

bool RuntimeCommandRequest::boolField(const std::string& name, bool fallback) const {
  const auto it = boolean_fields.find(name);
  return it == boolean_fields.end() ? fallback : it->second;
}

bool RuntimeCommandInvocation::hasStringField(const std::string& name) const {
  return request.hasStringField(name);
}

bool RuntimeCommandInvocation::hasObjectField(const std::string& name) const {
  return request.hasObjectField(name);
}

bool RuntimeCommandInvocation::hasIntegerField(const std::string& name) const {
  return request.hasIntegerField(name);
}

bool RuntimeCommandInvocation::hasDoubleField(const std::string& name) const {
  return request.hasDoubleField(name);
}

bool RuntimeCommandInvocation::hasBooleanField(const std::string& name) const {
  return request.hasBooleanField(name);
}

std::string RuntimeCommandInvocation::stringField(const std::string& name, const std::string& fallback) const {
  return request.stringField(name, fallback);
}

std::string RuntimeCommandInvocation::objectFieldJson(const std::string& name, const std::string& fallback) const {
  return request.objectFieldJson(name, fallback);
}

int RuntimeCommandInvocation::intField(const std::string& name, int fallback) const {
  return request.intField(name, fallback);
}

double RuntimeCommandInvocation::doubleField(const std::string& name, double fallback) const {
  return request.doubleField(name, fallback);
}

bool RuntimeCommandInvocation::boolField(const std::string& name, bool fallback) const {
  return request.boolField(name, fallback);
}

const RuntimeCommandTypedContract* findRuntimeCommandTypedContract(const std::string& command) {
  const auto& index = typedContractIndex();
  const auto it = index.find(command);
  return it == index.end() ? nullptr : it->second;
}

const RuntimeCommandRequestContract* findRuntimeCommandRequestContract(const std::string& command) {
  const auto* contract = findRuntimeCommandTypedContract(command);
  return contract == nullptr ? nullptr : &contract->request_contract;
}

const RuntimeCommandResponseContract* findRuntimeCommandResponseContract(const std::string& command) {
  const auto* contract = findRuntimeCommandTypedContract(command);
  return contract == nullptr ? nullptr : &contract->response_contract;
}

const RuntimeCommandGuardContract* findRuntimeCommandGuardContract(const std::string& command) {
  const auto* contract = findRuntimeCommandTypedContract(command);
  return contract == nullptr ? nullptr : &contract->guard_contract;
}

const RuntimeCommandDispatchContract* findRuntimeCommandDispatchContract(const std::string& command) {
  const auto* contract = findRuntimeCommandTypedContract(command);
  return contract == nullptr ? nullptr : &contract->dispatch_contract;
}

bool buildTypedRuntimeCommandRequest(const std::string& command,
                                     const RuntimeCommandRequest& request,
                                     RuntimeTypedRequestVariant* typed_request,
                                     std::string* error) {
#include "robot_core/generated_runtime_command_request_parsers.inc"
  if (error != nullptr) *error = "unsupported typed command request";
  return false;
}

bool buildRuntimeCommandInvocation(const std::string& envelope_json,
                                  RuntimeCommandInvocation* invocation,
                                  std::string* error) {
  const auto request_id = json::extractString(envelope_json, "request_id");
  const auto command = json::extractString(envelope_json, "command");
  const auto payload_json = json::extractObject(envelope_json, "payload", "{}");
  RuntimeCommandRequest parsed;
  std::string payload_error;
  if (!validateAndParseRuntimeCommandPayload(command, payload_json, &parsed, &payload_error)) {
    if (error != nullptr) *error = payload_error.empty() ? "invalid command payload" : payload_error;
    return false;
  }
  RuntimeTypedRequestVariant typed_request{};
  std::string typed_error;
  if (!buildTypedRuntimeCommandRequest(command, parsed, &typed_request, &typed_error)) {
    if (error != nullptr) *error = typed_error.empty() ? "invalid typed command request" : typed_error;
    return false;
  }
  if (invocation != nullptr) {
    invocation->request_id = request_id;
    invocation->command = command;
    invocation->envelope_json = envelope_json;
    invocation->request = std::move(parsed);
    invocation->typed_request = std::move(typed_request);
    invocation->typed_contract = findRuntimeCommandTypedContract(command);
  }
  return true;
}

bool validateAndParseRuntimeCommandPayload(const std::string& command,
                                          const std::string& payload_json,
                                          RuntimeCommandRequest* parsed,
                                          std::string* error) {
  const auto* contract = findRuntimeCommandTypedContract(command);
  if (contract == nullptr) {
    if (error != nullptr) *error = "unsupported command";
    return false;
  }
  RuntimeCommandRequest local;
  local.command = command;
  for (const auto& field : contract->request_contract.fields) {
    if (!validateField(field, payload_json, &local, error)) {
      return false;
    }
  }
  if (parsed != nullptr) {
    *parsed = std::move(local);
  }
  return true;
}

bool validateRuntimeCommandGuard(const std::string& command,
                                 RobotCoreState state,
                                 CommandRuntimeLane lane,
                                 std::string* error) {
  const auto* contract = findRuntimeCommandTypedContract(command);
  if (contract == nullptr) {
    if (error != nullptr) *error = "unsupported command";
    return false;
  }
  const auto& guard = contract->guard_contract;
  if (guard.lane != lane) {
    if (error != nullptr) *error = "command lane does not match typed guard contract";
    return false;
  }
  const auto allowed_states = splitSignature(guard.allowed_states_signature);
  if (!allowed_states.empty() && std::find(allowed_states.begin(), allowed_states.end(), std::string{"*"}) == allowed_states.end()) {
    const auto runtime_state_name = commandRegistryStateName(state);
    if (std::find(allowed_states.begin(), allowed_states.end(), runtime_state_name) == allowed_states.end()) {
      if (error != nullptr) {
        *error = command + " requires state in [" + std::string(guard.allowed_states_signature == nullptr ? "" : guard.allowed_states_signature) + "] but current state is " + runtime_state_name;
      }
      return false;
    }
  }
  return true;
}

bool validateRuntimeCommandReplyEnvelope(const std::string& command,
                                         const std::string& reply_json,
                                         std::string* error) {
  const auto* contract = findRuntimeCommandTypedContract(command);
  if (contract == nullptr) {
    if (error != nullptr) *error = "unsupported command";
    return false;
  }
  const auto& response = contract->response_contract;
  for (const auto& field_name : splitSignature(response.envelope_fields_signature)) {
    if (!hasJsonKey(reply_json, field_name)) {
      if (error != nullptr) *error = "reply envelope missing required field: " + field_name;
      return false;
    }
  }
  if (response.read_only) {
    const auto data_json = json::extractObject(reply_json, "data", "");
    if (data_json.empty()) {
      if (error != nullptr) *error = "reply envelope missing required data object";
      return false;
    }
    const auto required_data_fields = splitSignature(response.data_required_fields_signature);
    if (!required_data_fields.empty()) {
      for (const auto& field_name : required_data_fields) {
        if (!hasJsonKey(data_json, field_name)) {
          if (error != nullptr) *error = "reply data missing required field: " + field_name;
          return false;
        }
      }
    } else {
      const std::string token = response.data_contract_token == nullptr ? std::string{} : std::string(response.data_contract_token);
      if (!token.empty() && !hasJsonKey(data_json, token)) {
        if (error != nullptr) *error = "reply data missing required contract field: " + token;
        return false;
      }
    }
    for (const auto& field : response.data_fields) {
      std::string field_error;
      if (!validateField(field, data_json, nullptr, &field_error)) {
        if (error != nullptr) *error = "reply data field validation failed for '" + std::string(field.name == nullptr ? "" : field.name) + "': " + field_error;
        return false;
      }
    }
  }
  return true;
}

}  // namespace robot_core
