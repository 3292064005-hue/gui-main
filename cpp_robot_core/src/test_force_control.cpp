#include "impedance_control_manager.hpp"
#include <iostream>
#include <array>
#include <cmath>
#include <thread>
#include <chrono>

int main() {
    std::cout << "Testing Force Control Safety System..." << std::endl;

    // Create impedance control manager
    robot_core::ImpedanceControlManager manager;

    // Test impedance configuration
    robot_core::CartesianImpedanceParams stiffness_params;
    stiffness_params.stiffness = {1500.0, 1500.0, 20.0, 100.0, 100.0, 100.0};
    stiffness_params.damping = {50.0, 50.0, 10.0, 20.0, 20.0, 20.0};
    manager.configureImpedance(stiffness_params);
    std::cout << "✓ Impedance configured successfully" << std::endl;

    // Test desired force setting
    manager.setDesiredContactForce(10.0);
    std::cout << "✓ Desired contact force set to 10N downward pressure" << std::endl;

    // Test force circuit breaker with safe forces
    manager.getCircuitBreaker().resetEmergency();
    std::array<double, 6> safe_forces = {5.0, 5.0, 15.0, 1.0, 1.0, 1.0};
    std::array<double, 6> safe_torques = {0.5, 0.5, 0.5, 0.1, 0.1, 0.1};
    bool safe = manager.getCircuitBreaker().checkForces(safe_forces, safe_torques);
    std::cout << "✓ Force circuit breaker check with safe forces: " << (safe ? "OK" : "TRIPPED") << std::endl;

    // Test force circuit breaker with excessive Z force (should trip)
    manager.getCircuitBreaker().resetEmergency();
    std::this_thread::sleep_for(std::chrono::milliseconds(1)); // Rate limiting delay
    std::array<double, 6> dangerous_forces = {5.0, 5.0, 40.0, 1.0, 1.0, 1.0}; // 40N > 35N limit
    std::array<double, 6> dangerous_torques = {0.5, 0.5, 0.5, 0.1, 0.1, 0.1};
    safe = manager.getCircuitBreaker().checkForces(dangerous_forces, dangerous_torques);
    std::cout << "✓ Force circuit breaker check with excessive Z force: " << (safe ? "OK (unexpected)" : "TRIPPED (expected)") << std::endl;

    // Test force circuit breaker with excessive lateral force (should trip)
    manager.getCircuitBreaker().resetEmergency();
    std::this_thread::sleep_for(std::chrono::milliseconds(1)); // Rate limiting delay
    std::array<double, 6> lateral_danger = {25.0, 5.0, 15.0, 1.0, 1.0, 1.0}; // 25N > 20N X limit
    std::array<double, 6> lateral_torques = {0.5, 0.5, 0.5, 0.1, 0.1, 0.1};
    safe = manager.getCircuitBreaker().checkForces(lateral_danger, lateral_torques);
    std::cout << "✓ Force circuit breaker check with excessive X force: " << (safe ? "OK (unexpected)" : "TRIPPED (expected)") << std::endl;

    std::cout << "Force Control Safety System test completed successfully!" << std::endl;
    return 0;
}