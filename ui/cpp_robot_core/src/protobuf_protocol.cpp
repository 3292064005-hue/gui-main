#include "robot_core/protobuf_protocol.h"

#include <string>

#include "json_utils.h"

namespace robot_core {

spine_core::Reply dispatchProtobufCommand(CoreRuntime& runtime, const spine_core::Command& cmd) {
  spine_core::Reply reply;
  reply.set_protocol_version(kIpcProtocolVersion);
  reply.set_request_id(cmd.request_id());

  if (cmd.protocol_version() != kIpcProtocolVersion) {
    reply.set_ok(false);
    reply.set_message("protocol version mismatch");
    reply.set_data_json("{}");
    return reply;
  }

  std::string json_cmd = "{";
  json_cmd += "\"protocol_version\":" + std::to_string(cmd.protocol_version()) + ",";
  json_cmd += "\"command\":" + json::quote(cmd.command()) + ",";
  json_cmd += "\"payload\":" + cmd.payload_json() + ",";
  json_cmd += "\"request_id\":" + json::quote(cmd.request_id());
  json_cmd += "}";

  const std::string reply_json = runtime.handleCommandJson(json_cmd);
  reply.set_ok(json::extractBool(reply_json, "ok", false));
  reply.set_message(json::extractString(reply_json, "message"));
  reply.set_request_id(json::extractString(reply_json, "request_id", cmd.request_id()));
  reply.set_data_json(json::extractObject(reply_json, "data", "{}"));
  return reply;
}

}  // namespace robot_core
