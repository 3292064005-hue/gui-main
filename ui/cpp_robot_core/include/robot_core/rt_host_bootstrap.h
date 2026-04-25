#pragma once

#include <string>
#include <vector>

namespace robot_core {

struct RtHostBootstrapConfig {
  std::string contract_version{""};
  std::string contract_label{""};
  std::string expected_host_id{""};
  std::string actual_host_id{""};
  std::string scheduler_policy{"fifo"};
  int scheduler_priority{90};
  std::vector<int> cpu_affinity{};
  bool require_scheduler{true};
  bool require_affinity{true};
  bool require_memory_lock{true};
  bool require_preempt_rt{true};
  bool require_fixed_host_id{true};
};

struct RtHostBootstrapReport {
  bool ok{false};
  bool contract_complete{false};
  bool scheduler_configured{false};
  bool affinity_configured{false};
  bool memory_locked{false};
  bool preempt_rt_ready{false};
  std::string contract_version{""};
  std::string contract_label{""};
  std::string expected_host_id{""};
  std::string actual_host_id{""};
  std::string scheduler_policy{"fifo"};
  int scheduler_priority{90};
  std::vector<int> cpu_affinity{};
  std::string failure_reason;
};

/**
 * @brief Load RT host bootstrap policy from environment variables.
 * @return Parsed policy with fail-close defaults for the measured RT host.
 * @throws No exceptions are propagated; malformed values fall back to canonical defaults.
 * @boundary Reads only process environment and does not touch scheduler state.
 */
RtHostBootstrapConfig loadRtHostBootstrapConfigFromEnv();

/**
 * @brief Apply scheduler, affinity and memory-lock policy to the current RT host thread.
 * @param config Parsed host bootstrap policy.
 * @return Report describing which safeguards were configured and any blocking failure.
 * @throws No exceptions are propagated; errors are reported in ``failure_reason``.
 * @boundary Mutates only process/thread RT bootstrap state for the current executable.
 */
RtHostBootstrapReport applyRtHostBootstrap(const RtHostBootstrapConfig& config);

/**
 * @brief Render the configured CPU affinity set for logs / readiness evidence.
 * @param cpus Parsed affinity vector.
 * @return Comma-separated CPU list.
 * @throws No exceptions are thrown.
 * @boundary Pure formatting helper.
 */
std::string formatCpuAffinity(const std::vector<int>& cpus);

}  // namespace robot_core
