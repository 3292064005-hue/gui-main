#include "robot_core/command_server.h"
#include "robot_core/protobuf_protocol.h"

#include <arpa/inet.h>
#include <netinet/in.h>
#include <sys/socket.h>
#include <unistd.h>

#include <chrono>
#include <cstdlib>
#include <filesystem>
#include <functional>
#include <initializer_list>
#include <iostream>
#include <string>

#include <openssl/err.h>
#include <openssl/ssl.h>

#include "json_utils.h"

namespace robot_core {

namespace {

int openServerSocket(int port) {
  int fd = ::socket(AF_INET, SOCK_STREAM, 0);
  if (fd < 0) {
    return -1;
  }
  int reuse = 1;
  ::setsockopt(fd, SOL_SOCKET, SO_REUSEADDR, &reuse, sizeof(reuse));
  sockaddr_in addr{};
  addr.sin_family = AF_INET;
  addr.sin_addr.s_addr = htonl(INADDR_ANY);
  addr.sin_port = htons(static_cast<uint16_t>(port));
  if (::bind(fd, reinterpret_cast<sockaddr*>(&addr), sizeof(addr)) != 0) {
    ::close(fd);
    return -1;
  }
  if (::listen(fd, 16) != 0) {
    ::close(fd);
    return -1;
  }
  return fd;
}

std::filesystem::path resolveTlsFile(
    const char* env_name,
    std::initializer_list<const char*> fallback_candidates) {
  if (const char* env_value = std::getenv(env_name)) {
    const std::filesystem::path env_path(env_value);
    if (std::filesystem::exists(env_path)) {
      return env_path;
    }
  }
  for (const char* candidate : fallback_candidates) {
    const std::filesystem::path path(candidate);
    if (std::filesystem::exists(path)) {
      return path;
    }
  }
  return {};
}

SSL_CTX* createTLSContext() {
  const auto cert_path =
      resolveTlsFile("ROBOT_CORE_TLS_CERT", {"configs/tls/runtime/robot_core_server.crt",
                                              "configs/tls/robot_core_server.crt",
                                              "../configs/tls/runtime/robot_core_server.crt",
                                              "../configs/tls/robot_core_server.crt",
                                              "../../configs/tls/runtime/robot_core_server.crt",
                                              "../../configs/tls/robot_core_server.crt"});
  const auto key_path =
      resolveTlsFile("ROBOT_CORE_TLS_KEY", {"configs/tls/runtime/robot_core_server.key",
                                             "../configs/tls/runtime/robot_core_server.key",
                                             "../../configs/tls/runtime/robot_core_server.key"});
  if (cert_path.empty() || key_path.empty()) {
    std::cerr << "TLS certificate or key not found. Set ROBOT_CORE_TLS_CERT / "
                 "ROBOT_CORE_TLS_KEY or run scripts/generate_dev_tls_cert.sh"
              << std::endl;
    return nullptr;
  }

  SSL_CTX* ctx = SSL_CTX_new(TLS_server_method());
  if (ctx == nullptr) {
    std::cerr << "Unable to create SSL context" << std::endl;
    return nullptr;
  }
  SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
  SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);
  SSL_CTX_set_mode(ctx, SSL_MODE_AUTO_RETRY);

  if (SSL_CTX_use_certificate_file(ctx, cert_path.c_str(), SSL_FILETYPE_PEM) <= 0) {
    std::cerr << "Failed to load TLS certificate from " << cert_path << std::endl;
    SSL_CTX_free(ctx);
    return nullptr;
  }
  if (SSL_CTX_use_PrivateKey_file(ctx, key_path.c_str(), SSL_FILETYPE_PEM) <= 0) {
    std::cerr << "Failed to load TLS private key from " << key_path << std::endl;
    SSL_CTX_free(ctx);
    return nullptr;
  }
  if (SSL_CTX_check_private_key(ctx) != 1) {
    std::cerr << "TLS private key does not match certificate" << std::endl;
    SSL_CTX_free(ctx);
    return nullptr;
  }
  return ctx;
}

bool sendLengthPrefixedSSL(SSL* ssl, const google::protobuf::Message& msg) {
  std::string payload;
  if (!msg.SerializeToString(&payload)) {
    return false;
  }
  const uint32_t length = htonl(static_cast<uint32_t>(payload.size()));
  if (SSL_write(ssl, &length, sizeof(length)) != static_cast<int>(sizeof(length))) {
    return false;
  }
  size_t sent = 0;
  while (sent < payload.size()) {
    const int rc = SSL_write(ssl, payload.data() + sent, static_cast<int>(payload.size() - sent));
    if (rc <= 0) {
      return false;
    }
    sent += static_cast<size_t>(rc);
  }
  return true;
}

bool receiveLengthPrefixedSSL(SSL* ssl, google::protobuf::Message& msg) {
  uint32_t length_be = 0;
  if (SSL_read(ssl, &length_be, sizeof(length_be)) != static_cast<int>(sizeof(length_be))) {
    return false;
  }
  const uint32_t length = ntohl(length_be);
  std::string payload(length, '\0');
  size_t received = 0;
  while (received < payload.size()) {
    const int rc = SSL_read(ssl, payload.data() + received, static_cast<int>(payload.size() - received));
    if (rc <= 0) {
      return false;
    }
    received += static_cast<size_t>(rc);
  }
  return msg.ParseFromString(payload);
}

struct PeriodicLoopSample {
  double period_ms{0.0};
  double execution_ms{0.0};
  double wake_jitter_ms{0.0};
  bool overrun{false};
};

class PeriodicLoopController {
public:
  explicit PeriodicLoopController(std::chrono::microseconds period) : period_(period), next_deadline_(std::chrono::steady_clock::now() + period) {}

  PeriodicLoopSample runOnce(const std::function<void()>& fn) {
    const auto scheduled_start = next_deadline_ - period_;
    std::this_thread::sleep_until(next_deadline_);
    const auto actual_start = std::chrono::steady_clock::now();
    const auto wake_jitter = std::chrono::duration_cast<std::chrono::microseconds>(actual_start - next_deadline_).count();
    fn();
    const auto finish = std::chrono::steady_clock::now();
    const auto execution = std::chrono::duration_cast<std::chrono::microseconds>(finish - actual_start).count();
    next_deadline_ += period_;
    const bool overrun = finish > next_deadline_;
    if (overrun) {
      next_deadline_ = finish + period_;
    }
    PeriodicLoopSample sample;
    sample.period_ms = static_cast<double>(period_.count()) / 1000.0;
    sample.execution_ms = static_cast<double>(execution) / 1000.0;
    sample.wake_jitter_ms = static_cast<double>(wake_jitter) / 1000.0;
    sample.overrun = overrun;
    return sample;
  }

private:
  std::chrono::microseconds period_;
  std::chrono::steady_clock::time_point next_deadline_;
};

void closeTlsSocket(int fd, SSL* ssl) {
  if (ssl != nullptr) {
    SSL_shutdown(ssl);
    SSL_free(ssl);
  }
  if (fd >= 0) {
    ::shutdown(fd, SHUT_RDWR);
    ::close(fd);
  }
}

}  // namespace

CommandServer::CommandServer(int command_port, int telemetry_port)
    : command_port_(command_port), telemetry_port_(telemetry_port) {
  SSL_library_init();
  OpenSSL_add_all_algorithms();
  SSL_load_error_strings();
  ssl_ctx_ = createTLSContext();
}

CommandServer::~CommandServer() {
  stop();
  if (ssl_ctx_ != nullptr) {
    SSL_CTX_free(ssl_ctx_);
  }
}

void CommandServer::setState(RobotCoreState state) {
  state_ = state;
  runtime_.setState(state);
}

RobotCoreState CommandServer::state() const {
  return runtime_.state();
}

void CommandServer::spin() {
  if (ssl_ctx_ == nullptr) {
    std::cerr << "robot_core TLS context is unavailable, aborting startup" << std::endl;
    return;
  }

  command_server_fd_ = openServerSocket(command_port_);
  telemetry_server_fd_ = openServerSocket(telemetry_port_);
  if (command_server_fd_ < 0 || telemetry_server_fd_ < 0) {
    std::cerr << "failed to open robot_core sockets" << std::endl;
    stop();
    return;
  }

  std::cout << "spine_robot_core command server on 0.0.0.0:" << command_port_ << std::endl;
  std::cout << "spine_robot_core telemetry server on 0.0.0.0:" << telemetry_port_ << std::endl;

  command_thread_ = std::thread(&CommandServer::commandAcceptLoop, this);
  telemetry_accept_thread_ = std::thread(&CommandServer::telemetryAcceptLoop, this);
  rt_thread_ = std::thread(&CommandServer::rtLoop, this);
  state_poll_thread_ = std::thread(&CommandServer::statePollLoop, this);
  watchdog_thread_ = std::thread(&CommandServer::watchdogLoop, this);
  telemetry_thread_ = std::thread(&CommandServer::telemetryLoop, this);

  command_thread_.join();
  telemetry_accept_thread_.join();
  rt_thread_.join();
  state_poll_thread_.join();
  watchdog_thread_.join();
  telemetry_thread_.join();
}

void CommandServer::stop() {
  stop_requested_.store(true);
  if (command_server_fd_ >= 0) {
    ::shutdown(command_server_fd_, SHUT_RDWR);
    ::close(command_server_fd_);
    command_server_fd_ = -1;
  }
  if (telemetry_server_fd_ >= 0) {
    ::shutdown(telemetry_server_fd_, SHUT_RDWR);
    ::close(telemetry_server_fd_);
    telemetry_server_fd_ = -1;
  }
  std::lock_guard<std::mutex> lock(telemetry_clients_mutex_);
  for (auto& client : telemetry_clients_) {
    closeTlsSocket(client.fd, client.ssl);
  }
  telemetry_clients_.clear();
}

void CommandServer::commandAcceptLoop() {
  while (!stop_requested_.load()) {
    const int client_fd = ::accept(command_server_fd_, nullptr, nullptr);
    if (client_fd < 0) {
      if (stop_requested_.load()) {
        return;
      }
      continue;
    }

    SSL* ssl = SSL_new(ssl_ctx_);
    if (ssl == nullptr) {
      closeTlsSocket(client_fd, nullptr);
      continue;
    }
    SSL_set_fd(ssl, client_fd);
    if (SSL_accept(ssl) <= 0) {
      closeTlsSocket(client_fd, ssl);
      continue;
    }

    spine_core::Command command;
    if (!receiveLengthPrefixedSSL(ssl, command)) {
      closeTlsSocket(client_fd, ssl);
      continue;
    }

    const auto reply = dispatchProtobufCommand(runtime_, command);
    sendLengthPrefixedSSL(ssl, reply);
    closeTlsSocket(client_fd, ssl);

    const auto snapshot = telemetry_publisher_.buildProtobufMessages(runtime_.takeTelemetrySnapshot());
    std::lock_guard<std::mutex> lock(telemetry_clients_mutex_);
    broadcastProtobufLocked(snapshot);
  }
}

void CommandServer::telemetryAcceptLoop() {
  while (!stop_requested_.load()) {
    const int client_fd = ::accept(telemetry_server_fd_, nullptr, nullptr);
    if (client_fd < 0) {
      if (stop_requested_.load()) {
        return;
      }
      continue;
    }

    SSL* ssl = SSL_new(ssl_ctx_);
    if (ssl == nullptr) {
      closeTlsSocket(client_fd, nullptr);
      continue;
    }
    SSL_set_fd(ssl, client_fd);
    if (SSL_accept(ssl) <= 0) {
      closeTlsSocket(client_fd, ssl);
      continue;
    }

    {
      std::lock_guard<std::mutex> lock(telemetry_clients_mutex_);
      telemetry_clients_.push_back(TelemetryClient{client_fd, ssl});
      const auto snapshot = telemetry_publisher_.buildProtobufMessages(runtime_.takeTelemetrySnapshot());
      broadcastProtobufLocked(snapshot);
    }
  }
}

void CommandServer::rtLoop() {
  PeriodicLoopController controller(std::chrono::microseconds(1000));
  while (!stop_requested_.load()) {
    const auto sample = controller.runOnce([this]() { runtime_.rtStep(); });
    runtime_.recordRtLoopSample(sample.period_ms, sample.execution_ms, sample.wake_jitter_ms, sample.overrun);
  }
}

void CommandServer::statePollLoop() {
  PeriodicLoopController controller(std::chrono::microseconds(4000));
  while (!stop_requested_.load()) {
    controller.runOnce([this]() { runtime_.statePollStep(); });
  }
}

void CommandServer::watchdogLoop() {
  PeriodicLoopController controller(std::chrono::milliseconds(50));
  while (!stop_requested_.load()) {
    controller.runOnce([this]() { runtime_.watchdogStep(); });
  }
}

void CommandServer::telemetryLoop() {
  PeriodicLoopController controller(std::chrono::milliseconds(50));
  while (!stop_requested_.load()) {
    controller.runOnce([this]() {
      const auto messages = telemetry_publisher_.buildProtobufMessages(runtime_.takeTelemetrySnapshot());
      std::lock_guard<std::mutex> lock(telemetry_clients_mutex_);
      broadcastProtobufLocked(messages);
    });
  }
}

void CommandServer::broadcastProtobufLocked(const std::vector<spine_core::TelemetryEnvelope>& messages) {
  std::vector<TelemetryClient> alive;
  alive.reserve(telemetry_clients_.size());
  for (auto& client : telemetry_clients_) {
    bool ok = true;
    for (const auto& msg : messages) {
      if (!sendLengthPrefixedSSL(client.ssl, msg)) {
        ok = false;
        break;
      }
    }
    if (ok) {
      alive.push_back(client);
    } else {
      closeTlsSocket(client.fd, client.ssl);
    }
  }
  telemetry_clients_ = std::move(alive);
}

}  // namespace robot_core
