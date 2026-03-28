#pragma once

#include <memory>
#include <atomic>
#include <chrono>
#include "../../include/spsc_queue.hpp"
#include "../../include/ipc_messages.hpp"
#include "../../include/impedance_control_manager.hpp"

// Forward declaration of ROKAE robot class to avoid dragging big dependencies into header
namespace rokae { 
    class xMateErProRobot; 
}

namespace robot_core {

enum class SensorHealthDecision {
    None,
    Hold,
    ControlledRetract,
    Estop,
};

class AdaptiveTimer {
public:
    AdaptiveTimer(double min_period_ms = 0.5, double max_period_ms = 2.0, double target_cpu = 70.0);
    ~AdaptiveTimer() = default;

    void start();
    void wait();
    double getCurrentPeriodMs() const { return current_period_ms_; }
    void adjustPeriod(double cpu_usage);

private:
    double min_period_ms_;
    double max_period_ms_;
    double target_cpu_;
    double current_period_ms_;
    std::chrono::steady_clock::time_point last_time_;
    double getCpuUsage();
};

class RtMotionService {
public:
    explicit RtMotionService(std::shared_ptr<rokae::xMateErProRobot> robot = nullptr);
    ~RtMotionService();

    // SPSC Queues exposed for IPC Server background thread insertion/extraction
    // Ensures absolutely zero locks between ZMQ Network & 1ms SDK Callback
    spine_core::SPSCQueue<spine_core_pod::CommandPose> cmd_queue{100};
    spine_core::SPSCQueue<spine_core_pod::RobotTelemetry> telemetry_queue{100};

    // Main routine to engage the 10N path tracking Real-Time loop
    bool startCartesianImpedance();
    
    // Safety triggers
    void stop();
    void controlledRetract();
    SensorHealthDecision evaluateSensorFreshnessMs(double age_ms) const;
    
    // Deprecated in favor of direct Force-Tracking, but kept for interface compatibility
    bool seekContact();
    void pauseAndHold();

private:
    std::shared_ptr<rokae::xMateErProRobot> robot_;
    std::unique_ptr<robot_core::ImpedanceControlManager> impedance_manager_;
    std::atomic<bool> is_running_{false};
    
    // Stores the last valid command for timeout checks
    spine_core_pod::CommandPose current_target_{};
    
    // Adaptive timer for dynamic frequency control
    std::unique_ptr<AdaptiveTimer> adaptive_timer_;
};

} // namespace robot_core
