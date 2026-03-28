#include <cerrno>
#include <csignal>
#include <cstring>
#include <iostream>
#include <pthread.h>
#include <sched.h>
#include <sys/mman.h>
#include <unistd.h>

#include "robot_core/command_server.h"

namespace {

robot_core::CommandServer* g_server = nullptr;

void pinThreadToIsolatedCores() {
  cpu_set_t cpuset;
  CPU_ZERO(&cpuset);
  CPU_SET(0, &cpuset);
  CPU_SET(1, &cpuset);

  const pthread_t current_thread = pthread_self();
  if (pthread_setaffinity_np(current_thread, sizeof(cpu_set_t), &cpuset) != 0) {
    std::cerr << "[Warning] Failed to set CPU affinity to isolated cores. Are you root?" << std::endl;
  } else {
    std::cout << "[RT-Core] System isolated to CPU 0,1 successfully." << std::endl;
  }
}

void lockMemoryForRt() {
  if (mlockall(MCL_CURRENT | MCL_FUTURE) == -1) {
    std::cerr << "[Warning] mlockall failed: " << std::strerror(errno)
              << " - Check LimitMEMLOCK in systemd!" << std::endl;
  } else {
    std::cout << "[RT-Core] Memory globally locked successfully. OS page faults eliminated." << std::endl;
  }
}

void handleSignal(int) {
  if (g_server != nullptr) {
    std::cout << "[spine_robot_core] shutdown requested" << std::endl;
    g_server->stop();
  }
}

}  // namespace

int main() {
  std::cout << "Starting spine_robot_core..." << std::endl;

  lockMemoryForRt();
  pinThreadToIsolatedCores();

  robot_core::CommandServer server;
  g_server = &server;
  std::signal(SIGINT, handleSignal);
  std::signal(SIGTERM, handleSignal);

  server.spin();

  g_server = nullptr;
  std::cout << "spine_robot_core stopped" << std::endl;
  return 0;
}
