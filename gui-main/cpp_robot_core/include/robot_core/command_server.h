#pragma once
#include <atomic>
#include <mutex>
#include <thread>
#include <vector>

#include "robot_core/core_runtime.h"
#include "robot_core/runtime_types.h"
#include "robot_core/telemetry_publisher.h"
#include "ipc_messages.pb.h"  // Generated protobuf header

typedef struct ssl_st SSL;
typedef struct ssl_ctx_st SSL_CTX;

namespace robot_core {
class CommandServer {
public:
  CommandServer(int command_port = 5656, int telemetry_port = 5657);
  ~CommandServer();
  void setState(RobotCoreState state);
  RobotCoreState state() const;
  void spin();
  void stop();
private:
  struct TelemetryClient {
    int fd{-1};
    SSL* ssl{nullptr};
  };

  void commandAcceptLoop();
  void telemetryAcceptLoop();
  void rtLoop();
  void statePollLoop();
  void watchdogLoop();
  void telemetryLoop();
  void broadcastProtobufLocked(const std::vector<spine_core::TelemetryEnvelope>& messages);

  RobotCoreState state_{RobotCoreState::Boot};
  int command_port_{5656};
  int telemetry_port_{5657};
  std::atomic<bool> stop_requested_{false};
  int command_server_fd_{-1};
  int telemetry_server_fd_{-1};
  mutable std::mutex telemetry_clients_mutex_;
  std::vector<TelemetryClient> telemetry_clients_;
  CoreRuntime runtime_{};
  TelemetryPublisher telemetry_publisher_{};
  std::thread command_thread_;
  std::thread telemetry_accept_thread_;
  std::thread rt_thread_;
  std::thread state_poll_thread_;
  std::thread watchdog_thread_;
  std::thread telemetry_thread_;

  // TLS support
  SSL_CTX* ssl_ctx_{nullptr};
};
}
