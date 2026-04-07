#pragma once

#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <regex>
#include <sstream>
#include <string>
#include <vector>

namespace robot_core {

struct ForceControlLimits {
    double max_z_force_n = 35.0;
    double warning_z_force_n = 25.0;
    double min_z_force_n = 5.0;
    double max_xy_force_n = 20.0;
    double desired_contact_force_n = 10.0;
    double emergency_retract_mm = 50.0;
    double force_filter_cutoff_hz = 30.0;
    double sensor_timeout_ms = 500.0;
    double stale_telemetry_ms = 250.0;
    double force_settle_window_ms = 150.0;
    double resume_force_band_n = 1.5;
};

inline double extractForceControlDouble(const std::string& json_text, const std::string& key, double fallback) {
    const std::regex re("\"" + key + "\"\\s*:\\s*(-?[0-9]+(?:\\.[0-9]+)?)");
    std::smatch match;
    if (std::regex_search(json_text, match, re)) {
        return std::stod(match[1].str());
    }
    return fallback;
}

inline std::filesystem::path resolveForceControlConfigPath() {
    if (const char* env_path = std::getenv("SPINE_FORCE_CONTROL_CONFIG")) {
        const std::filesystem::path candidate(env_path);
        if (std::filesystem::exists(candidate)) {
            return candidate;
        }
    }

    std::vector<std::filesystem::path> candidates;
#ifdef ROBOT_CORE_FORCE_CONTROL_CONFIG_PATH
    candidates.emplace_back(ROBOT_CORE_FORCE_CONTROL_CONFIG_PATH);
#endif
    const auto cwd = std::filesystem::current_path();
    candidates.emplace_back(cwd / "configs" / "force_control.json");
    candidates.emplace_back(cwd.parent_path() / "configs" / "force_control.json");
    candidates.emplace_back(cwd.parent_path().parent_path() / "configs" / "force_control.json");
    candidates.emplace_back(cwd.parent_path().parent_path().parent_path() / "configs" / "force_control.json");

    for (const auto& candidate : candidates) {
        if (!candidate.empty() && std::filesystem::exists(candidate)) {
            return candidate;
        }
    }
    return {};
}

inline ForceControlLimits loadForceControlLimits() {
    ForceControlLimits limits;
    const auto config_path = resolveForceControlConfigPath();
    if (config_path.empty()) {
        return limits;
    }

    std::ifstream input(config_path);
    if (!input) {
        return limits;
    }

    std::ostringstream buffer;
    buffer << input.rdbuf();
    const auto json_text = buffer.str();
    limits.max_z_force_n = extractForceControlDouble(json_text, "max_z_force_n", limits.max_z_force_n);
    limits.warning_z_force_n = extractForceControlDouble(json_text, "warning_z_force_n", limits.warning_z_force_n);
    limits.max_xy_force_n = extractForceControlDouble(json_text, "max_xy_force_n", limits.max_xy_force_n);
    limits.desired_contact_force_n = extractForceControlDouble(
        json_text, "desired_contact_force_n", limits.desired_contact_force_n
    );
    limits.emergency_retract_mm = extractForceControlDouble(
        json_text, "emergency_retract_mm", limits.emergency_retract_mm
    );
    limits.force_filter_cutoff_hz = extractForceControlDouble(
        json_text, "force_filter_cutoff_hz", limits.force_filter_cutoff_hz
    );
    limits.sensor_timeout_ms = extractForceControlDouble(json_text, "sensor_timeout_ms", limits.sensor_timeout_ms);
    limits.stale_telemetry_ms = extractForceControlDouble(json_text, "stale_telemetry_ms", limits.stale_telemetry_ms);
    limits.force_settle_window_ms =
        extractForceControlDouble(json_text, "force_settle_window_ms", limits.force_settle_window_ms);
    limits.resume_force_band_n = extractForceControlDouble(json_text, "resume_force_band_n", limits.resume_force_band_n);
    return limits;
}

}  // namespace robot_core
