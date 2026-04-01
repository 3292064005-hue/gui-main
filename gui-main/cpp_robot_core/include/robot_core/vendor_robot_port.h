#pragma once

#include <memory>
#include <string>
#include <vector>

#include "robot_core/sdk_robot_facade.h"

namespace robot_core {

struct VendorRobotPortSnapshot {
  std::string binding_mode{"contract_only"};
  std::string runtime_source{"simulated_contract"};
  std::string lifecycle_state{"disconnected"};
  bool sdk_available{false};
  bool xmate_model_available{false};
  bool motion_channel_ready{false};
  bool state_channel_ready{false};
  bool aux_channel_ready{false};
  bool control_source_exclusive{true};
  bool network_healthy{false};
  int nominal_rt_loop_hz{1000};
  std::string active_nrt_profile{"idle"};
  std::string active_rt_phase{"idle"};
  int command_sequence{0};
};

class VendorRobotPort {
public:
  virtual ~VendorRobotPort() = default;
  virtual VendorRobotPortSnapshot snapshot() const = 0;
  virtual bool connect(const std::string& remote_ip, const std::string& local_ip) = 0;
  virtual void disconnect() = 0;
  virtual bool setPower(bool on) = 0;
  virtual bool setAutoMode() = 0;
  virtual bool setManualMode() = 0;
  virtual bool configureRtMainline(const SdkRobotRuntimeConfig& config) = 0;
};

class XCoreRobotPort final : public VendorRobotPort {
public:
  explicit XCoreRobotPort(SdkRobotFacade* facade) : facade_(facade) {}
  VendorRobotPortSnapshot snapshot() const override;
  bool connect(const std::string& remote_ip, const std::string& local_ip) override;
  void disconnect() override;
  bool setPower(bool on) override;
  bool setAutoMode() override;
  bool setManualMode() override;
  bool configureRtMainline(const SdkRobotRuntimeConfig& config) override;

private:
  SdkRobotFacade* facade_{nullptr};
};

class LabRobotPort final : public VendorRobotPort {
public:
  explicit LabRobotPort(SdkRobotFacade* facade) : facade_(facade) {}
  VendorRobotPortSnapshot snapshot() const override;
  bool connect(const std::string& remote_ip, const std::string& local_ip) override;
  void disconnect() override;
  bool setPower(bool on) override;
  bool setAutoMode() override;
  bool setManualMode() override;
  bool configureRtMainline(const SdkRobotRuntimeConfig& config) override;

private:
  SdkRobotFacade* facade_{nullptr};
};

}  // namespace robot_core
