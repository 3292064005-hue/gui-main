#include "robot_core/sdk_robot_facade_internal.h"

#include "robot_core/contact_control_contract.h"

namespace robot_core {

using namespace sdk_robot_facade_internal;

namespace {

double rtContractScanWaypointDistanceM(const ScanWaypoint& a, const ScanWaypoint& b) {
  const double dx = b.x - a.x;
  const double dy = b.y - a.y;
  const double dz = b.z - a.z;
  return std::sqrt(dx * dx + dy * dy + dz * dz);
}

std::vector<double> rtContractBuildCumulativeLengthsM(const std::vector<ScanWaypoint>& waypoints) {
  std::vector<double> cumulative;
  cumulative.reserve(waypoints.size());
  double total = 0.0;
  cumulative.push_back(0.0);
  for (std::size_t idx = 1; idx < waypoints.size(); ++idx) {
    total += std::max(0.0, rtContractScanWaypointDistanceM(waypoints[idx - 1], waypoints[idx]));
    cumulative.push_back(total);
  }
  return cumulative;
}

}  // namespace

void SdkRobotFacade::setPlannedSegment(const ScanSegment& segment) {
  planned_segment_.configured = true;
  planned_segment_.segment_id = segment.segment_id;
  planned_segment_.waypoints = segment.waypoints;
  planned_segment_.cumulative_lengths_m = rtContractBuildCumulativeLengthsM(segment.waypoints);
  planned_segment_.total_length_m = planned_segment_.cumulative_lengths_m.empty() ? 0.0 : planned_segment_.cumulative_lengths_m.back();
  planned_segment_.transition_policy = segment.transition_policy;
  planned_segment_.target_force_n = segment.target_pressure;
}

void SdkRobotFacade::clearPlannedSegment() {
  planned_segment_ = PlannedSegmentRuntime{};
}

int SdkRobotFacade::plannedSegmentId() const {
  return planned_segment_.configured ? planned_segment_.segment_id : 0;
}

std::size_t SdkRobotFacade::plannedWaypointCount() const {
  return planned_segment_.waypoints.size();
}

std::array<double, 16> SdkRobotFacade::defaultPoseMatrix() {
  return identityPoseMatrix();
}

double SdkRobotFacade::measuredNormalForce(const RtObservedState& state) const {
  return normal_force_estimator_.lastEstimate().estimated_force_n;
}

void SdkRobotFacade::configureContactControllersFromRuntimeConfig() {
  contact_control_contract_ = buildContactControlContract(rt_config_);
  normal_force_estimator_.configure(contact_control_contract_.force_estimator);
  normal_admittance_controller_.configure(contact_control_contract_.seek_contact_admittance);
  tangential_scan_controller_.configure(contact_control_contract_.tangential_scan);
  orientation_trim_controller_.configure(contact_control_contract_.orientation_trim);
  rt_config_.contact_control.mode = "normal_axis_admittance";
  rt_config_.contact_control.virtual_mass = contact_control_contract_.seek_contact_admittance.virtual_mass;
  rt_config_.contact_control.virtual_damping = contact_control_contract_.seek_contact_admittance.virtual_damping;
  rt_config_.contact_control.virtual_stiffness = contact_control_contract_.seek_contact_admittance.virtual_stiffness;
  rt_config_.contact_control.force_deadband_n = contact_control_contract_.seek_contact_admittance.force_deadband_n;
  rt_config_.contact_control.max_normal_step_mm = contact_control_contract_.seek_contact_admittance.max_step_mm;
  rt_config_.contact_control.max_normal_velocity_mm_s = contact_control_contract_.seek_contact_admittance.max_velocity_mm_s;
  rt_config_.contact_control.max_normal_acc_mm_s2 = contact_control_contract_.seek_contact_admittance.max_acceleration_mm_s2;
  rt_config_.contact_control.max_normal_travel_mm = contact_control_contract_.seek_contact_admittance.max_displacement_mm;
  rt_config_.contact_control.anti_windup_limit_n = contact_control_contract_.seek_contact_admittance.integrator_limit_n;
  rt_config_.contact_control.integrator_leak = contact_control_contract_.pause_hold_admittance.integrator_leak;
  rt_config_.force_estimator.preferred_source = contact_control_contract_.force_estimator.preferred_source;
  rt_config_.force_estimator.pressure_weight = contact_control_contract_.force_estimator.pressure_weight;
  rt_config_.force_estimator.wrench_weight = contact_control_contract_.force_estimator.wrench_weight;
  rt_config_.force_estimator.stale_timeout_ms = static_cast<int>(contact_control_contract_.force_estimator.stale_timeout_ms);
  rt_config_.force_estimator.timeout_ms = static_cast<int>(contact_control_contract_.force_estimator.timeout_ms);
  rt_config_.force_estimator.auto_bias_zero = contact_control_contract_.force_estimator.auto_bias_zero;
  rt_config_.force_estimator.min_confidence = contact_control_contract_.force_estimator.min_confidence;
  rt_config_.orientation_trim.gain = contact_control_contract_.orientation_trim.gain;
  rt_config_.orientation_trim.max_trim_deg = contact_control_contract_.orientation_trim.max_trim_deg;
  rt_config_.orientation_trim.lowpass_hz = contact_control_contract_.orientation_trim.lowpass_hz;
}

double SdkRobotFacade::measuredNormalVelocity(const RtObservedState& state) const {
  return state.normal_axis_velocity_m_s;
}

void SdkRobotFacade::clampCommandPose(std::array<double, 16>& pose, const std::array<double, 16>& anchor) {
  const double dt = 1.0 / std::max(1, nominal_rt_loop_hz_);
  const double max_step_m = mmToM(std::max(0.01, rt_phase_contract_.common.max_cart_step_mm));
  const double max_vel_m_s = mmToM(std::max(0.01, rt_phase_contract_.common.max_cart_vel_mm_s));
  const double max_acc_m_s2 = mmToM(std::max(1.0, rt_phase_contract_.common.max_cart_acc_mm_s2));
  const double prev_vel_m_s = rt_phase_loop_state_.last_command_step_m > 0.0 ? (rt_phase_loop_state_.last_command_step_m / dt) : 0.0;
  const double accel_limited_vel_m_s = std::min(max_vel_m_s, prev_vel_m_s + max_acc_m_s2 * dt);
  const double allowed_m = std::min(max_step_m, std::max(mmToM(0.01), accel_limited_vel_m_s * dt));
  double max_applied_delta_m = 0.0;
  for (const auto idx : kTranslationIndices) {
    const double delta = pose[idx] - anchor[idx];
    if (!std::isfinite(delta)) {
      pose[idx] = anchor[idx];
      continue;
    }
    const double clamped = clampSigned(delta, allowed_m);
    pose[idx] = anchor[idx] + clamped;
    max_applied_delta_m = std::max(max_applied_delta_m, std::abs(clamped));
  }
  rt_phase_loop_state_.last_command_step_m = max_applied_delta_m;
}

void SdkRobotFacade::clampPoseTrim(std::array<double, 16>& pose, const std::array<double, 16>& anchor) const {
  (void)anchor;
  for (auto& item : pose) {
    if (!std::isfinite(item)) item = 0.0;
  }
  pose[15] = 1.0;
}

void SdkRobotFacade::applyLocalPitchTrim(std::array<double, 16>& pose, const std::array<double, 16>& anchor, double trim_rad) const {
  const double c = std::cos(trim_rad);
  const double s = std::sin(trim_rad);
  pose = anchor;
  pose[0] = anchor[0] * c - anchor[2] * s;
  pose[1] = anchor[1];
  pose[2] = anchor[0] * s + anchor[2] * c;
  pose[4] = anchor[4] * c - anchor[6] * s;
  pose[5] = anchor[5];
  pose[6] = anchor[4] * s + anchor[6] * c;
  pose[8] = anchor[8] * c - anchor[10] * s;
  pose[9] = anchor[9];
  pose[10] = anchor[8] * s + anchor[10] * c;
  pose[3] = anchor[3];
  pose[7] = anchor[7];
  pose[11] = anchor[11];
  pose[12] = 0.0; pose[13] = 0.0; pose[14] = 0.0; pose[15] = 1.0;
}

void SdkRobotFacade::resetRtPhaseIntegrators() {
  rt_phase_loop_state_ = {};
  rt_phase_loop_state_.contact_axis_index = translationIndexForAxis(2);
  rt_phase_loop_state_.scan_axis_index = translationIndexForAxis(0);
  rt_phase_loop_state_.lateral_axis_index = translationIndexForAxis(1);
  rt_phase_loop_state_.contact_direction_sign = (rt_config_.desired_wrench_n[2] < 0.0) ? -1.0 : 1.0;
  normal_force_estimator_.reset();
  normal_admittance_controller_.reset();
  tangential_scan_controller_.reset();
  orientation_trim_controller_.reset();
  last_phase_telemetry_ = {};
}

void SdkRobotFacade::setRtPhaseControlContract(const RtPhaseControlContract& contract) {
  rt_phase_contract_ = contract;
  configureContactControllersFromRuntimeConfig();
}

bool SdkRobotFacade::validateRtControlContract(std::string* reason) const {
  if (rt_phase_contract_.common.max_cart_step_mm <= 0.0 ||
      rt_phase_contract_.common.max_cart_vel_mm_s <= 0.0 ||
      rt_phase_contract_.common.max_cart_acc_mm_s2 <= 0.0 ||
      rt_phase_contract_.common.max_pose_trim_deg <= 0.0 ||
      rt_phase_contract_.common.stale_state_timeout_ms <= 0.0 ||
      rt_phase_contract_.seek_contact.establish_cycles < 1 ||
      rt_phase_contract_.scan_follow.tangent_speed_min_mm_s <= 0.0 ||
      rt_phase_contract_.scan_follow.tangent_speed_max_mm_s < rt_phase_contract_.scan_follow.tangent_speed_min_mm_s ||
      rt_phase_contract_.controlled_retract.release_cycles < 1 ||
      rt_phase_contract_.controlled_retract.timeout_ms <= 0.0 ||
      rt_phase_contract_.controlled_retract.release_force_n > rt_phase_contract_.seek_contact.force_target_n) {
    if (reason != nullptr) {
      *reason = "invalid_rt_phase_control_contract";
    }
    return false;
  }
  return validateContactControlContract(contact_control_contract_, reason);
}


}  // namespace robot_core
