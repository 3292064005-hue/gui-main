#pragma once

#include <array>
#include <map>
#include <string>
#include <vector>

#include "json_utils.h"
#include "robot_core/robot_identity_contract.h"
#include "robot_core/sdk_robot_facade.h"

namespace robot_core::query_json {

inline std::string objectArray(const std::vector<std::string>& entries) {
  std::string out = "[";
  for (size_t idx = 0; idx < entries.size(); ++idx) {
    if (idx > 0) out += ",";
    out += entries[idx];
  }
  out += "]";
  return out;
}

inline std::string logEntryJson(const std::string& level, const std::string& source, const std::string& message) {
  return json::object(std::vector<std::string>{
      json::field("level", json::quote(level)),
      json::field("source", json::quote(source)),
      json::field("message", json::quote(message)),
  });
}

inline std::string boolMapJson(const std::map<std::string, bool>& items) {
  std::vector<std::string> fields;
  for (const auto& [key, value] : items) fields.push_back(json::field(key, json::boolLiteral(value)));
  return json::object(fields);
}

inline std::string doubleMapJson(const std::map<std::string, double>& items) {
  std::vector<std::string> fields;
  for (const auto& [key, value] : items) fields.push_back(json::field(key, json::formatDouble(value)));
  return json::object(fields);
}

inline std::string intMapJson(const std::map<std::string, int>& items) {
  std::vector<std::string> fields;
  for (const auto& [key, value] : items) fields.push_back(json::field(key, std::to_string(value)));
  return json::object(fields);
}

inline std::string projectArrayJson(const std::vector<SdkRobotProjectInfo>& projects) {
  std::vector<std::string> entries;
  for (const auto& project : projects) {
    entries.push_back(json::object(std::vector<std::string>{
        json::field("name", json::quote(project.name)),
        json::field("tasks", json::stringArray(project.tasks)),
    }));
  }
  return objectArray(entries);
}

inline std::string pathArrayJson(const std::vector<SdkRobotPathInfo>& paths) {
  std::vector<std::string> entries;
  for (const auto& path : paths) {
    entries.push_back(json::object(std::vector<std::string>{
        json::field("name", json::quote(path.name)),
        json::field("rate", json::formatDouble(path.rate)),
        json::field("points", std::to_string(path.points)),
    }));
  }
  return objectArray(entries);
}

inline std::string vectorJson(const std::vector<double>& values) { return json::array(values); }

inline std::string dhArrayJson(const std::vector<OfficialDhParameter>& params) {
  std::vector<std::string> entries;
  for (const auto& item : params) {
    entries.push_back(json::object(std::vector<std::string>{
        json::field("joint", std::to_string(item.joint)),
        json::field("a_mm", json::formatDouble(item.a_mm)),
        json::field("alpha_rad", json::formatDouble(item.alpha_rad, 4)),
        json::field("d_mm", json::formatDouble(item.d_mm)),
        json::field("theta_rad", json::formatDouble(item.theta_rad, 4)),
    }));
  }
  return objectArray(entries);
}

inline std::vector<double> array6ToVector(const std::array<double, 6>& values) { return std::vector<double>(values.begin(), values.end()); }
inline std::vector<double> array16ToVector(const std::array<double, 16>& values) { return std::vector<double>(values.begin(), values.end()); }
inline std::vector<double> array3ToVector(const std::array<double, 3>& values) { return std::vector<double>(values.begin(), values.end()); }

}  // namespace robot_core::query_json
