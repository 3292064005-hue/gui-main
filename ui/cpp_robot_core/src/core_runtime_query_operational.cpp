#include "robot_core/core_runtime.h"

#include "core_runtime_query_json_helpers.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {

using namespace query_json;

std::string CoreRuntime::handleOperationalQueryCommandLocked(const RuntimeCommandInvocation& invocation) {
  const auto& command = invocation.command;
  if (command == "query_controller_log") {
           const auto* request = invocation.requestAs<QueryControllerLogRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: query_controller_log");
           }
           (void)request;
           std::vector<std::string> entries;
           for (const auto& item : this->procedure_executor_.sdk_robot.queryPort().controllerLogs()) {
             entries.push_back(logEntryJson("INFO", "sdk", item));
           }
           return this->replyJson(invocation.request_id, true, "query_controller_log accepted", json::object(std::vector<std::string>{json::field("logs", objectArray(entries))}));
  }
  if (command == "query_rl_projects") {
           const auto* request = invocation.requestAs<QueryRlProjectsRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: query_rl_projects");
           }
           (void)request;
           const auto projects = projectArrayJson(this->procedure_executor_.sdk_robot.queryPort().rlProjects());
           const auto rl_status = this->procedure_executor_.sdk_robot.queryPort().rlStatus();
           const auto status = json::object(std::vector<std::string>{
               json::field("loaded_project", json::quote(rl_status.loaded_project)),
               json::field("loaded_task", json::quote(rl_status.loaded_task)),
               json::field("running", json::boolLiteral(rl_status.running)),
               json::field("rate", json::formatDouble(rl_status.rate)),
               json::field("loop", json::boolLiteral(rl_status.loop)),
           });
           return this->replyJson(invocation.request_id, true, "query_rl_projects accepted", json::object(std::vector<std::string>{json::field("projects", projects), json::field("status", status)}));
  }
  if (command == "query_path_lists") {
           const auto* request = invocation.requestAs<QueryPathListsRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: query_path_lists");
           }
           (void)request;
           const auto paths = pathArrayJson(this->procedure_executor_.sdk_robot.queryPort().pathLibrary());
           const auto drag_state = this->procedure_executor_.sdk_robot.queryPort().dragState();
           const auto drag = json::object(std::vector<std::string>{
               json::field("enabled", json::boolLiteral(drag_state.enabled)),
               json::field("space", json::quote(drag_state.space)),
               json::field("type", json::quote(drag_state.type)),
           });
           return this->replyJson(invocation.request_id, true, "query_path_lists accepted", json::object(std::vector<std::string>{json::field("paths", paths), json::field("drag", drag)}));
  }
  if (command == "get_io_snapshot") {
           const auto* request = invocation.requestAs<GetIoSnapshotRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: get_io_snapshot");
           }
           (void)request;
           const auto data = json::object(std::vector<std::string>{
               json::field("di", boolMapJson(this->procedure_executor_.sdk_robot.queryPort().di())),
               json::field("do", boolMapJson(this->procedure_executor_.sdk_robot.queryPort().doState())),
               json::field("ai", doubleMapJson(this->procedure_executor_.sdk_robot.queryPort().ai())),
               json::field("ao", doubleMapJson(this->procedure_executor_.sdk_robot.queryPort().ao())),
               json::field("registers", intMapJson(this->procedure_executor_.sdk_robot.queryPort().registers())),
               json::field("xpanel_vout_mode", json::quote(this->state_store_.config.xpanel_vout_mode)),
           });
           return this->replyJson(invocation.request_id, true, "get_io_snapshot accepted", data);
  }
  if (command == "get_register_snapshot") {
           const auto* request = invocation.requestAs<GetRegisterSnapshotRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: get_register_snapshot");
           }
           (void)request;
           const auto data = json::object(std::vector<std::string>{
               json::field("registers", intMapJson(this->procedure_executor_.sdk_robot.queryPort().registers())),
               json::field("session_id", json::quote(this->state_store_.session_id)),
               json::field("plan_hash", json::quote(this->state_store_.plan_hash))
           });
           return this->replyJson(invocation.request_id, true, "get_register_snapshot accepted", data);
  }
  if (command == "get_safety_config") {
           const auto* request = invocation.requestAs<GetSafetyConfigRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: get_safety_config");
           }
           (void)request;
           const auto data = json::object(std::vector<std::string>{
               json::field("collision_detection_enabled", json::boolLiteral(this->state_store_.config.collision_detection_enabled)),
               json::field("collision_sensitivity", std::to_string(this->state_store_.config.collision_sensitivity)),
               json::field("collision_behavior", json::quote(this->state_store_.config.collision_behavior)),
               json::field("collision_fallback_mm", json::formatDouble(this->state_store_.config.collision_fallback_mm)),
               json::field("soft_limit_enabled", json::boolLiteral(this->state_store_.config.soft_limit_enabled)),
               json::field("joint_soft_limit_margin_deg", json::formatDouble(this->state_store_.config.joint_soft_limit_margin_deg)),
               json::field("singularity_avoidance_enabled", json::boolLiteral(this->state_store_.config.singularity_avoidance_enabled))
           });
           return this->replyJson(invocation.request_id, true, "get_safety_config accepted", data);
  }
  return {};
}

}  // namespace robot_core
