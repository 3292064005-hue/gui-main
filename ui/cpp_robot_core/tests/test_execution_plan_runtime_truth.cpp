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

std::string minimalPlanJson() {
  return R"JSON({
    "scan_plan": {
      "session_id": "sess-truth",
      "plan_id": "plan-truth",
      "plan_hash": "hash-truth-001",
      "planner_version": "planner-1",
      "registration_hash": "reg-1",
      "approach_pose": {"x": 10.0, "y": 0.0, "z": 100.0, "rx": 0.0, "ry": 0.0, "rz": 0.0},
      "retreat_pose": {"x": 10.0, "y": 0.0, "z": 120.0, "rx": 0.0, "ry": 0.0, "rz": 0.0},
      "execution_constraints": {"max_segment_duration_ms": 10000, "allowed_contact_band": {"lower_n": 4.0, "upper_n": 12.0}},
      "segments": [
        {
          "segment_id": 1,
          "target_pressure": 8.0,
          "scan_direction": "caudal_to_cranial",
          "estimated_duration_ms": 1000,
          "quality_target": 0.8,
          "coverage_target": 0.8,
          "segment_hash": "seg-1-hash",
          "contact_band": {"lower_n": 4.0, "upper_n": 10.0},
          "transition_policy": "serpentine",
          "waypoints": [
            {"x": 10.0, "y": 0.0, "z": 100.0, "rx": 0.0, "ry": 0.0, "rz": 0.0, "sequence_index": 1, "checkpoint_tag": "wp-1"},
            {"x": 20.0, "y": 0.0, "z": 100.0, "rx": 0.0, "ry": 0.0, "rz": 0.0, "sequence_index": 2, "checkpoint_tag": "wp-2"}
          ]
        },
        {
          "segment_id": 2,
          "target_pressure": 8.0,
          "scan_direction": "caudal_to_cranial",
          "estimated_duration_ms": 1000,
          "quality_target": 0.8,
          "coverage_target": 0.8,
          "segment_hash": "seg-2-hash",
          "contact_band": {"lower_n": 4.0, "upper_n": 10.0},
          "transition_policy": "serpentine",
          "waypoints": [
            {"x": 20.0, "y": 5.0, "z": 100.0, "rx": 0.0, "ry": 0.0, "rz": 0.0, "sequence_index": 3, "checkpoint_tag": "wp-3"},
            {"x": 30.0, "y": 5.0, "z": 100.0, "rx": 0.0, "ry": 0.0, "rz": 0.0, "sequence_index": 4, "checkpoint_tag": "wp-4"}
          ]
        }
      ]
    }
  })JSON";
}

}

std::string lockSessionJson() {
  return R"JSON({
    "experiment_id": "exp-truth",
    "session_id": "sess-truth",
    "session_dir": "/tmp/spine_truth_session",
    "config_snapshot": {"home_joint_rad": [0.0, 0.3, 0.6, 0.0, 1.2, 0.0, 0.0]},
    "device_roster": {},
    "software_version": "test",
    "build_id": "test",
    "scan_plan_hash": "hash-truth-001",
    "force_sensor_provider": "mock",
    "protocol_version": 1,
    "safety_thresholds": {},
    "device_health_snapshot": {}
  })JSON";
}

int main() {
  robot_core::CoreRuntime runtime;

  auto dispatch = [&](const char* command_name, const std::string& payload_json, const char* request_id) {
    spine_core::Command cmd;
    cmd.set_protocol_version(robot_core::kIpcProtocolVersion);
    cmd.set_command(command_name);
    cmd.set_payload_json(payload_json);
    cmd.set_request_id(request_id);
    return robot_core::dispatchProtobufCommand(runtime, cmd);
  };

  if (!require(dispatch("connect_robot", "{}", "req-connect").ok(), "connect_robot should succeed")) return 1;
  if (!require(dispatch("power_on", "{}", "req-power-on").ok(), "power_on should succeed")) return 1;
  if (!require(dispatch("set_auto_mode", "{}", "req-auto").ok(), "set_auto_mode should succeed")) return 1;

  spine_core::Command lock;
  lock.set_protocol_version(robot_core::kIpcProtocolVersion);
  lock.set_command("lock_session");
  lock.set_payload_json(lockSessionJson());
  lock.set_request_id("req-lock-session");
  const auto lock_reply = robot_core::dispatchProtobufCommand(runtime, lock);
  if (!require(lock_reply.ok(), "lock_session should succeed")) return 1;

  spine_core::Command load;
  load.set_protocol_version(robot_core::kIpcProtocolVersion);
  load.set_command("load_scan_plan");
  load.set_payload_json(minimalPlanJson());
  load.set_request_id("req-load-plan");
  const auto reply = robot_core::dispatchProtobufCommand(runtime, load);
  if (!require(reply.ok(), "load_scan_plan should succeed")) return 1;

  const auto snapshot = runtime.takeTelemetrySnapshot();
  if (!require(snapshot.scan_progress.total_waypoints == 4, "total_waypoints must equal plan waypoint count")) return 1;
  if (!require(snapshot.core_state.active_segment == 1, "active segment must initialize to first segment")) return 1;
  if (!require(snapshot.scan_progress.active_waypoint_index == 0, "active waypoint must initialize to zero")) return 1;
  return 0;
}
