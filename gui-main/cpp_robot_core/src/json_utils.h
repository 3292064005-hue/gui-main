#pragma once

#include <chrono>
#include <filesystem>
#include <fstream>
#include <iomanip>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

namespace robot_core::json {

inline int64_t nowNs() {
  using namespace std::chrono;
  return duration_cast<nanoseconds>(steady_clock::now().time_since_epoch()).count();
}

inline std::string escape(const std::string& input) {
  std::string out;
  out.reserve(input.size() + 8);
  for (char c : input) {
    switch (c) {
      case '\\': out += "\\\\"; break;
      case '"': out += "\\\""; break;
      case '\n': out += "\\n"; break;
      case '\r': out += "\\r"; break;
      case '\t': out += "\\t"; break;
      default: out += c; break;
    }
  }
  return out;
}

inline std::string quote(const std::string& input) {
  return "\"" + escape(input) + "\"";
}

inline std::string boolLiteral(bool value) {
  return value ? "true" : "false";
}

inline std::string formatDouble(double value, int precision = 3) {
  std::ostringstream oss;
  oss << std::fixed << std::setprecision(precision) << value;
  auto out = oss.str();
  while (out.find('.') != std::string::npos && !out.empty() && out.back() == '0') {
    out.pop_back();
  }
  if (!out.empty() && out.back() == '.') {
    out.push_back('0');
  }
  return out;
}

inline std::string field(const std::string& key, const std::string& value_json) {
  return quote(key) + ":" + value_json;
}

inline std::string object(const std::vector<std::string>& fields) {
  std::ostringstream oss;
  oss << "{";
  for (size_t idx = 0; idx < fields.size(); ++idx) {
    if (idx > 0) {
      oss << ",";
    }
    oss << fields[idx];
  }
  oss << "}";
  return oss.str();
}

inline std::string array(const std::vector<double>& values) {
  std::ostringstream oss;
  oss << "[";
  for (size_t idx = 0; idx < values.size(); ++idx) {
    if (idx > 0) {
      oss << ",";
    }
    oss << formatDouble(values[idx], 4);
  }
  oss << "]";
  return oss.str();
}

inline std::string stringArray(const std::vector<std::string>& values) {
  std::ostringstream oss;
  oss << "[";
  for (size_t idx = 0; idx < values.size(); ++idx) {
    if (idx > 0) {
      oss << ",";
    }
    oss << quote(values[idx]);
  }
  oss << "]";
  return oss.str();
}

inline std::string extractString(const std::string& json_line, const std::string& key, const std::string& fallback = "") {
  const std::regex re("\"" + key + "\"\\s*:\\s*\"([^\"]*)\"");
  std::smatch match;
  if (std::regex_search(json_line, match, re)) {
    return match[1].str();
  }
  return fallback;
}

inline double extractDouble(const std::string& json_line, const std::string& key, double fallback = 0.0) {
  const std::regex re("\"" + key + "\"\\s*:\\s*(-?[0-9]+(?:\\.[0-9]+)?)");
  std::smatch match;
  if (std::regex_search(json_line, match, re)) {
    return std::stod(match[1].str());
  }
  return fallback;
}

inline int extractInt(const std::string& json_line, const std::string& key, int fallback = 0) {
  const std::regex re("\"" + key + "\"\\s*:\\s*(-?[0-9]+)");
  std::smatch match;
  if (std::regex_search(json_line, match, re)) {
    return std::stoi(match[1].str());
  }
  return fallback;
}

inline bool extractBool(const std::string& json_line, const std::string& key, bool fallback = false) {
  const std::regex re("\"" + key + "\"\\s*:\\s*(true|false)");
  std::smatch match;
  if (std::regex_search(json_line, match, re)) {
    return match[1].str() == "true";
  }
  return fallback;
}

inline std::string extractObject(const std::string& json_line, const std::string& key, const std::string& fallback = "{}") {
  const auto token = "\"" + key + "\"";
  auto key_pos = json_line.find(token);
  if (key_pos == std::string::npos) {
    return fallback;
  }
  auto colon_pos = json_line.find(':', key_pos + token.size());
  if (colon_pos == std::string::npos) {
    return fallback;
  }
  auto start = json_line.find_first_not_of(" \t\r\n", colon_pos + 1);
  if (start == std::string::npos) {
    return fallback;
  }
  if (json_line[start] != '{') {
    return fallback;
  }
  int depth = 0;
  bool in_string = false;
  bool escaped = false;
  for (size_t idx = start; idx < json_line.size(); ++idx) {
    const char ch = json_line[idx];
    if (escaped) {
      escaped = false;
      continue;
    }
    if (ch == '\\') {
      escaped = true;
      continue;
    }
    if (ch == '"') {
      in_string = !in_string;
      continue;
    }
    if (in_string) {
      continue;
    }
    if (ch == '{') {
      ++depth;
    } else if (ch == '}') {
      --depth;
      if (depth == 0) {
        return json_line.substr(start, idx - start + 1);
      }
    }
  }
  return fallback;
}

inline size_t countToken(const std::string& json_line, const std::string& token) {
  size_t count = 0;
  size_t pos = 0;
  while ((pos = json_line.find(token, pos)) != std::string::npos) {
    ++count;
    pos += token.size();
  }
  return count;
}

inline std::vector<int> extractAllInts(const std::string& json_line, const std::string& key) {
  std::vector<int> values;
  const std::regex re("\"" + key + "\"\\s*:\\s*(-?[0-9]+)");
  for (auto it = std::sregex_iterator(json_line.begin(), json_line.end(), re); it != std::sregex_iterator(); ++it) {
    values.push_back(std::stoi((*it)[1].str()));
  }
  return values;
}

inline void ensureDir(const std::filesystem::path& dir) {
  std::filesystem::create_directories(dir);
}

inline void appendLine(const std::filesystem::path& path, const std::string& line) {
  ensureDir(path.parent_path());
  std::ofstream out(path, std::ios::app);
  out << line << '\n';
}

}  // namespace robot_core::json
