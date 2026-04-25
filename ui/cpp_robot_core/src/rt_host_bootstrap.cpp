#include "robot_core/rt_host_bootstrap.h"

#include <cerrno>
#include <cstring>
#include <pthread.h>
#include <sched.h>
#include <sys/mman.h>
#include <unistd.h>

#include <algorithm>
#include <cctype>
#include <cstdlib>
#include <filesystem>
#include <fstream>
#include <sstream>
#include <string_view>

namespace robot_core {
namespace {

bool parseBoolEnv(const char* name, bool default_value) {
  const char* raw = std::getenv(name);
  if (raw == nullptr) return default_value;
  std::string value(raw);
  std::transform(value.begin(), value.end(), value.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
  if (value == "1" || value == "true" || value == "on" || value == "yes") return true;
  if (value == "0" || value == "false" || value == "off" || value == "no") return false;
  return default_value;
}

int parseIntEnv(const char* name, int default_value) {
  const char* raw = std::getenv(name);
  if (raw == nullptr || std::string(raw).empty()) return default_value;
  try {
    return std::stoi(raw);
  } catch (...) {
    return default_value;
  }
}

std::string parseStringEnv(const char* name, const std::string& default_value = {}) {
  const char* raw = std::getenv(name);
  if (raw == nullptr || std::string(raw).empty()) return default_value;
  return std::string(raw);
}

std::vector<int> parseCpuAffinityEnv(const char* name) {
  const char* raw = std::getenv(name);
  if (raw == nullptr || std::string(raw).empty()) return {};
  std::vector<int> cpus;
  std::stringstream ss(raw);
  std::string item;
  while (std::getline(ss, item, ',')) {
    item.erase(std::remove_if(item.begin(), item.end(), [](unsigned char ch) { return std::isspace(ch) != 0; }), item.end());
    if (item.empty()) continue;
    try {
      const int cpu = std::stoi(item);
      if (cpu < 0) {
        return {};
      }
      cpus.push_back(cpu);
    } catch (...) {
      return {};
    }
  }
  return cpus;
}

int schedulerPolicyFromString(const std::string& policy) {
  std::string normalized(policy);
  std::transform(normalized.begin(), normalized.end(), normalized.begin(), [](unsigned char ch) { return static_cast<char>(std::tolower(ch)); });
  if (normalized == "fifo") return SCHED_FIFO;
  if (normalized == "rr") return SCHED_RR;
  return SCHED_OTHER;
}

std::string schedulerPolicyName(int policy) {
  switch (policy) {
    case SCHED_FIFO: return "fifo";
    case SCHED_RR: return "rr";
    default: return "other";
  }
}

bool hostReportsPreemptRt() {
  const std::filesystem::path realtime_flag("/sys/kernel/realtime");
  if (!std::filesystem::exists(realtime_flag)) return false;
  try {
    const auto content = parseStringEnv("SPINE_RT_FORCE_PREEMPT_RT_FLAG", "");
    if (!content.empty()) {
      return content == "1";
    }
    std::ifstream stream(realtime_flag);
    std::string value;
    stream >> value;
    return value == "1";
  } catch (...) {
    return false;
  }
}

std::string currentHostId() {
  char buffer[256]{};
  if (gethostname(buffer, sizeof(buffer) - 1) != 0) {
    return {};
  }
  return std::string(buffer);
}

}  // namespace

RtHostBootstrapConfig loadRtHostBootstrapConfigFromEnv() {
  RtHostBootstrapConfig cfg;
  cfg.contract_version = parseStringEnv("SPINE_RT_HOST_CONTRACT_VERSION");
  cfg.contract_label = parseStringEnv("SPINE_RT_HOST_CONTRACT_LABEL");
  cfg.expected_host_id = parseStringEnv("SPINE_RT_FIXED_HOST_ID");
  cfg.scheduler_policy = parseStringEnv("SPINE_RT_SCHED_POLICY", cfg.scheduler_policy);
  cfg.scheduler_priority = std::clamp(parseIntEnv("SPINE_RT_SCHED_PRIORITY", cfg.scheduler_priority), 0, 99);
  cfg.cpu_affinity = parseCpuAffinityEnv("SPINE_RT_CPU_SET");
  cfg.require_scheduler = parseBoolEnv("SPINE_RT_REQUIRE_SCHEDULER", cfg.require_scheduler);
  cfg.require_affinity = parseBoolEnv("SPINE_RT_REQUIRE_AFFINITY", cfg.require_affinity);
  cfg.require_memory_lock = parseBoolEnv("SPINE_RT_REQUIRE_MEMORY_LOCK", cfg.require_memory_lock);
  cfg.require_preempt_rt = parseBoolEnv("SPINE_RT_REQUIRE_PREEMPT_RT", cfg.require_preempt_rt);
  cfg.require_fixed_host_id = parseBoolEnv("SPINE_RT_REQUIRE_FIXED_HOST_ID", cfg.require_fixed_host_id);
  return cfg;
}

std::string formatCpuAffinity(const std::vector<int>& cpus) {
  std::ostringstream oss;
  for (std::size_t idx = 0; idx < cpus.size(); ++idx) {
    if (idx > 0) oss << ',';
    oss << cpus[idx];
  }
  return oss.str();
}

RtHostBootstrapReport applyRtHostBootstrap(const RtHostBootstrapConfig& config) {
  RtHostBootstrapReport report;
  report.contract_version = config.contract_version;
  report.contract_label = config.contract_label;
  report.expected_host_id = config.expected_host_id;
  report.actual_host_id = currentHostId();
  report.scheduler_policy = config.scheduler_policy;
  report.scheduler_priority = config.scheduler_priority;
  report.cpu_affinity = config.cpu_affinity;

  if (config.contract_version.empty() || config.contract_label.empty()) {
    report.failure_reason = "RT host contract metadata missing: SPINE_RT_HOST_CONTRACT_VERSION / SPINE_RT_HOST_CONTRACT_LABEL";
    return report;
  }
  if (config.require_fixed_host_id && config.expected_host_id.empty()) {
    report.failure_reason = "RT host contract missing SPINE_RT_FIXED_HOST_ID for single fixed workstation deployment";
    return report;
  }
  if (config.require_fixed_host_id && report.actual_host_id != config.expected_host_id) {
    report.failure_reason = "RT host identity mismatch: expected " + config.expected_host_id + ", actual " + report.actual_host_id;
    return report;
  }
  if (config.require_affinity && config.cpu_affinity.empty()) {
    report.failure_reason = "RT host contract missing SPINE_RT_CPU_SET";
    return report;
  }
  if (schedulerPolicyFromString(config.scheduler_policy) == SCHED_OTHER && config.require_scheduler) {
    report.failure_reason = "RT host contract requires fifo or rr scheduler policy";
    return report;
  }
  report.contract_complete = true;

  if (config.require_preempt_rt) {
    report.preempt_rt_ready = hostReportsPreemptRt();
    if (!report.preempt_rt_ready) {
      report.failure_reason = "PREEMPT_RT kernel requirement not satisfied (/sys/kernel/realtime != 1)";
      return report;
    }
  } else {
    report.preempt_rt_ready = hostReportsPreemptRt();
  }

  if (mlockall(MCL_CURRENT | MCL_FUTURE) == 0) {
    report.memory_locked = true;
  } else if (config.require_memory_lock) {
    report.failure_reason = std::string("mlockall failed: ") + std::strerror(errno);
    return report;
  }

  cpu_set_t cpuset;
  CPU_ZERO(&cpuset);
  for (int cpu : config.cpu_affinity) {
    CPU_SET(cpu, &cpuset);
  }
  if (!config.cpu_affinity.empty() && pthread_setaffinity_np(pthread_self(), sizeof(cpu_set_t), &cpuset) == 0) {
    report.affinity_configured = true;
  } else if (config.require_affinity) {
    report.failure_reason = std::string("pthread_setaffinity_np failed: ") + std::strerror(errno);
    return report;
  }

  sched_param sched{};
  sched.sched_priority = config.scheduler_priority;
  const int policy = schedulerPolicyFromString(config.scheduler_policy);
  report.scheduler_policy = schedulerPolicyName(policy);
  if (pthread_setschedparam(pthread_self(), policy, &sched) == 0) {
    report.scheduler_configured = true;
  } else if (config.require_scheduler) {
    report.failure_reason = std::string("pthread_setschedparam failed: ") + std::strerror(errno);
    return report;
  }

  report.ok = report.contract_complete &&
              (!config.require_preempt_rt || report.preempt_rt_ready) &&
              (!config.require_memory_lock || report.memory_locked) &&
              (!config.require_affinity || report.affinity_configured) &&
              (!config.require_scheduler || report.scheduler_configured);
  return report;
}

}  // namespace robot_core
