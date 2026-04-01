#pragma once

#include <cstdint>
#include <string>
#include <vector>

namespace google::protobuf {
class Message {
 public:
  virtual ~Message() = default;
  virtual bool SerializeToString(std::string* output) const = 0;
  virtual bool ParseFromString(const std::string& input) = 0;
};
}  // namespace google::protobuf

namespace spine_core {

class Command final : public google::protobuf::Message {
 public:
  int32_t protocol_version() const noexcept { return protocol_version_; }
  void set_protocol_version(int32_t value) noexcept { protocol_version_ = value; }

  const std::string& command() const noexcept { return command_; }
  void set_command(const std::string& value) { command_ = value; }
  void set_command(const char* value) { command_ = value ? value : ""; }
  void set_command(std::string&& value) noexcept { command_ = std::move(value); }

  const std::string& payload_json() const noexcept { return payload_json_; }
  void set_payload_json(const std::string& value) { payload_json_ = value; }
  void set_payload_json(const char* value) { payload_json_ = value ? value : ""; }
  void set_payload_json(std::string&& value) noexcept { payload_json_ = std::move(value); }

  const std::string& request_id() const noexcept { return request_id_; }
  void set_request_id(const std::string& value) { request_id_ = value; }
  void set_request_id(const char* value) { request_id_ = value ? value : ""; }
  void set_request_id(std::string&& value) noexcept { request_id_ = std::move(value); }

  bool SerializeToString(std::string* output) const override;
  bool ParseFromString(const std::string& input) override;

 private:
  int32_t protocol_version_{0};
  std::string command_;
  std::string payload_json_;
  std::string request_id_;
};

class Reply final : public google::protobuf::Message {
 public:
  int32_t protocol_version() const noexcept { return protocol_version_; }
  void set_protocol_version(int32_t value) noexcept { protocol_version_ = value; }

  bool ok() const noexcept { return ok_; }
  void set_ok(bool value) noexcept { ok_ = value; }

  const std::string& message() const noexcept { return message_; }
  void set_message(const std::string& value) { message_ = value; }
  void set_message(const char* value) { message_ = value ? value : ""; }
  void set_message(std::string&& value) noexcept { message_ = std::move(value); }

  const std::string& request_id() const noexcept { return request_id_; }
  void set_request_id(const std::string& value) { request_id_ = value; }
  void set_request_id(const char* value) { request_id_ = value ? value : ""; }
  void set_request_id(std::string&& value) noexcept { request_id_ = std::move(value); }

  const std::string& data_json() const noexcept { return data_json_; }
  void set_data_json(const std::string& value) { data_json_ = value; }
  void set_data_json(const char* value) { data_json_ = value ? value : ""; }
  void set_data_json(std::string&& value) noexcept { data_json_ = std::move(value); }

  bool SerializeToString(std::string* output) const override;
  bool ParseFromString(const std::string& input) override;

 private:
  int32_t protocol_version_{0};
  bool ok_{false};
  std::string message_;
  std::string request_id_;
  std::string data_json_;
};

class TelemetryEnvelope final : public google::protobuf::Message {
 public:
  int32_t protocol_version() const noexcept { return protocol_version_; }
  void set_protocol_version(int32_t value) noexcept { protocol_version_ = value; }

  const std::string& topic() const noexcept { return topic_; }
  void set_topic(const std::string& value) { topic_ = value; }
  void set_topic(const char* value) { topic_ = value ? value : ""; }
  void set_topic(std::string&& value) noexcept { topic_ = std::move(value); }

  int64_t ts_ns() const noexcept { return ts_ns_; }
  void set_ts_ns(int64_t value) noexcept { ts_ns_ = value; }

  const std::string& data_json() const noexcept { return data_json_; }
  void set_data_json(const std::string& value) { data_json_ = value; }
  void set_data_json(const char* value) { data_json_ = value ? value : ""; }
  void set_data_json(std::string&& value) noexcept { data_json_ = std::move(value); }

  bool SerializeToString(std::string* output) const override;
  bool ParseFromString(const std::string& input) override;

 private:
  int32_t protocol_version_{0};
  std::string topic_;
  int64_t ts_ns_{0};
  std::string data_json_;
};

class RobotTelemetry final : public google::protobuf::Message {
 public:
  int32_t protocol_version() const noexcept { return protocol_version_; }
  void set_protocol_version(int32_t value) noexcept { protocol_version_ = value; }

  const std::string& topic() const noexcept { return topic_; }
  void set_topic(const std::string& value) { topic_ = value; }
  void set_topic(const char* value) { topic_ = value ? value : ""; }
  void set_topic(std::string&& value) noexcept { topic_ = std::move(value); }

  int64_t ts_ns() const noexcept { return ts_ns_; }
  void set_ts_ns(int64_t value) noexcept { ts_ns_ = value; }

  const std::vector<double>& tcp_pose_measured() const noexcept { return tcp_pose_measured_; }
  std::vector<double>* mutable_tcp_pose_measured() noexcept { return &tcp_pose_measured_; }
  void clear_tcp_pose_measured() noexcept { tcp_pose_measured_.clear(); }
  void add_tcp_pose_measured(double value) { tcp_pose_measured_.push_back(value); }

  const std::vector<double>& joint_pos() const noexcept { return joint_pos_; }
  std::vector<double>* mutable_joint_pos() noexcept { return &joint_pos_; }
  void clear_joint_pos() noexcept { joint_pos_.clear(); }
  void add_joint_pos(double value) { joint_pos_.push_back(value); }

  const std::vector<double>& joint_torque() const noexcept { return joint_torque_; }
  std::vector<double>* mutable_joint_torque() noexcept { return &joint_torque_; }
  void clear_joint_torque() noexcept { joint_torque_.clear(); }
  void add_joint_torque(double value) { joint_torque_.push_back(value); }

  double actual_force_z() const noexcept { return actual_force_z_; }
  void set_actual_force_z(double value) noexcept { actual_force_z_ = value; }

  int32_t safety_status() const noexcept { return safety_status_; }
  void set_safety_status(int32_t value) noexcept { safety_status_ = value; }

  double quality_score() const noexcept { return quality_score_; }
  void set_quality_score(double value) noexcept { quality_score_ = value; }

  bool SerializeToString(std::string* output) const override;
  bool ParseFromString(const std::string& input) override;

 private:
  int32_t protocol_version_{0};
  std::string topic_;
  int64_t ts_ns_{0};
  std::vector<double> tcp_pose_measured_;
  std::vector<double> joint_pos_;
  std::vector<double> joint_torque_;
  double actual_force_z_{0.0};
  int32_t safety_status_{0};
  double quality_score_{0.0};
};

class CommandPose final : public google::protobuf::Message {
 public:
  const std::vector<double>& tcp_pose_td() const noexcept { return tcp_pose_td_; }
  std::vector<double>* mutable_tcp_pose_td() noexcept { return &tcp_pose_td_; }
  void clear_tcp_pose_td() noexcept { tcp_pose_td_.clear(); }
  void add_tcp_pose_td(double value) { tcp_pose_td_.push_back(value); }

  int64_t timestamp_ns() const noexcept { return timestamp_ns_; }
  void set_timestamp_ns(int64_t value) noexcept { timestamp_ns_ = value; }

  bool SerializeToString(std::string* output) const override;
  bool ParseFromString(const std::string& input) override;

 private:
  std::vector<double> tcp_pose_td_;
  int64_t timestamp_ns_{0};
};

}  // namespace spine_core
