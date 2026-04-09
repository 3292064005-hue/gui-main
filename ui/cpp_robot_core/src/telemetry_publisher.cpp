#include "robot_core/telemetry_publisher.h"

#include "json_utils.h"
#include <chrono>

namespace robot_core {

namespace {

constexpr int kProtocolVersion = 1;

std::string stateName(RobotCoreState state) {
  switch (state) {
    case RobotCoreState::Boot: return "BOOT";
    case RobotCoreState::Disconnected: return "DISCONNECTED";
    case RobotCoreState::Connected: return "CONNECTED";
    case RobotCoreState::Powered: return "POWERED";
    case RobotCoreState::AutoReady: return "AUTO_READY";
    case RobotCoreState::SessionLocked: return "SESSION_LOCKED";
    case RobotCoreState::PathValidated: return "PATH_VALIDATED";
    case RobotCoreState::Approaching: return "APPROACHING";
    case RobotCoreState::ContactSeeking: return "CONTACT_SEEKING";
    case RobotCoreState::Scanning: return "SCANNING";
    case RobotCoreState::PausedHold: return "PAUSED_HOLD";
    case RobotCoreState::Retreating: return "RETREATING";
    case RobotCoreState::ScanComplete: return "SCAN_COMPLETE";
    case RobotCoreState::Fault: return "FAULT";
    case RobotCoreState::Estop: return "ESTOP";
  }
  return "BOOT";
}

std::string envelope(const std::string& topic, const std::string& data_json) {
  using namespace json;
  return object({
      field("topic", quote(topic)),
      field("data", data_json),
      field("ts_ns", std::to_string(json::nowNs())),
      field("protocol_version", std::to_string(kProtocolVersion)),
  });
}

std::string deviceMapJson(const std::vector<DeviceHealth>& devices) {
  using namespace json;
  std::vector<std::string> fields;
  fields.reserve(devices.size());
  for (const auto& device : devices) {
    fields.push_back(
        field(
            device.device_name,
            object({
                field("connected", boolLiteral(device.online)),
                field("health", quote(device.online ? (device.fresh ? "online" : "stale") : "offline")),
                field("detail", quote(device.detail)),
                field("fresh", boolLiteral(device.fresh)),
                field("last_ts_ns", std::to_string(device.last_ts_ns)),
            })));
  }
  return object({field("devices", object(fields))});
}

spine_core::TelemetryEnvelope makeTelemetryEnvelope(
    const std::string& topic,
    int64_t ts_ns,
    const std::string& data_json) {
  spine_core::TelemetryEnvelope msg;
  msg.set_protocol_version(kProtocolVersion);
  msg.set_topic(topic);
  msg.set_ts_ns(ts_ns);
  msg.set_data_json(data_json);
  return msg;
}

}  // namespace

std::vector<std::string> TelemetryPublisher::buildLines(const TelemetrySnapshot& snapshot) const {
  using namespace json;
  std::vector<std::string> lines;
  lines.push_back(envelope(
      "core_state",
      object({
          field("execution_state", quote(stateName(snapshot.core_state.execution_state))),
          field("armed", boolLiteral(snapshot.core_state.armed)),
          field("fault_code", quote(snapshot.core_state.fault_code)),
          field("active_segment", std::to_string(snapshot.core_state.active_segment)),
          field("progress_pct", formatDouble(snapshot.core_state.progress_pct)),
          field("session_id", quote(snapshot.core_state.session_id)),
          field("recovery_state", quote(snapshot.core_state.recovery_state)),
      })));
  lines.push_back(envelope(
      "robot_state",
      object({
          field("powered", boolLiteral(snapshot.robot_state.power_state == "on")),
          field("operate_mode", quote(snapshot.robot_state.operate_mode)),
          field("joint_pos", array(snapshot.robot_state.joint_pos)),
          field("joint_vel", array(snapshot.robot_state.joint_vel)),
          field("joint_torque", array(snapshot.robot_state.joint_torque)),
          field("cart_force", array(snapshot.robot_state.cart_force)),
          field(
              "tcp_pose",
              object({
                  field("x", snapshot.robot_state.tcp_pose.size() > 0 ? formatDouble(snapshot.robot_state.tcp_pose[0], 2) : "0.0"),
                  field("y", snapshot.robot_state.tcp_pose.size() > 1 ? formatDouble(snapshot.robot_state.tcp_pose[1], 2) : "0.0"),
                  field("z", snapshot.robot_state.tcp_pose.size() > 2 ? formatDouble(snapshot.robot_state.tcp_pose[2], 2) : "0.0"),
                  field("rx", snapshot.robot_state.tcp_pose.size() > 3 ? formatDouble(snapshot.robot_state.tcp_pose[3], 2) : "0.0"),
                  field("ry", snapshot.robot_state.tcp_pose.size() > 4 ? formatDouble(snapshot.robot_state.tcp_pose[4], 2) : "0.0"),
                  field("rz", snapshot.robot_state.tcp_pose.size() > 5 ? formatDouble(snapshot.robot_state.tcp_pose[5], 2) : "0.0"),
              })),
          field("last_event", quote(snapshot.robot_state.last_event)),
          field("last_controller_log", quote(snapshot.robot_state.last_controller_log)),
          field("runtime_source", quote(snapshot.robot_state.runtime_source)),
          field("pose_source", quote(snapshot.robot_state.pose_source)),
          field("force_source", quote(snapshot.robot_state.force_source)),
          field("pose_available", boolLiteral(snapshot.robot_state.pose_available)),
          field("force_available", boolLiteral(snapshot.robot_state.force_available)),
          field("pose_authoritative", boolLiteral(snapshot.robot_state.pose_authoritative)),
          field("force_authoritative", boolLiteral(snapshot.robot_state.force_authoritative)),
      })));
  lines.push_back(envelope(
      "contact_state",
      object({
          field("mode", quote(snapshot.contact_state.mode)),
          field("confidence", formatDouble(snapshot.contact_state.confidence)),
          field("pressure_current", formatDouble(snapshot.contact_state.pressure_current)),
          field("recommended_action", quote(snapshot.contact_state.recommended_action)),
          field("pressure_source", quote(snapshot.contact_state.pressure_source)),
          field("quality_source", quote(snapshot.contact_state.quality_source)),
          field("pressure_available", boolLiteral(snapshot.contact_state.pressure_available)),
          field("quality_available", boolLiteral(snapshot.contact_state.quality_available)),
          field("authoritative", boolLiteral(snapshot.contact_state.authoritative)),
          field("contact_stable", boolLiteral(snapshot.contact_state.contact_stable)),
      })));
  lines.push_back(envelope(
      "scan_progress",
      object({
          field("active_segment", std::to_string(snapshot.scan_progress.active_segment)),
          field("path_index", std::to_string(snapshot.scan_progress.path_index)),
          field("overall_progress", formatDouble(snapshot.scan_progress.overall_progress)),
          field("frame_id", std::to_string(snapshot.scan_progress.frame_id)),
      })));
  lines.push_back(envelope("device_health", deviceMapJson(snapshot.devices)));
  lines.push_back(envelope(
      "safety_status",
      object({
          field("safe_to_arm", boolLiteral(snapshot.safety_status.safe_to_arm)),
          field("safe_to_scan", boolLiteral(snapshot.safety_status.safe_to_scan)),
          field("active_interlocks", stringArray(snapshot.safety_status.active_interlocks)),
      })));
  lines.push_back(envelope(
      "recording_status",
      object({
          field("session_id", quote(snapshot.recorder_status.session_id)),
          field("recording", boolLiteral(snapshot.recorder_status.recording)),
          field("dropped_samples", std::to_string(snapshot.recorder_status.dropped_samples)),
          field("last_flush_ns", std::to_string(snapshot.recorder_status.last_flush_ns)),
      })));
  lines.push_back(envelope(
      "quality_feedback",
      object({
          field("image_quality", formatDouble(snapshot.quality_feedback.image_quality)),
          field("feature_confidence", formatDouble(snapshot.quality_feedback.feature_confidence)),
          field("quality_score", formatDouble(snapshot.quality_feedback.quality_score)),
          field("need_resample", boolLiteral(snapshot.quality_feedback.need_resample)),
          field("source", quote(snapshot.quality_feedback.source)),
          field("available", boolLiteral(snapshot.quality_feedback.available)),
          field("authoritative", boolLiteral(snapshot.quality_feedback.authoritative)),
      })));
  for (const auto& alarm : snapshot.alarms) {
    lines.push_back(envelope(
        "alarm_event",
        object({
            field("severity", quote(alarm.severity)),
            field("source", quote(alarm.source)),
            field("message", quote(alarm.message)),
            field("session_id", quote(alarm.session_id)),
            field("segment_id", std::to_string(alarm.segment_id)),
            field("event_ts_ns", std::to_string(alarm.event_ts_ns)),
            field("workflow_step", quote(alarm.workflow_step)),
            field("request_id", quote(alarm.request_id)),
            field("auto_action", quote(alarm.auto_action)),
        })));
  }
  return lines;
}

std::vector<spine_core::TelemetryEnvelope> TelemetryPublisher::buildProtobufMessages(
    const TelemetrySnapshot& snapshot) const {
  using namespace json;

  std::vector<spine_core::TelemetryEnvelope> messages;
  const int64_t ts = json::nowNs();

  messages.push_back(makeTelemetryEnvelope(
      "core_state",
      ts,
      object({
          field("execution_state", quote(stateName(snapshot.core_state.execution_state))),
          field("armed", boolLiteral(snapshot.core_state.armed)),
          field("fault_code", quote(snapshot.core_state.fault_code)),
          field("active_segment", std::to_string(snapshot.core_state.active_segment)),
          field("progress_pct", formatDouble(snapshot.core_state.progress_pct)),
          field("session_id", quote(snapshot.core_state.session_id)),
          field("recovery_state", quote(snapshot.core_state.recovery_state)),
      })));

  messages.push_back(makeTelemetryEnvelope(
      "robot_state",
      ts,
      object({
          field("powered", boolLiteral(snapshot.robot_state.power_state == "on")),
          field("operate_mode", quote(snapshot.robot_state.operate_mode)),
          field("joint_pos", array(snapshot.robot_state.joint_pos)),
          field("joint_vel", array(snapshot.robot_state.joint_vel)),
          field("joint_torque", array(snapshot.robot_state.joint_torque)),
          field("cart_force", array(snapshot.robot_state.cart_force)),
          field(
              "tcp_pose",
              object({
                  field("x", snapshot.robot_state.tcp_pose.size() > 0 ? formatDouble(snapshot.robot_state.tcp_pose[0], 2) : "0.0"),
                  field("y", snapshot.robot_state.tcp_pose.size() > 1 ? formatDouble(snapshot.robot_state.tcp_pose[1], 2) : "0.0"),
                  field("z", snapshot.robot_state.tcp_pose.size() > 2 ? formatDouble(snapshot.robot_state.tcp_pose[2], 2) : "0.0"),
                  field("rx", snapshot.robot_state.tcp_pose.size() > 3 ? formatDouble(snapshot.robot_state.tcp_pose[3], 2) : "0.0"),
                  field("ry", snapshot.robot_state.tcp_pose.size() > 4 ? formatDouble(snapshot.robot_state.tcp_pose[4], 2) : "0.0"),
                  field("rz", snapshot.robot_state.tcp_pose.size() > 5 ? formatDouble(snapshot.robot_state.tcp_pose[5], 2) : "0.0"),
              })),
          field("last_event", quote(snapshot.robot_state.last_event)),
          field("last_controller_log", quote(snapshot.robot_state.last_controller_log)),
          field("runtime_source", quote(snapshot.robot_state.runtime_source)),
          field("pose_source", quote(snapshot.robot_state.pose_source)),
          field("force_source", quote(snapshot.robot_state.force_source)),
          field("pose_available", boolLiteral(snapshot.robot_state.pose_available)),
          field("force_available", boolLiteral(snapshot.robot_state.force_available)),
          field("pose_authoritative", boolLiteral(snapshot.robot_state.pose_authoritative)),
          field("force_authoritative", boolLiteral(snapshot.robot_state.force_authoritative)),
      })));

  messages.push_back(makeTelemetryEnvelope(
      "contact_state",
      ts,
      object({
          field("mode", quote(snapshot.contact_state.mode)),
          field("confidence", formatDouble(snapshot.contact_state.confidence)),
          field("pressure_current", formatDouble(snapshot.contact_state.pressure_current)),
          field("recommended_action", quote(snapshot.contact_state.recommended_action)),
          field("pressure_source", quote(snapshot.contact_state.pressure_source)),
          field("quality_source", quote(snapshot.contact_state.quality_source)),
          field("pressure_available", boolLiteral(snapshot.contact_state.pressure_available)),
          field("quality_available", boolLiteral(snapshot.contact_state.quality_available)),
          field("authoritative", boolLiteral(snapshot.contact_state.authoritative)),
          field("contact_stable", boolLiteral(snapshot.contact_state.contact_stable)),
      })));

  messages.push_back(makeTelemetryEnvelope(
      "scan_progress",
      ts,
      object({
          field("active_segment", std::to_string(snapshot.scan_progress.active_segment)),
          field("path_index", std::to_string(snapshot.scan_progress.path_index)),
          field("overall_progress", formatDouble(snapshot.scan_progress.overall_progress)),
          field("frame_id", std::to_string(snapshot.scan_progress.frame_id)),
      })));

  messages.push_back(makeTelemetryEnvelope("device_health", ts, deviceMapJson(snapshot.devices)));

  messages.push_back(makeTelemetryEnvelope(
      "safety_status",
      ts,
      object({
          field("safe_to_arm", boolLiteral(snapshot.safety_status.safe_to_arm)),
          field("safe_to_scan", boolLiteral(snapshot.safety_status.safe_to_scan)),
          field("active_interlocks", stringArray(snapshot.safety_status.active_interlocks)),
      })));

  messages.push_back(makeTelemetryEnvelope(
      "recording_status",
      ts,
      object({
          field("session_id", quote(snapshot.recorder_status.session_id)),
          field("recording", boolLiteral(snapshot.recorder_status.recording)),
          field("dropped_samples", std::to_string(snapshot.recorder_status.dropped_samples)),
          field("last_flush_ns", std::to_string(snapshot.recorder_status.last_flush_ns)),
      })));

  messages.push_back(makeTelemetryEnvelope(
      "quality_feedback",
      ts,
      object({
          field("image_quality", formatDouble(snapshot.quality_feedback.image_quality)),
          field("feature_confidence", formatDouble(snapshot.quality_feedback.feature_confidence)),
          field("quality_score", formatDouble(snapshot.quality_feedback.quality_score)),
          field("need_resample", boolLiteral(snapshot.quality_feedback.need_resample)),
          field("source", quote(snapshot.quality_feedback.source)),
          field("available", boolLiteral(snapshot.quality_feedback.available)),
          field("authoritative", boolLiteral(snapshot.quality_feedback.authoritative)),
      })));

  for (const auto& alarm : snapshot.alarms) {
    messages.push_back(makeTelemetryEnvelope(
        "alarm_event",
        ts,
        object({
            field("severity", quote(alarm.severity)),
            field("source", quote(alarm.source)),
            field("message", quote(alarm.message)),
            field("session_id", quote(alarm.session_id)),
            field("segment_id", std::to_string(alarm.segment_id)),
            field("event_ts_ns", std::to_string(alarm.event_ts_ns)),
            field("workflow_step", quote(alarm.workflow_step)),
            field("request_id", quote(alarm.request_id)),
            field("auto_action", quote(alarm.auto_action)),
        })));
  }

  return messages;
}

}  // namespace robot_core
