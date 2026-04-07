/**
 * @file impedance_scan_example.cpp
 * @brief Canonical controller-composition demo for legacy impedance-scan users.
 *
 * This example no longer implements an alternative contact-control law. It
 * demonstrates how the production primitives are composed:
 *   - NormalForceEstimator
 *   - NormalAxisAdmittanceController
 *   - TangentialScanController
 *   - OrientationTrimController
 *
 * The production RT execution path still lives in SdkRobotFacade.
 */

#include "impedance_scan_controller.hpp"

#include <iomanip>
#include <iostream>

#include "robot_core/contact_control_contract.h"

int main() {
  std::cout << "=== Canonical Admittance Controller Composition Demo ===\n";

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
    std::cerr << "Contract validation failed.\n";
    return 1;
  }

  legacy_example::ImpedanceScanController wrapper;
  if (!wrapper.configure(contract)) {
    std::cerr << "Failed to configure legacy wrapper.\n";
    return 1;
  }

  const double target_force_n = 8.0;
  std::cout << "target_force_n=" << target_force_n << "\n";
  std::cout << std::fixed << std::setprecision(4);

  for (int i = 0; i < 8; ++i) {
    legacy_example::DemoObservation obs{};
    obs.pressure_force_n = 6.8 + 0.18 * static_cast<double>(i);
    obs.pressure_valid = true;
    obs.pressure_age_ms = 2.0;
    obs.wrench_force_n = 7.0 + 0.12 * static_cast<double>(i);
    obs.wrench_valid = true;
    obs.wrench_age_ms = 2.0;
    obs.requested_tangent_speed_mm_s = 6.0;
    obs.dt_s = 0.001;

    const auto snapshot = wrapper.step(target_force_n, obs);
    std::cout << "cycle=" << i
              << " source=" << snapshot.force.source
              << " est_force=" << snapshot.force.estimated_force_n
              << "N force_err=" << snapshot.admittance.state.force_error_n
              << " delta_normal_mm=" << (snapshot.admittance.delta_normal_m * 1000.0)
              << " tangent_progress_mm=" << (snapshot.tangential.progress_m * 1000.0)
              << " trim_deg=" << (snapshot.trim.trim_rad * 180.0 / 3.14159265358979323846)
              << '\n';
  }

  std::cout << "=== Demo complete ===\n";
  return 0;
}
