#include <csignal>
#include <iostream>

#include "robot_core/command_server.h"
#include "robot_core/rt_host_bootstrap.h"

namespace {

robot_core::CommandServer* g_server = nullptr;

void handleSignal(int) {
  if (g_server != nullptr) {
    std::cout << "[spine_robot_core] shutdown requested" << std::endl;
    g_server->stop();
  }
}

}  // namespace

int main() {
  std::cout << "Starting spine_robot_core..." << std::endl;

  const auto rt_host_config = robot_core::loadRtHostBootstrapConfigFromEnv();
  const auto rt_host_report = robot_core::applyRtHostBootstrap(rt_host_config);
  std::cout << "[RT-Core] contract_version=" << rt_host_report.contract_version
            << " contract_label=" << rt_host_report.contract_label
            << " expected_host_id=" << rt_host_report.expected_host_id
            << " actual_host_id=" << rt_host_report.actual_host_id
            << " policy=" << rt_host_report.scheduler_policy
            << " priority=" << rt_host_report.scheduler_priority
            << " cpus=" << robot_core::formatCpuAffinity(rt_host_report.cpu_affinity)
            << " preempt_rt=" << (rt_host_report.preempt_rt_ready ? "yes" : "no") << std::endl;
  if (!rt_host_report.ok) {
    std::cerr << "[RT-Core] bootstrap failed: " << rt_host_report.failure_reason << std::endl;
    return 2;
  }
  std::cout << "[RT-Core] explicit scheduler/affinity/mlock/PREEMPT_RT bootstrap complete" << std::endl;

  robot_core::CommandServer server;
  g_server = &server;
  std::signal(SIGINT, handleSignal);
  std::signal(SIGTERM, handleSignal);

  server.spin();

  g_server = nullptr;
  std::cout << "spine_robot_core stopped" << std::endl;
  return 0;
}
