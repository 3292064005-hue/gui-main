#include "robot_core/contact_control_contract.h"
#include "robot_core/sdk_robot_facade.h"

#include <algorithm>

namespace robot_core {

namespace {

AdmittanceControllerConfig buildSeekAdmittance(double gain, double damping_gain, double max_step, double max_travel, double integrator_limit) {
  AdmittanceControllerConfig cfg{};
  cfg.virtual_mass = gain > 0.0 ? std::max(0.05, 1.0 / (gain * 10000.0)) : 0.8;
  cfg.virtual_damping = damping_gain > 0.0 ? std::max(5.0, 1.0 / (damping_gain * 10000.0)) : 120.0;
  cfg.virtual_stiffness = 40.0;
  cfg.max_step_mm = max_step;
  cfg.max_velocity_mm_s = 2.0;
  cfg.max_acceleration_mm_s2 = 30.0;
  cfg.max_displacement_mm = max_travel;
  cfg.force_deadband_n = 0.3;
  cfg.integrator_limit_n = integrator_limit;
  cfg.integrator_leak = 0.02;
  return cfg;
}

}  // namespace

ContactControlContract buildContactControlContract(const RuntimeConfig& config) {
  ContactControlContract contract{};
  contract.mode = config.contact_control.mode.empty() ? std::string("normal_axis_admittance") : config.contact_control.mode;
  contract.seek_contact_admittance = buildSeekAdmittance(config.normal_admittance_gain, config.normal_damping_gain, config.seek_contact_max_step_mm, config.seek_contact_max_travel_mm, config.rt_integrator_limit_n);
  contract.seek_contact_admittance.virtual_mass = std::max(0.01, config.contact_control.virtual_mass);
  contract.seek_contact_admittance.virtual_damping = std::max(0.0, config.contact_control.virtual_damping);
  contract.seek_contact_admittance.virtual_stiffness = std::max(0.0, config.contact_control.virtual_stiffness);
  contract.seek_contact_admittance.force_deadband_n = std::max(0.0, config.contact_control.force_deadband_n);
  contract.seek_contact_admittance.max_step_mm = std::max(0.01, config.contact_control.max_normal_step_mm);
  contract.seek_contact_admittance.max_velocity_mm_s = std::max(0.1, config.contact_control.max_normal_velocity_mm_s);
  contract.seek_contact_admittance.max_acceleration_mm_s2 = std::max(1.0, config.contact_control.max_normal_acc_mm_s2);
  contract.seek_contact_admittance.max_displacement_mm = std::max(contract.seek_contact_admittance.max_step_mm, config.contact_control.max_normal_travel_mm);
  contract.seek_contact_admittance.integrator_limit_n = std::max(0.1, config.contact_control.anti_windup_limit_n);
  contract.seek_contact_admittance.integrator_leak = std::clamp(config.contact_control.integrator_leak, 0.0, 1.0);

  contract.scan_follow_admittance = contract.seek_contact_admittance;
  contract.scan_follow_admittance.max_displacement_mm = std::max(contract.seek_contact_admittance.max_step_mm, config.contact_control.max_normal_travel_mm);
  contract.scan_follow_admittance.max_velocity_mm_s = std::max(0.1, config.contact_control.max_normal_velocity_mm_s);
  contract.scan_follow_admittance.max_acceleration_mm_s2 = std::max(1.0, config.contact_control.max_normal_acc_mm_s2);
  contract.scan_follow_admittance.virtual_stiffness = std::max(contract.seek_contact_admittance.virtual_stiffness, std::max(5.0, config.scan_normal_pi_kp * 1000.0));
  contract.scan_follow_admittance.integrator_limit_n = std::max(contract.seek_contact_admittance.integrator_limit_n, config.rt_integrator_limit_n);
  contract.scan_follow_admittance.integrator_leak = std::clamp(config.contact_control.integrator_leak, 0.0, 1.0);

  contract.pause_hold_admittance = contract.seek_contact_admittance;
  contract.pause_hold_admittance.max_displacement_mm = std::max(config.pause_hold_position_guard_mm, 0.1);
  contract.pause_hold_admittance.virtual_stiffness = std::max(contract.seek_contact_admittance.virtual_stiffness, std::max(10.0, config.pause_hold_drift_kp * 1000.0));
  contract.pause_hold_admittance.integrator_leak = std::clamp(config.contact_control.integrator_leak, 0.0, 1.0);

  contract.tangential_scan.tangent_speed_min_mm_s = config.scan_tangent_speed_min_mm_s;
  contract.tangential_scan.tangent_speed_max_mm_s = config.scan_tangent_speed_max_mm_s;
  contract.tangential_scan.max_travel_mm = std::max(config.segment_length_mm, contract.seek_contact_admittance.max_displacement_mm);
  contract.tangential_scan.enable_lateral_modulation = config.scan_follow_enable_lateral_modulation;
  contract.tangential_scan.lateral_amplitude_mm = config.scan_follow_lateral_amplitude_mm;
  contract.tangential_scan.modulation_frequency_hz = config.scan_follow_frequency_hz;

  contract.orientation_trim.gain = std::max(0.0, config.orientation_trim.gain);
  contract.orientation_trim.max_trim_deg = std::max(0.1, config.orientation_trim.max_trim_deg);
  contract.orientation_trim.lowpass_hz = std::max(0.1, config.orientation_trim.lowpass_hz);

  contract.force_estimator.preferred_source = config.force_estimator.preferred_source.empty() ? std::string("fused") : config.force_estimator.preferred_source;
  contract.force_estimator.pressure_weight = std::max(0.0, config.force_estimator.pressure_weight);
  contract.force_estimator.wrench_weight = std::max(0.0, config.force_estimator.wrench_weight);
  contract.force_estimator.stale_timeout_ms = std::max(1.0, static_cast<double>(config.force_estimator.stale_timeout_ms));
  contract.force_estimator.timeout_ms = std::max(contract.force_estimator.stale_timeout_ms, static_cast<double>(config.force_estimator.timeout_ms));
  contract.force_estimator.auto_bias_zero = config.force_estimator.auto_bias_zero;
  contract.force_estimator.min_confidence = std::clamp(config.force_estimator.min_confidence, 0.0, 1.0);
  return contract;
}

ContactControlContract buildContactControlContract(const SdkRobotRuntimeConfig& config) {
  RuntimeConfig shadow{};
  shadow.seek_contact_max_travel_mm = config.seek_contact_max_travel_mm;
  shadow.segment_length_mm = config.scan_follow_max_travel_mm;
  shadow.normal_admittance_gain = config.normal_admittance_gain;
  shadow.normal_damping_gain = config.normal_damping_gain;
  shadow.seek_contact_max_step_mm = config.seek_contact_max_step_mm;
  shadow.rt_integrator_limit_n = config.rt_integrator_limit_n;
  shadow.scan_tangent_speed_min_mm_s = config.scan_tangent_speed_min_mm_s;
  shadow.scan_tangent_speed_max_mm_s = config.scan_tangent_speed_max_mm_s;
  shadow.scan_normal_pi_kp = config.scan_normal_pi_kp;
  shadow.scan_follow_enable_lateral_modulation = config.scan_follow_enable_lateral_modulation;
  shadow.scan_follow_lateral_amplitude_mm = config.scan_follow_lateral_amplitude_mm;
  shadow.scan_follow_frequency_hz = config.scan_follow_frequency_hz;
  shadow.scan_pose_trim_gain = config.scan_pose_trim_gain;
  shadow.rt_max_pose_trim_deg = config.rt_max_pose_trim_deg;
  shadow.pressure_stale_ms = static_cast<int>(config.rt_stale_state_timeout_ms);
  shadow.pause_hold_position_guard_mm = config.pause_hold_position_guard_mm;
  shadow.pause_hold_drift_kp = config.pause_hold_drift_kp;
  shadow.pause_hold_integrator_leak = config.pause_hold_integrator_leak;
  shadow.contact_control = config.contact_control;
  shadow.force_estimator = config.force_estimator;
  shadow.orientation_trim = config.orientation_trim;
  return buildContactControlContract(shadow);
}

bool validateContactControlContract(const ContactControlContract& contract, std::string* reason) {
  const bool invalid_mode = contract.mode != "normal_axis_admittance";
  const bool invalid_mass = contract.seek_contact_admittance.virtual_mass <= 0.0 || contract.scan_follow_admittance.virtual_mass <= 0.0 || contract.pause_hold_admittance.virtual_mass <= 0.0;
  const bool invalid_dynamics = contract.seek_contact_admittance.max_step_mm <= 0.0 ||
                                contract.seek_contact_admittance.max_velocity_mm_s <= 0.0 ||
                                contract.seek_contact_admittance.max_acceleration_mm_s2 <= 0.0 ||
                                contract.scan_follow_admittance.max_displacement_mm < contract.scan_follow_admittance.max_step_mm;
  const bool invalid_tangent = contract.tangential_scan.tangent_speed_min_mm_s <= 0.0 ||
                               contract.tangential_scan.tangent_speed_max_mm_s < contract.tangential_scan.tangent_speed_min_mm_s ||
                               contract.tangential_scan.max_travel_mm <= 0.0;
  const bool invalid_trim = contract.orientation_trim.max_trim_deg <= 0.0 || contract.orientation_trim.lowpass_hz <= 0.0;
  const bool invalid_force = contract.force_estimator.stale_timeout_ms <= 0.0 ||
                             contract.force_estimator.timeout_ms < contract.force_estimator.stale_timeout_ms ||
                             (contract.force_estimator.pressure_weight + contract.force_estimator.wrench_weight) <= 0.0 ||
                             contract.force_estimator.min_confidence < 0.0 || contract.force_estimator.min_confidence > 1.0 ||
                             (contract.force_estimator.preferred_source != "fused" && contract.force_estimator.preferred_source != "pressure" && contract.force_estimator.preferred_source != "wrench");
  if (invalid_mode || invalid_mass || invalid_dynamics || invalid_tangent || invalid_trim || invalid_force) {
    if (reason != nullptr) {
      if (invalid_mode) *reason = "invalid_contact_control_mode";
      else if (invalid_mass) *reason = "invalid_contact_control_mass";
      else if (invalid_dynamics) *reason = "invalid_contact_control_dynamics";
      else if (invalid_tangent) *reason = "invalid_contact_control_tangent";
      else if (invalid_trim) *reason = "invalid_contact_control_trim";
      else *reason = "invalid_force_estimator_contract";
    }
    return false;
  }
  return true;
}

}  // namespace robot_core
