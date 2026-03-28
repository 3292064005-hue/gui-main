#include "robot_core/rt_motion_service.h"
#include "impedance_control_manager.hpp"
#include <iostream>
#include <array>
#include <cstring>
#include <functional>
#include <thread>
#include <fstream>
#include <sstream>

// Assuming ROKAE SDK headers are available when compiling against third_party.
// #include "rokae/robot.h"
// #include "rokae/data_types.h"
namespace rokae {
    // Stubs for the IDE parser syntax sake since third_party is externally linked
    struct CartesianPosition { std::array<double, 16> pos; };
    enum CoordinateType { endInRef };
    enum FrameType { path };
    enum RtControllerMode { cartesianImpedance };
    enum RtSupportedFields { tcpPose_m, tau_m };
}

namespace robot_core {

// AdaptiveTimer implementation
AdaptiveTimer::AdaptiveTimer(double min_period_ms, double max_period_ms, double target_cpu)
    : min_period_ms_(min_period_ms), max_period_ms_(max_period_ms), target_cpu_(target_cpu),
      current_period_ms_(1.0) {}  // Start with 1ms

void AdaptiveTimer::start() {
    last_time_ = std::chrono::steady_clock::now();
}

void AdaptiveTimer::wait() {
    auto now = std::chrono::steady_clock::now();
    auto elapsed = std::chrono::duration_cast<std::chrono::microseconds>(now - last_time_).count();
    double elapsed_ms = elapsed / 1000.0;
    
    if (elapsed_ms < current_period_ms_) {
        std::this_thread::sleep_for(std::chrono::microseconds(static_cast<long>((current_period_ms_ - elapsed_ms) * 1000)));
    }
    
    last_time_ = std::chrono::steady_clock::now();
}

void AdaptiveTimer::adjustPeriod(double cpu_usage) {
    if (cpu_usage > target_cpu_ + 10.0) {
        // CPU too high, increase period (lower frequency)
        current_period_ms_ = std::min(current_period_ms_ * 1.1, max_period_ms_);
    } else if (cpu_usage < target_cpu_ - 10.0) {
        // CPU low, decrease period (higher frequency)
        current_period_ms_ = std::max(current_period_ms_ * 0.9, min_period_ms_);
    }
}

double AdaptiveTimer::getCpuUsage() {
    // Simple CPU usage estimation (Linux /proc/stat)
    std::ifstream file("/proc/stat");
    std::string line;
    if (std::getline(file, line)) {
        std::istringstream iss(line);
        std::string cpu;
        long user, nice, system, idle, iowait, irq, softirq;
        iss >> cpu >> user >> nice >> system >> idle >> iowait >> irq >> softirq;
        long total = user + nice + system + idle + iowait + irq + softirq;
        static long prev_total = 0;
        static long prev_idle = 0;
        long total_diff = total - prev_total;
        long idle_diff = idle - prev_idle;
        prev_total = total;
        prev_idle = idle;
        if (total_diff > 0) {
            return 100.0 * (1.0 - static_cast<double>(idle_diff) / total_diff);
        }
    }
    return 0.0;
}

// Helper to get monotonic system time in nanoseconds
inline int64_t get_current_time_ns() {
    auto now = std::chrono::steady_clock::now();
    return std::chrono::duration_cast<std::chrono::nanoseconds>(now.time_since_epoch()).count();
}

RtMotionService::RtMotionService(std::shared_ptr<rokae::xMateErProRobot> robot)
    : robot_(robot), cmd_queue(100), telemetry_queue(100),
      adaptive_timer_(std::make_unique<AdaptiveTimer>()),
      impedance_manager_(std::make_unique<ImpedanceControlManager>()) {
    // Initialize current_target_ to a safe default.
    std::memset(current_target_.tcp_pose_td, 0, sizeof(current_target_.tcp_pose_td));
    current_target_.tcp_pose_td[0] = 1.0;
    current_target_.tcp_pose_td[5] = 1.0;
    current_target_.tcp_pose_td[10] = 1.0;
    current_target_.tcp_pose_td[15] = 1.0;
    current_target_.timestamp_ns = get_current_time_ns();
}

RtMotionService::~RtMotionService() {
    stop();
}

bool RtMotionService::startCartesianImpedance() {
    /* 
     * In a fully linked environment:
     * std::error_code ec;
     * auto rtCon = robot_->getRtMotionController().lock();
     * if(!rtCon) return false;
     *
     * // 1. Extremely stiff in XYZ orientations, but completely soft (-20) in Z for contact
     * rtCon->setCartesianImpedance({1500, 1500, 20, 100, 100, 100}, ec);
     *
     * // 2. Apply exactly 10N constant pressure into the Z direction
     * rtCon->setCartesianImpedanceDesiredTorque({0, 0, -10, 0, 0, 0}, ec);
     *
     * // 3. Ensure the Z orientation tracked is always the normal of the moving path
     * std::array<double, 16> path_transform = {1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1};
     * rtCon->setFcCoor(path_transform, rokae::FrameType::path, ec);
     *
     * // Configure desired outputs that we broadcast back to Python
     * rtCon->startReceiveRobotState(std::chrono::milliseconds(1), 
     *     {rokae::RtSupportedFields::tcpPose_m, rokae::RtSupportedFields::tau_m});
     *
     * rtCon->startMove(rokae::RtControllerMode::cartesianImpedance);
     */
    
    is_running_ = true;
    adaptive_timer_->start();

    // Initialize impedance control manager with medical safety parameters
    CartesianImpedanceParams params;
    params.stiffness = {
        1500.0,  // X stiffness (N/m) - very stiff for lateral control
        1500.0,  // Y stiffness (N/m) - very stiff for lateral control
        20.0,    // Z stiffness (N/m) - compliant for contact
        100.0,   // RX stiffness
        100.0,   // RY stiffness
        100.0    // RZ stiffness
    };
    params.damping = {50.0, 50.0, 10.0, 20.0, 20.0, 20.0};
    if (!impedance_manager_->configureImpedance(params)) {
        is_running_ = false;
        return false;
    }

    const auto& force_limits = impedance_manager_->getCircuitBreaker().getLimits();
    impedance_manager_->setDesiredWrench({0.0, 0.0, -std::abs(force_limits.desired_contact_force_n), 0.0, 0.0, 0.0});
    impedance_manager_->activateImpedance();

    /*
     * std::function<rokae::CartesianPosition()> callback = [&]() -> rokae::CartesianPosition {
     *     
     *     // (1) Lock-free Data Fetch from ZMQ IPC Thread
     *     spine_core::CommandPose target;
     *     while (cmd_queue.try_dequeue(target)) {
     *         current_target_ = target;
     *     }
     *
     *     int64_t now_ns = get_current_time_ns();
     *     
     *     // (2) Dead Man's Switch (50ms network timeout limit)
     *     if ((now_ns - current_target_.timestamp_ns) > 50'000'000) {
     *          // The Python planning pipeline or UI died. The network dropped.
     *          // Immediately lift off 10N force and trigger a safe Retreat inside C++.
     *          rtCon->setCartesianImpedanceDesiredTorque({0, 0, 0, 0, 0, 0}, ec);
     *          this->controlledRetract();
     *          // This branch would eventually return a halted position or call stopLoop().
     *     }
     *
     *     // (3) Force Circuit Breaker Safety Check
     *     std::array<double, 6> measured_forces = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0}; // Would read from rtCon
     *     if (impedance_manager_->getForceCircuitBreaker().checkForces(measured_forces)) {
     *         // Force exceeded safety limits - emergency stop
     *         this->controlledRetract();
     *         // This branch would eventually return a halted position or call stopLoop().
     *     }
     *
     *     // (4) Adaptive frequency adjustment based on CPU load
     *     double cpu_usage = adaptive_timer_->getCpuUsage();
     *     adaptive_timer_->adjustPeriod(cpu_usage);
     *     std::cout << "Current period: " << adaptive_timer_->getCurrentPeriodMs() << "ms, CPU: " << cpu_usage << "%" << std::endl;
     *
     *     // (5) Lock-free Data Push to Python Telemetry Thread
     *     spine_core::RobotTelemetry tel = {};
     *     tel.timestamp_ns = now_ns;
     *     rtCon->getStateData(rokae::RtSupportedFields::tcpPose_m, tel.tcp_pose_measured);
     *     // Omitted getting joint angles / Z-torque for brevity.
     *     tel.actual_force_z = measured_forces[2]; // Z-force from circuit breaker
     *     tel.safety_status = is_running_.load() ? 0 : 1;
     *     telemetry_queue.try_enqueue(tel);
     *
     *     // (6) Wait for adaptive period
     *     adaptive_timer_->wait();
     *
     *     // (7) Actuate pure tracking trajectory, relying on hardware controller for Z-Force
     *     rokae::CartesianPosition out;
     *     std::memcpy(out.pos.data(), current_target_.tcp_pose_td, sizeof(double)*16);
     *     return out;
     * };
     *
     * rtCon->setControlLoop(callback, 99, false); // Real-time Priority = 99
     * rtCon->startLoop(false); // Non-blocking
     */
    return true;
}

void RtMotionService::controlledRetract() {
    is_running_ = false;
    
    // Emergency stop - remove all forces and lift safely
    impedance_manager_->setDesiredWrench({0.0, 0.0, 0.0, 0.0, 0.0, 0.0});
    impedance_manager_->deactivateImpedance();
    
    // Command the robot upward by +10cm relative to the path Z axis securely.
    /*
     * std::error_code ec;
     * auto rtCon = robot_->getRtMotionController().lock();
     * rtCon->stopLoop();
     * 
     * // MoveL +Z 100mm logic goes here to pull ultrasound probe safely off patient.
     * rtCon->MoveL(...);
     */
}

SensorHealthDecision RtMotionService::evaluateSensorFreshnessMs(double age_ms) const {
    const auto& limits = impedance_manager_->getCircuitBreaker().getLimits();
    if (age_ms > limits.sensor_timeout_ms * 2.0) {
        return SensorHealthDecision::Estop;
    }
    if (age_ms > limits.sensor_timeout_ms) {
        return SensorHealthDecision::ControlledRetract;
    }
    if (age_ms > limits.stale_telemetry_ms) {
        return SensorHealthDecision::Hold;
    }
    return SensorHealthDecision::None;
}

void RtMotionService::stop() {
    is_running_ = false;
    impedance_manager_->deactivateImpedance();
    /*
     * auto rtCon = robot_->getRtMotionController().lock();
     * if(rtCon) {
     *     rtCon->stopLoop();
     *     rtCon->stopMove();
     * }
     */
}

bool RtMotionService::seekContact() { 
    if (!impedance_manager_) {
        return false;
    }
    impedance_manager_->setDesiredContactForce(impedance_manager_->getCircuitBreaker().getLimits().desired_contact_force_n);
    impedance_manager_->activateImpedance();
    return true; 
}

void RtMotionService::pauseAndHold() {
    if (!impedance_manager_) {
        return;
    }
    // Hold posture while releasing contact force demand.
    impedance_manager_->setDesiredContactForce(0.0);
    impedance_manager_->activateImpedance();
}

} // namespace robot_core
