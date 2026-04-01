#pragma once

#include <array>
#include <atomic>
#include <chrono>
#include <functional>
#include <memory>
#include <mutex>
#include <thread>
#include <iostream>
#include <cmath>

#include "robot_core/force_control_config.h"

namespace robot_core {

// Cartesian impedance parameters
struct CartesianImpedanceParams {
    std::array<double, 6> stiffness = {2000.0, 2000.0, 50.0, 200.0, 200.0, 200.0};
    std::array<double, 6> damping = {100.0, 100.0, 20.0, 50.0, 50.0, 50.0};
    std::array<double, 6> desired_wrench = {0.0, 0.0, -10.0, 0.0, 0.0, 0.0};
};

// Force circuit breaker for real-time safety
class ForceCircuitBreaker {
private:
    ForceControlLimits limits_;
    std::atomic<bool> emergency_triggered_{false};
    std::atomic<int64_t> last_force_check_ns_{0};
    mutable std::mutex safety_mutex_;

public:
    explicit ForceCircuitBreaker(const ForceControlLimits& limits = loadForceControlLimits())
        : limits_(limits) {}

    // Real-time force checking (called every 1ms in control loop)
    bool checkForces(const std::array<double, 6>& cartesian_forces,
                    const std::array<double, 6>& cartesian_torques) {

        auto now = std::chrono::steady_clock::now();
        int64_t now_ns = std::chrono::duration_cast<std::chrono::nanoseconds>(
            now.time_since_epoch()).count();

        // Rate limit checks to avoid excessive processing
        if (now_ns - last_force_check_ns_.load() < 500000) { // 0.5ms minimum interval
            return !emergency_triggered_.load();
        }
        last_force_check_ns_.store(now_ns);

        // Check Z-axis force (primary safety concern)
        double z_force = cartesian_forces[2];
        if (std::abs(z_force) > limits_.max_z_force_n) {
            std::lock_guard<std::mutex> lock(safety_mutex_);
            emergency_triggered_.store(true);
            std::cerr << "[EMERGENCY] Z-axis force exceeded limit: "
                      << z_force << "N > " << limits_.max_z_force_n << "N" << std::endl;
            return false;
        }

        // Check lateral forces
        double xy_force_magnitude = std::sqrt(cartesian_forces[0] * cartesian_forces[0] +
                                             cartesian_forces[1] * cartesian_forces[1]);
        if (xy_force_magnitude > limits_.max_xy_force_n) {
            std::lock_guard<std::mutex> lock(safety_mutex_);
            emergency_triggered_.store(true);
            std::cerr << "[EMERGENCY] XY lateral force exceeded limit: "
                      << xy_force_magnitude << "N > " << limits_.max_xy_force_n << "N" << std::endl;
            return false;
        }

        return !emergency_triggered_.load();
    }

    // Reset emergency state (only after manual inspection)
    void resetEmergency() {
        std::lock_guard<std::mutex> lock(safety_mutex_);
        emergency_triggered_.store(false);
        std::cout << "[SAFETY] Emergency state reset - manual inspection required" << std::endl;
    }

    bool isEmergencyTriggered() const {
        return emergency_triggered_.load();
    }

    const ForceControlLimits& getLimits() const { return limits_; }
    void setLimits(const ForceControlLimits& limits) {
        std::lock_guard<std::mutex> lock(safety_mutex_);
        limits_ = limits;
    }
};

// Impedance control manager
class ImpedanceControlManager {
private:
    CartesianImpedanceParams params_;
    ForceCircuitBreaker circuit_breaker_;
    std::atomic<bool> impedance_active_{false};
    mutable std::mutex control_mutex_;

public:
    explicit ImpedanceControlManager(const CartesianImpedanceParams& params = CartesianImpedanceParams(),
                                   const ForceControlLimits& limits = loadForceControlLimits())
        : params_(params), circuit_breaker_(limits) {}

    // Configure impedance parameters
    bool configureImpedance(const CartesianImpedanceParams& params) {
        // Validate parameters
        for (size_t i = 0; i < 6; ++i) {
            if (params.stiffness[i] < 0.0 || params.damping[i] < 0.0) {
                std::cerr << "[ERROR] Invalid impedance parameters: negative stiffness/damping" << std::endl;
                return false;
            }
        }

        std::lock_guard<std::mutex> lock(control_mutex_);
        params_ = params;

        std::cout << "[IMPEDANCE] Configured stiffness: ["
                  << params_.stiffness[0] << ", " << params_.stiffness[1] << ", " << params_.stiffness[2] << ", "
                  << params_.stiffness[3] << ", " << params_.stiffness[4] << ", " << params_.stiffness[5] << "]"
                  << std::endl;

        return true;
    }

    // Set desired contact force (Z-axis)
    void setDesiredContactForce(double force_n) {
        std::lock_guard<std::mutex> lock(control_mutex_);
        params_.desired_wrench = {0.0, 0.0, -std::abs(force_n), 0.0, 0.0, 0.0};
        std::cout << "[IMPEDANCE] Set desired contact force: " << force_n << "N" << std::endl;
    }

    // Set full desired wrench for RT control code paths.
    void setDesiredWrench(const std::array<double, 6>& wrench) {
        std::lock_guard<std::mutex> lock(control_mutex_);
        params_.desired_wrench = wrench;
        std::cout << "[IMPEDANCE] Set desired wrench: ["
                  << wrench[0] << ", " << wrench[1] << ", " << wrench[2] << ", "
                  << wrench[3] << ", " << wrench[4] << ", " << wrench[5] << "]"
                  << std::endl;
    }

    // Real-time safety check and control
    bool updateControl(const std::array<double, 6>& current_forces,
                      const std::array<double, 6>& current_torques) {

        // Always check safety first
        if (!circuit_breaker_.checkForces(current_forces, current_torques)) {
            impedance_active_.store(false);
            return false;
        }

        return impedance_active_.load();
    }

    void activateImpedance() {
        std::lock_guard<std::mutex> lock(control_mutex_);
        impedance_active_.store(true);
        std::cout << "[IMPEDANCE] Impedance control activated" << std::endl;
    }

    void deactivateImpedance() {
        std::lock_guard<std::mutex> lock(control_mutex_);
        impedance_active_.store(false);
        std::cout << "[IMPEDANCE] Impedance control deactivated" << std::endl;
    }

    const CartesianImpedanceParams& getParams() const { return params_; }
    const ForceCircuitBreaker& getCircuitBreaker() const { return circuit_breaker_; }
    ForceCircuitBreaker& getCircuitBreaker() { return circuit_breaker_; }
    const ForceCircuitBreaker& getForceCircuitBreaker() const { return circuit_breaker_; }
    ForceCircuitBreaker& getForceCircuitBreaker() { return circuit_breaker_; }
};

} // namespace robot_core
