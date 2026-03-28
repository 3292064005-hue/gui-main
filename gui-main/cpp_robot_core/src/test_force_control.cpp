#include "impedance_control_manager.hpp"
#include "robot_core/force_control_config.h"
#include <iostream>
#include <array>
#include <cmath>
#include <thread>
#include <chrono>
#include "robot_core/rt_motion_service.h"

int main() {
    std::cout << "Testing Force Control Safety System..." << std::endl;
    const auto limits = robot_core::loadForceControlLimits();

    // Create impedance control manager
    robot_core::ImpedanceControlManager manager;
    if (std::abs(manager.getCircuitBreaker().getLimits().max_z_force_n - limits.max_z_force_n) > 1e-9) {
        std::cerr << "Runtime force limits did not load from configs/force_control.json" << std::endl;
        return 1;
    }
    if (std::abs(manager.getCircuitBreaker().getLimits().sensor_timeout_ms - limits.sensor_timeout_ms) > 1e-9) {
        std::cerr << "Sensor timeout did not load from configs/force_control.json" << std::endl;
        return 1;
    }
    std::cout << "✓ Force limits loaded from configs/force_control.json" << std::endl;

    // Test impedance configuration
    robot_core::CartesianImpedanceParams stiffness_params;
    stiffness_params.stiffness = {1500.0, 1500.0, 20.0, 100.0, 100.0, 100.0};
    stiffness_params.damping = {50.0, 50.0, 10.0, 20.0, 20.0, 20.0};
    if (!manager.configureImpedance(stiffness_params)) {
        std::cerr << "Failed to configure impedance parameters" << std::endl;
        return 1;
    }
    std::cout << "✓ Impedance configured successfully" << std::endl;

    // Test desired force setting
    manager.setDesiredContactForce(limits.desired_contact_force_n);
    if (std::abs(manager.getParams().desired_wrench[2] + limits.desired_contact_force_n) > 1e-9) {
        std::cerr << "Desired contact force was not mapped onto desired wrench" << std::endl;
        return 1;
    }
    std::cout << "✓ Desired contact force set to configured downward pressure" << std::endl;

    const std::array<double, 6> explicit_wrench = {1.0, -2.0, -8.0, 0.1, 0.2, 0.3};
    manager.setDesiredWrench(explicit_wrench);
    if (manager.getParams().desired_wrench != explicit_wrench) {
        std::cerr << "Explicit desired wrench was not preserved" << std::endl;
        return 1;
    }
    std::cout << "✓ Desired wrench API writes to the shared impedance state" << std::endl;

    // Test force circuit breaker with safe forces
    manager.getCircuitBreaker().resetEmergency();
    std::array<double, 6> safe_forces = {5.0, 5.0, 15.0, 1.0, 1.0, 1.0};
    std::array<double, 6> safe_torques = {0.5, 0.5, 0.5, 0.1, 0.1, 0.1};
    bool safe = manager.getCircuitBreaker().checkForces(safe_forces, safe_torques);
    if (!safe) {
        std::cerr << "Safe forces unexpectedly tripped the circuit breaker" << std::endl;
        return 1;
    }
    std::cout << "✓ Force circuit breaker check with safe forces: " << (safe ? "OK" : "TRIPPED") << std::endl;

    // Test force circuit breaker with excessive Z force (should trip)
    manager.getCircuitBreaker().resetEmergency();
    std::this_thread::sleep_for(std::chrono::milliseconds(1)); // Rate limiting delay
    std::array<double, 6> dangerous_forces = {5.0, 5.0, limits.max_z_force_n + 5.0, 1.0, 1.0, 1.0};
    std::array<double, 6> dangerous_torques = {0.5, 0.5, 0.5, 0.1, 0.1, 0.1};
    safe = manager.getCircuitBreaker().checkForces(dangerous_forces, dangerous_torques);
    if (safe || !manager.getCircuitBreaker().isEmergencyTriggered()) {
        std::cerr << "Excessive Z force should trip the circuit breaker" << std::endl;
        return 1;
    }
    std::cout << "✓ Force circuit breaker check with excessive Z force: " << (safe ? "OK (unexpected)" : "TRIPPED (expected)") << std::endl;

    // Test force circuit breaker with excessive lateral force (should trip)
    manager.getCircuitBreaker().resetEmergency();
    std::this_thread::sleep_for(std::chrono::milliseconds(1)); // Rate limiting delay
    std::array<double, 6> lateral_danger = {limits.max_xy_force_n + 5.0, 5.0, 15.0, 1.0, 1.0, 1.0};
    std::array<double, 6> lateral_torques = {0.5, 0.5, 0.5, 0.1, 0.1, 0.1};
    safe = manager.getCircuitBreaker().checkForces(lateral_danger, lateral_torques);
    if (safe || !manager.getCircuitBreaker().isEmergencyTriggered()) {
        std::cerr << "Excessive XY force should trip the circuit breaker" << std::endl;
        return 1;
    }
    std::cout << "✓ Force circuit breaker check with excessive X force: " << (safe ? "OK (unexpected)" : "TRIPPED (expected)") << std::endl;

    robot_core::RtMotionService motion_service;
    if (motion_service.evaluateSensorFreshnessMs(limits.stale_telemetry_ms + 10.0) != robot_core::SensorHealthDecision::Hold) {
        std::cerr << "Stale telemetry should request PAUSED_HOLD semantics" << std::endl;
        return 1;
    }
    if (motion_service.evaluateSensorFreshnessMs(limits.sensor_timeout_ms + 10.0) != robot_core::SensorHealthDecision::ControlledRetract) {
        std::cerr << "Sensor timeout should request controlled retract" << std::endl;
        return 1;
    }
    if (motion_service.evaluateSensorFreshnessMs(limits.sensor_timeout_ms * 2.0 + 10.0) != robot_core::SensorHealthDecision::Estop) {
        std::cerr << "Severe sensor timeout should request ESTOP" << std::endl;
        return 1;
    }
    std::cout << "✓ Sensor freshness decisions map to hold/retract/estop" << std::endl;

    std::cout << "Force Control Safety System test completed successfully!" << std::endl;
    return 0;
}
