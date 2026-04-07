#include "ipc_messages.pb.h"

#include <array>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <limits>
#include <string>
#include <string_view>
#include <utility>
#include <vector>

namespace {

using ByteVec = std::string;

template <typename To, typename From>
To bitCopy(const From& value) {
  static_assert(sizeof(To) == sizeof(From), "bitCopy requires identical sizes");
  To out{};
  std::memcpy(&out, &value, sizeof(To));
  return out;
}

void appendVarint(ByteVec& out, uint64_t value) {
  while (value >= 0x80) {
    out.push_back(static_cast<char>((value & 0x7F) | 0x80));
    value >>= 7;
  }
  out.push_back(static_cast<char>(value));
}

bool readVarint(std::string_view input, size_t& offset, uint64_t& value) {
  value = 0;
  int shift = 0;
  while (offset < input.size() && shift <= 63) {
    const uint8_t byte = static_cast<uint8_t>(input[offset++]);
    value |= static_cast<uint64_t>(byte & 0x7F) << shift;
    if ((byte & 0x80u) == 0) {
      return true;
    }
    shift += 7;
  }
  return false;
}

void appendTag(ByteVec& out, uint32_t field_number, uint8_t wire_type) {
  appendVarint(out, (static_cast<uint64_t>(field_number) << 3) | wire_type);
}

void appendStringField(ByteVec& out, uint32_t field_number, const std::string& value) {
  if (value.empty()) {
    return;
  }
  appendTag(out, field_number, 2);
  appendVarint(out, value.size());
  out.append(value);
}

void appendBoolField(ByteVec& out, uint32_t field_number, bool value) {
  if (!value) {
    return;
  }
  appendTag(out, field_number, 0);
  appendVarint(out, value ? 1u : 0u);
}

void appendInt32Field(ByteVec& out, uint32_t field_number, int32_t value) {
  if (value == 0) {
    return;
  }
  appendTag(out, field_number, 0);
  appendVarint(out, static_cast<uint64_t>(static_cast<int64_t>(value)));
}

void appendInt64Field(ByteVec& out, uint32_t field_number, int64_t value) {
  if (value == 0) {
    return;
  }
  appendTag(out, field_number, 0);
  appendVarint(out, static_cast<uint64_t>(value));
}

void appendDoubleField(ByteVec& out, uint32_t field_number, double value) {
  if (value == 0.0) {
    return;
  }
  appendTag(out, field_number, 1);
  const uint64_t bits = bitCopy<uint64_t>(value);
  for (int i = 0; i < 8; ++i) {
    out.push_back(static_cast<char>((bits >> (8 * i)) & 0xFFu));
  }
}

void appendPackedDoubleField(ByteVec& out, uint32_t field_number, const std::vector<double>& values) {
  if (values.empty()) {
    return;
  }
  appendTag(out, field_number, 2);
  appendVarint(out, values.size() * sizeof(double));
  for (double value : values) {
    const uint64_t bits = bitCopy<uint64_t>(value);
    for (int i = 0; i < 8; ++i) {
      out.push_back(static_cast<char>((bits >> (8 * i)) & 0xFFu));
    }
  }
}

bool readLengthDelimited(std::string_view input, size_t& offset, std::string& value) {
  uint64_t len = 0;
  if (!readVarint(input, offset, len)) {
    return false;
  }
  if (len > input.size() - offset) {
    return false;
  }
  value.assign(input.substr(offset, static_cast<size_t>(len)));
  offset += static_cast<size_t>(len);
  return true;
}

bool readFixed64(std::string_view input, size_t& offset, uint64_t& value) {
  if (input.size() - offset < sizeof(uint64_t)) {
    return false;
  }
  value = 0;
  for (int i = 0; i < 8; ++i) {
    value |= static_cast<uint64_t>(static_cast<uint8_t>(input[offset + i])) << (8 * i);
  }
  offset += sizeof(uint64_t);
  return true;
}

bool readDouble(std::string_view input, size_t& offset, double& value) {
  uint64_t bits = 0;
  if (!readFixed64(input, offset, bits)) {
    return false;
  }
  value = bitCopy<double>(bits);
  return true;
}

bool readPackedDoubleField(std::string_view input, size_t& offset, std::vector<double>& target) {
  uint64_t len = 0;
  if (!readVarint(input, offset, len)) {
    return false;
  }
  if (len > input.size() - offset || (len % sizeof(double)) != 0) {
    return false;
  }
  const size_t end = offset + static_cast<size_t>(len);
  while (offset < end) {
    double value = 0.0;
    if (!readDouble(input, offset, value)) {
      return false;
    }
    target.push_back(value);
  }
  return offset == end;
}

bool skipField(std::string_view input, size_t& offset, uint8_t wire_type) {
  switch (wire_type) {
    case 0: {
      uint64_t unused = 0;
      return readVarint(input, offset, unused);
    }
    case 1:
      if (input.size() - offset < sizeof(uint64_t)) {
        return false;
      }
      offset += sizeof(uint64_t);
      return true;
    case 2: {
      uint64_t len = 0;
      if (!readVarint(input, offset, len) || len > input.size() - offset) {
        return false;
      }
      offset += static_cast<size_t>(len);
      return true;
    }
    case 5:
      if (input.size() - offset < sizeof(uint32_t)) {
        return false;
      }
      offset += sizeof(uint32_t);
      return true;
    default:
      return false;
  }
}

}  // namespace

namespace spine_core {

bool Command::SerializeToString(std::string* output) const {
  if (output == nullptr) {
    return false;
  }
  ByteVec encoded;
  appendInt32Field(encoded, 1, protocol_version_);
  appendStringField(encoded, 2, command_);
  appendStringField(encoded, 3, payload_json_);
  appendStringField(encoded, 4, request_id_);
  *output = std::move(encoded);
  return true;
}

bool Command::ParseFromString(const std::string& input) {
  protocol_version_ = 0;
  command_.clear();
  payload_json_.clear();
  request_id_.clear();
  std::string_view view(input);
  size_t offset = 0;
  while (offset < view.size()) {
    uint64_t tag = 0;
    if (!readVarint(view, offset, tag)) {
      return false;
    }
    const uint32_t field = static_cast<uint32_t>(tag >> 3);
    const uint8_t wire = static_cast<uint8_t>(tag & 0x07u);
    switch (field) {
      case 1: {
        if (wire != 0) return false;
        uint64_t value = 0;
        if (!readVarint(view, offset, value)) return false;
        protocol_version_ = static_cast<int32_t>(value);
        break;
      }
      case 2:
        if (wire != 2 || !readLengthDelimited(view, offset, command_)) return false;
        break;
      case 3:
        if (wire != 2 || !readLengthDelimited(view, offset, payload_json_)) return false;
        break;
      case 4:
        if (wire != 2 || !readLengthDelimited(view, offset, request_id_)) return false;
        break;
      default:
        if (!skipField(view, offset, wire)) return false;
        break;
    }
  }
  return true;
}

bool Reply::SerializeToString(std::string* output) const {
  if (output == nullptr) {
    return false;
  }
  ByteVec encoded;
  appendInt32Field(encoded, 1, protocol_version_);
  appendBoolField(encoded, 2, ok_);
  appendStringField(encoded, 3, message_);
  appendStringField(encoded, 4, request_id_);
  appendStringField(encoded, 5, data_json_);
  *output = std::move(encoded);
  return true;
}

bool Reply::ParseFromString(const std::string& input) {
  protocol_version_ = 0;
  ok_ = false;
  message_.clear();
  request_id_.clear();
  data_json_.clear();
  std::string_view view(input);
  size_t offset = 0;
  while (offset < view.size()) {
    uint64_t tag = 0;
    if (!readVarint(view, offset, tag)) {
      return false;
    }
    const uint32_t field = static_cast<uint32_t>(tag >> 3);
    const uint8_t wire = static_cast<uint8_t>(tag & 0x07u);
    switch (field) {
      case 1: {
        if (wire != 0) return false;
        uint64_t value = 0;
        if (!readVarint(view, offset, value)) return false;
        protocol_version_ = static_cast<int32_t>(value);
        break;
      }
      case 2: {
        if (wire != 0) return false;
        uint64_t value = 0;
        if (!readVarint(view, offset, value)) return false;
        ok_ = value != 0;
        break;
      }
      case 3:
        if (wire != 2 || !readLengthDelimited(view, offset, message_)) return false;
        break;
      case 4:
        if (wire != 2 || !readLengthDelimited(view, offset, request_id_)) return false;
        break;
      case 5:
        if (wire != 2 || !readLengthDelimited(view, offset, data_json_)) return false;
        break;
      default:
        if (!skipField(view, offset, wire)) return false;
        break;
    }
  }
  return true;
}

bool TelemetryEnvelope::SerializeToString(std::string* output) const {
  if (output == nullptr) {
    return false;
  }
  ByteVec encoded;
  appendInt32Field(encoded, 1, protocol_version_);
  appendStringField(encoded, 2, topic_);
  appendInt64Field(encoded, 3, ts_ns_);
  appendStringField(encoded, 4, data_json_);
  *output = std::move(encoded);
  return true;
}

bool TelemetryEnvelope::ParseFromString(const std::string& input) {
  protocol_version_ = 0;
  topic_.clear();
  ts_ns_ = 0;
  data_json_.clear();
  std::string_view view(input);
  size_t offset = 0;
  while (offset < view.size()) {
    uint64_t tag = 0;
    if (!readVarint(view, offset, tag)) {
      return false;
    }
    const uint32_t field = static_cast<uint32_t>(tag >> 3);
    const uint8_t wire = static_cast<uint8_t>(tag & 0x07u);
    switch (field) {
      case 1: {
        if (wire != 0) return false;
        uint64_t value = 0;
        if (!readVarint(view, offset, value)) return false;
        protocol_version_ = static_cast<int32_t>(value);
        break;
      }
      case 2:
        if (wire != 2 || !readLengthDelimited(view, offset, topic_)) return false;
        break;
      case 3: {
        if (wire != 0) return false;
        uint64_t value = 0;
        if (!readVarint(view, offset, value)) return false;
        ts_ns_ = static_cast<int64_t>(value);
        break;
      }
      case 4:
        if (wire != 2 || !readLengthDelimited(view, offset, data_json_)) return false;
        break;
      default:
        if (!skipField(view, offset, wire)) return false;
        break;
    }
  }
  return true;
}

bool RobotTelemetry::SerializeToString(std::string* output) const {
  if (output == nullptr) {
    return false;
  }
  ByteVec encoded;
  appendInt32Field(encoded, 1, protocol_version_);
  appendStringField(encoded, 2, topic_);
  appendInt64Field(encoded, 3, ts_ns_);
  appendPackedDoubleField(encoded, 4, tcp_pose_measured_);
  appendPackedDoubleField(encoded, 5, joint_pos_);
  appendPackedDoubleField(encoded, 6, joint_torque_);
  appendDoubleField(encoded, 7, actual_force_z_);
  appendInt32Field(encoded, 8, safety_status_);
  appendDoubleField(encoded, 9, quality_score_);
  *output = std::move(encoded);
  return true;
}

bool RobotTelemetry::ParseFromString(const std::string& input) {
  protocol_version_ = 0;
  topic_.clear();
  ts_ns_ = 0;
  tcp_pose_measured_.clear();
  joint_pos_.clear();
  joint_torque_.clear();
  actual_force_z_ = 0.0;
  safety_status_ = 0;
  quality_score_ = 0.0;
  std::string_view view(input);
  size_t offset = 0;
  while (offset < view.size()) {
    uint64_t tag = 0;
    if (!readVarint(view, offset, tag)) {
      return false;
    }
    const uint32_t field = static_cast<uint32_t>(tag >> 3);
    const uint8_t wire = static_cast<uint8_t>(tag & 0x07u);
    switch (field) {
      case 1: {
        if (wire != 0) return false;
        uint64_t value = 0;
        if (!readVarint(view, offset, value)) return false;
        protocol_version_ = static_cast<int32_t>(value);
        break;
      }
      case 2:
        if (wire != 2 || !readLengthDelimited(view, offset, topic_)) return false;
        break;
      case 3: {
        if (wire != 0) return false;
        uint64_t value = 0;
        if (!readVarint(view, offset, value)) return false;
        ts_ns_ = static_cast<int64_t>(value);
        break;
      }
      case 4:
        if (wire == 2) {
          if (!readPackedDoubleField(view, offset, tcp_pose_measured_)) return false;
        } else if (wire == 1) {
          double value = 0.0;
          if (!readDouble(view, offset, value)) return false;
          tcp_pose_measured_.push_back(value);
        } else {
          return false;
        }
        break;
      case 5:
        if (wire == 2) {
          if (!readPackedDoubleField(view, offset, joint_pos_)) return false;
        } else if (wire == 1) {
          double value = 0.0;
          if (!readDouble(view, offset, value)) return false;
          joint_pos_.push_back(value);
        } else {
          return false;
        }
        break;
      case 6:
        if (wire == 2) {
          if (!readPackedDoubleField(view, offset, joint_torque_)) return false;
        } else if (wire == 1) {
          double value = 0.0;
          if (!readDouble(view, offset, value)) return false;
          joint_torque_.push_back(value);
        } else {
          return false;
        }
        break;
      case 7:
        if (wire != 1 || !readDouble(view, offset, actual_force_z_)) return false;
        break;
      case 8: {
        if (wire != 0) return false;
        uint64_t value = 0;
        if (!readVarint(view, offset, value)) return false;
        safety_status_ = static_cast<int32_t>(value);
        break;
      }
      case 9:
        if (wire != 1 || !readDouble(view, offset, quality_score_)) return false;
        break;
      default:
        if (!skipField(view, offset, wire)) return false;
        break;
    }
  }
  return true;
}

bool CommandPose::SerializeToString(std::string* output) const {
  if (output == nullptr) {
    return false;
  }
  ByteVec encoded;
  appendPackedDoubleField(encoded, 1, tcp_pose_td_);
  appendInt64Field(encoded, 2, timestamp_ns_);
  *output = std::move(encoded);
  return true;
}

bool CommandPose::ParseFromString(const std::string& input) {
  tcp_pose_td_.clear();
  timestamp_ns_ = 0;
  std::string_view view(input);
  size_t offset = 0;
  while (offset < view.size()) {
    uint64_t tag = 0;
    if (!readVarint(view, offset, tag)) {
      return false;
    }
    const uint32_t field = static_cast<uint32_t>(tag >> 3);
    const uint8_t wire = static_cast<uint8_t>(tag & 0x07u);
    switch (field) {
      case 1:
        if (wire == 2) {
          if (!readPackedDoubleField(view, offset, tcp_pose_td_)) return false;
        } else if (wire == 1) {
          double value = 0.0;
          if (!readDouble(view, offset, value)) return false;
          tcp_pose_td_.push_back(value);
        } else {
          return false;
        }
        break;
      case 2: {
        if (wire != 0) return false;
        uint64_t value = 0;
        if (!readVarint(view, offset, value)) return false;
        timestamp_ns_ = static_cast<int64_t>(value);
        break;
      }
      default:
        if (!skipField(view, offset, wire)) return false;
        break;
    }
  }
  return true;
}

}  // namespace spine_core
