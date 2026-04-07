#include "impedance_scan_controller.hpp"
#include "robot_core/contact_control_contract.h"
#include "robot_core/force_control_config.h"
#include <cmath>
#include <iostream>

int main() {
    std::cout << "Testing Impedance Scan Controller..." << std::endl;
    const auto limits = robot_core::loadForceControlLimits();

    robot_core::ContactControlContract contract{};
    contract.mode = "normal_axis_admittance";
    contract.seek_contact_admittance.virtual_mass = 0.8;
    contract.seek_contact_admittance.virtual_damping = 120.0;
    contract.seek_contact_admittance.virtual_stiffness = 40.0;
    contract.seek_contact_admittance.max_step_mm = 0.08;
    contract.seek_contact_admittance.max_velocity_mm_s = 2.0;
    contract.seek_contact_admittance.max_acceleration_mm_s2 = 30.0;
    contract.seek_contact_admittance.max_displacement_mm = 8.0;
    contract.seek_contact_admittance.force_deadband_n = 0.3;
    contract.seek_contact_admittance.integrator_limit_n = 10.0;
    contract.seek_contact_admittance.integrator_leak = 0.02;
    contract.tangential_scan.tangent_speed_min_mm_s = 2.0;
    contract.tangential_scan.tangent_speed_max_mm_s = 10.0;
    contract.tangential_scan.max_travel_mm = 120.0;
    contract.tangential_scan.enable_lateral_modulation = true;
    contract.tangential_scan.lateral_amplitude_mm = 0.5;
    contract.tangential_scan.modulation_frequency_hz = 0.25;
    contract.orientation_trim.gain = 0.08;
    contract.orientation_trim.max_trim_deg = 1.5;
    contract.orientation_trim.lowpass_hz = 8.0;
    contract.force_estimator.preferred_source = "fused";
    contract.force_estimator.pressure_weight = 0.7;
    contract.force_estimator.wrench_weight = 0.3;
    contract.force_estimator.stale_timeout_ms = 100.0;
    contract.force_estimator.timeout_ms = 250.0;
    contract.force_estimator.auto_bias_zero = true;
    contract.force_estimator.min_confidence = 0.4;

    if (!robot_core::validateContactControlContract(contract)) {
        std::cerr << "Canonical contact-control contract should validate" << std::endl;
        return 1;
    }

    legacy_example::ImpedanceScanController controller;
    if (!controller.configure(contract)) {
        std::cerr << "Failed to configure legacy impedance wrapper" << std::endl;
        return 1;
    }

    legacy_example::DemoObservation observation{};
    observation.pressure_force_n = limits.desired_contact_force_n - 1.0;
    observation.pressure_valid = true;
    observation.pressure_age_ms = 2.0;
    observation.wrench_force_n = limits.desired_contact_force_n - 0.5;
    observation.wrench_valid = true;
    observation.wrench_age_ms = 2.0;
    observation.requested_tangent_speed_mm_s = 6.0;
    observation.dt_s = 0.001;

    const auto snapshot = controller.step(limits.desired_contact_force_n, observation);
    if (!(snapshot.force.confidence > 0.0)) {
        std::cerr << "Force estimator confidence should be positive for fresh fused measurements" << std::endl;
        return 1;
    }
    if (!(std::abs(snapshot.admittance.state.force_error_n) > 0.0)) {
        std::cerr << "Admittance controller should observe a non-zero force error for the test observation" << std::endl;
        return 1;
    }
    if (!(snapshot.tangential.progress_m > 0.0)) {
        std::cerr << "Tangential scan controller should advance progress for a positive commanded speed" << std::endl;
        return 1;
    }

    std::cout << "✓ ImpedanceScanController configured successfully" << std::endl;
    std::cout << "✓ Safety limits: desired_contact_force_n = " << limits.desired_contact_force_n << " N" << std::endl;
    std::cout << "✓ Controller ready for medical ultrasound scanning" << std::endl;
    return 0;
}
