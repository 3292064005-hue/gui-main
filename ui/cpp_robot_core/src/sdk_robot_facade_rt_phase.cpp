#include "robot_core/sdk_robot_facade_internal.h"
#include "robot_core/deployment_policy.h"

#include <sstream>
#include <cstdlib>
#include <stdexcept>
#include <algorithm>
#include <cmath>

namespace robot_core {

using namespace sdk_robot_facade_internal;



namespace {

double rtScanWaypointDistanceM(const ScanWaypoint& a, const ScanWaypoint& b) {
  const double dx = b.x - a.x;
  const double dy = b.y - a.y;
  const double dz = b.z - a.z;
  return std::sqrt(dx * dx + dy * dy + dz * dz);
}

std::array<double, 16> scanWaypointToPose(const ScanWaypoint& waypoint) {
  return postureVectorToMatrix({waypoint.x, waypoint.y, waypoint.z, waypoint.rx, waypoint.ry, waypoint.rz});
}

std::vector<double> rtBuildCumulativeLengthsM(const std::vector<ScanWaypoint>& waypoints) {
  std::vector<double> cumulative;
  cumulative.reserve(waypoints.size());
  double total = 0.0;
  cumulative.push_back(0.0);
  for (std::size_t idx = 1; idx < waypoints.size(); ++idx) {
    total += std::max(0.0, rtScanWaypointDistanceM(waypoints[idx - 1], waypoints[idx]));
    cumulative.push_back(total);
  }
  return cumulative;
}

std::array<double, 16> interpolatePoseOnSegment(const std::vector<ScanWaypoint>& waypoints, const std::vector<double>& cumulative_lengths_m, double progress_m) {
  if (waypoints.empty()) return identityPoseMatrix();
  if (waypoints.size() == 1 || cumulative_lengths_m.empty()) return scanWaypointToPose(waypoints.front());
  const double total = cumulative_lengths_m.back();
  const double clamped = std::clamp(progress_m, 0.0, total);
  std::size_t upper = 1;
  while (upper < cumulative_lengths_m.size() && cumulative_lengths_m[upper] < clamped) ++upper;
  if (upper >= waypoints.size()) return scanWaypointToPose(waypoints.back());
  const std::size_t lower = upper - 1;
  const double span = std::max(1e-9, cumulative_lengths_m[upper] - cumulative_lengths_m[lower]);
  const double alpha = std::clamp((clamped - cumulative_lengths_m[lower]) / span, 0.0, 1.0);
  auto a = scanWaypointToPose(waypoints[lower]);
  auto b = scanWaypointToPose(waypoints[upper]);
  std::array<double, 16> out{};
  for (std::size_t i = 0; i < out.size(); ++i) out[i] = a[i] + (b[i] - a[i]) * alpha;
  return out;
}

}  // namespace

class RtControlAdapter {
public:
  explicit RtControlAdapter(SdkRobotFacade& owner) : owner_(owner) {}

  bool stop(std::string* reason) {
    bool live_ok = true;
    std::string local_reason;
    if (!owner_.connected_) {
      owner_.finalizeRtStopLocal("controller_not_connected");
      if (reason != nullptr) *reason = "controller_not_connected";
      return false;
    }
    if (!owner_.liveBindingEstablished()) {
      live_ok = false;
      local_reason = "live_binding_required";
      if (reason != nullptr) *reason = local_reason;
    }
#ifdef ROBOT_CORE_WITH_XCORE_SDK
    if (live_ok && owner_.live_binding_established_ && owner_.rt_controller_ != nullptr) {
      try {
        try { owner_.rt_controller_->stopLoop(); } catch (...) {}
        try { owner_.rt_controller_->stopMove(); } catch (...) {}
        try { owner_.robot_->stopReceiveRobotState(); } catch (...) {}
      } catch (const std::exception& ex) {
        live_ok = false;
        local_reason = ex.what();
        if (reason != nullptr) *reason = local_reason;
      }
    }
#endif
    owner_.finalizeRtStopLocal(local_reason);
    if (!local_reason.empty()) owner_.captureFailure("stopRt", local_reason);
    return live_ok;
  }

  bool beginMainline(const std::string& phase, int nominal_loop_hz, std::string* reason) {
    return owner_.beginRtMainlineInternal(phase, nominal_loop_hz, reason);
  }

  void updatePhase(const std::string& phase, const std::string& detail) {
    owner_.updateRtPhaseInternal(phase, detail);
  }

  void finishMainline(const std::string& phase, const std::string& detail) {
    owner_.finishRtMainlineInternal(phase, detail);
  }

private:
  SdkRobotFacade& owner_;
};

bool SdkRobotFacade::populateObservedState(RtObservedState& out, std::string* reason) {
  out = {};
  out.tcp_pose = postureVectorToMatrix(tcp_pose_);
  for (std::size_t idx = 0; idx < std::min<std::size_t>(6, joint_pos_.size()); ++idx) out.joint_pos[idx] = joint_pos_[idx];
  for (std::size_t idx = 0; idx < std::min<std::size_t>(6, joint_vel_.size()); ++idx) out.joint_vel[idx] = joint_vel_[idx];
  for (std::size_t idx = 0; idx < std::min<std::size_t>(6, joint_torque_.size()); ++idx) out.joint_torque[idx] = joint_torque_[idx];
  const double now_s = std::chrono::duration<double>(std::chrono::steady_clock::now().time_since_epoch()).count();
  out.monotonic_time_s = now_s;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && robot_ != nullptr) {
    try {
      std::array<double, 16> tcp_pose{};
      std::array<double, 6> joint_pos{};
      std::array<double, 6> joint_vel{};
      std::array<double, 6> joint_tau{};
      std::array<double, 6> ext_tau{};
      const bool got_pose = (robot_->getStateData(rokae::RtSupportedFields::tcpPose_m, tcp_pose) == 0);
      const bool got_joints = (robot_->getStateData(rokae::RtSupportedFields::jointPos_m, joint_pos) == 0);
      const bool got_joint_vel = (robot_->getStateData(rokae::RtSupportedFields::jointVel_m, joint_vel) == 0);
      const bool got_tau = (robot_->getStateData(rokae::RtSupportedFields::tau_m, joint_tau) == 0);
      const bool got_ext = (robot_->getStateData(rokae::RtSupportedFields::tauExt_inBase, ext_tau) == 0);
      if (got_pose) out.tcp_pose = tcp_pose;
      if (got_joints) out.joint_pos = joint_pos;
      if (got_joint_vel) out.joint_vel = joint_vel;
      if (got_tau) out.joint_torque = joint_tau;
      if (got_ext) out.external_wrench = ext_tau;
      out.valid = got_pose && got_joints;
      if (out.valid) {
        last_rt_state_sample_time_s_ = now_s;
        const std::size_t axis = std::min<std::size_t>(11, rt_phase_loop_state_.contact_axis_index);
        if (last_rt_observed_pose_initialized_ && now_s > last_rt_observed_time_s_) {
          const double dt = now_s - last_rt_observed_time_s_;
          out.normal_axis_velocity_m_s = (out.tcp_pose[axis] - last_rt_observed_pose_[axis]) / std::max(1e-6, dt);
        }
        last_rt_observed_pose_ = out.tcp_pose;
        last_rt_observed_pose_initialized_ = true;
        last_rt_observed_time_s_ = now_s;
      }
    } catch (const std::exception& ex) {
      if (reason != nullptr) *reason = ex.what();
      out.valid = false;
    }
    out.age_ms = last_rt_state_sample_time_s_ > 0.0 ? (now_s - last_rt_state_sample_time_s_) * 1000.0 : rt_phase_contract_.common.stale_state_timeout_ms + 1.0;
    out.pressure_force_n = ai_.count("board0_port0") ? ai_.at("board0_port0") : 0.0;
    out.pressure_age_ms = out.age_ms;
    out.pressure_valid = ai_.count("board0_port0") > 0;
    out.stale = out.age_ms > rt_phase_contract_.common.stale_state_timeout_ms;
    return out.valid;
  }
#endif
  out.valid = connected_;
  out.age_ms = 0.0;
  out.normal_axis_velocity_m_s = 0.0;
  out.pressure_force_n = ai_.count("board0_port0") ? ai_.at("board0_port0") : 0.0;
  out.pressure_age_ms = 0.0;
  out.pressure_valid = ai_.count("board0_port0") > 0;
  out.stale = false;
  return out.valid;
}

RtPhaseStepResult SdkRobotFacade::stepSeekContact(const RtObservedState& state) {
  RtPhaseStepResult result{};
  result.telemetry.phase_name = "seek_contact";
  if (!state.valid || state.stale) {
    result.verdict = RtPhaseVerdict::StaleState;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  auto& loop = rt_phase_loop_state_;
  if (!loop.anchor_initialized) {
    if (planned_segment_.configured && !planned_segment_.waypoints.empty()) {
      loop.anchor_pose = scanWaypointToPose(planned_segment_.waypoints.front());
      loop.hold_reference_pose = loop.anchor_pose;
    } else {
      loop.anchor_pose = state.tcp_pose;
      loop.hold_reference_pose = state.tcp_pose;
    }
    loop.anchor_initialized = true;
  }
  const double dt = 1.0 / std::max(1, nominal_rt_loop_hz_);
  loop.phase_time_s += dt;
  normal_admittance_controller_.configure(contact_control_contract_.seek_contact_admittance);
  NormalForceEstimatorInput input{};
  const std::size_t axis = std::min<std::size_t>(5, loop.contact_axis_index == translationIndexForAxis(0) ? 0 : (loop.contact_axis_index == translationIndexForAxis(1) ? 1 : 2));
  input.pressure_force_n = state.pressure_force_n;
  input.pressure_valid = state.pressure_valid;
  input.pressure_age_ms = state.pressure_age_ms;
  input.wrench_force_n = state.external_wrench[axis];
  input.wrench_valid = true;
  input.wrench_age_ms = state.age_ms;
  input.contact_direction_sign = loop.contact_direction_sign;
  const auto estimate = normal_force_estimator_.estimate(input);
  if (!estimate.valid) {
    result.verdict = RtPhaseVerdict::StaleState;
    result.telemetry.normal_force_source = estimate.source;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  const auto command = normal_admittance_controller_.step(rt_phase_contract_.seek_contact.force_target_n, estimate.estimated_force_n, dt);
  const double velocity = measuredNormalVelocity(state);
  const double error = command.state.force_error_n;
  loop.last_normal_error_n = error;
  if (std::abs(error) <= rt_phase_contract_.seek_contact.force_tolerance_n &&
      std::abs(velocity) <= mmToM(rt_phase_contract_.seek_contact.quiet_velocity_mm_s)) {
    ++loop.stable_cycles;
  } else {
    loop.stable_cycles = 0;
  }
  result.telemetry.normal_force_error_n = error;
  result.telemetry.estimated_normal_force_n = estimate.estimated_force_n;
  result.telemetry.normal_force_confidence = estimate.confidence;
  result.telemetry.normal_force_source = estimate.source;
  result.telemetry.admittance_displacement_m = command.state.x_m;
  result.telemetry.admittance_velocity_m_s = command.state.v_m_s;
  result.telemetry.admittance_saturated = command.state.saturated;
  result.telemetry.stable_cycles = loop.stable_cycles;
  if (loop.stable_cycles >= static_cast<unsigned>(std::max(1, rt_phase_contract_.seek_contact.establish_cycles))) {
    result.command_pose = state.tcp_pose;
    result.verdict = RtPhaseVerdict::PhaseCompleted;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  loop.seek_progress_m = std::clamp(loop.seek_progress_m + command.delta_normal_m, -mmToM(rt_phase_contract_.seek_contact.max_travel_mm), mmToM(rt_phase_contract_.seek_contact.max_travel_mm));
  result.command_pose = loop.anchor_pose;
  result.command_pose[loop.contact_axis_index] = loop.anchor_pose[loop.contact_axis_index] + loop.contact_direction_sign * loop.seek_progress_m;
  result.telemetry.tangent_progress_m = loop.seek_progress_m;
  if (std::abs(error) > rt_phase_contract_.common.max_force_error_n) {
    result.verdict = RtPhaseVerdict::ExceededForce;
  }
  last_phase_telemetry_ = result.telemetry;
  return result;
}

RtPhaseStepResult SdkRobotFacade::stepScanFollow(const RtObservedState& state) {
  RtPhaseStepResult result{};
  result.telemetry.phase_name = "scan_follow";
  if (!state.valid || state.stale) {
    result.verdict = RtPhaseVerdict::StaleState;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  auto& loop = rt_phase_loop_state_;
  if (!loop.anchor_initialized) {
    if (planned_segment_.configured && !planned_segment_.waypoints.empty()) {
      loop.anchor_pose = scanWaypointToPose(planned_segment_.waypoints.front());
      loop.hold_reference_pose = loop.anchor_pose;
    } else {
      loop.anchor_pose = state.tcp_pose;
      loop.hold_reference_pose = state.tcp_pose;
    }
    loop.anchor_initialized = true;
  }
  const double dt = 1.0 / std::max(1, nominal_rt_loop_hz_);
  loop.phase_time_s += dt;
  normal_admittance_controller_.configure(contact_control_contract_.scan_follow_admittance);
  tangential_scan_controller_.configure(contact_control_contract_.tangential_scan);
  orientation_trim_controller_.configure(contact_control_contract_.orientation_trim);
  const std::size_t axis = std::min<std::size_t>(5, loop.contact_axis_index == translationIndexForAxis(0) ? 0 : (loop.contact_axis_index == translationIndexForAxis(1) ? 1 : 2));
  NormalForceEstimatorInput input{};
  input.pressure_force_n = state.pressure_force_n;
  input.pressure_valid = state.pressure_valid;
  input.pressure_age_ms = state.pressure_age_ms;
  input.wrench_force_n = state.external_wrench[axis];
  input.wrench_valid = true;
  input.wrench_age_ms = state.age_ms;
  input.contact_direction_sign = loop.contact_direction_sign;
  const auto estimate = normal_force_estimator_.estimate(input);
  if (!estimate.valid) {
    result.verdict = RtPhaseVerdict::NeedPauseHold;
    result.telemetry.normal_force_source = estimate.source;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  const auto normal = normal_admittance_controller_.step(rt_phase_contract_.scan_follow.force_target_n, estimate.estimated_force_n, dt);
  const auto tangent = tangential_scan_controller_.advance(rt_config_.scan_speed_mm_s, dt);
  const auto trim = orientation_trim_controller_.step(normal.state.force_error_n / std::max(0.1, rt_phase_contract_.common.max_force_error_n), dt);
  loop.scan_progress_m = tangent.progress_m;
  const bool plan_driven = planned_segment_.configured && !planned_segment_.waypoints.empty();
  if (plan_driven) {
    const double segment_length_m = std::max(planned_segment_.total_length_m, mmToM(std::max(0.5, rt_config_.sample_step_mm)) * std::max<std::size_t>(1, planned_segment_.waypoints.size() - 1));
    const double clamped_progress_m = std::clamp(tangent.progress_m, 0.0, segment_length_m);
    result.command_pose = interpolatePoseOnSegment(planned_segment_.waypoints, planned_segment_.cumulative_lengths_m, clamped_progress_m);
    result.command_pose[loop.contact_axis_index] += loop.contact_direction_sign * normal.state.x_m;
    result.telemetry.tangent_progress_m = clamped_progress_m;
    if (clamped_progress_m >= segment_length_m - 1e-6) {
      result.finished = true;
      result.verdict = RtPhaseVerdict::PhaseCompleted;
    }
  } else {
    result.command_pose = loop.anchor_pose;
    result.command_pose[loop.scan_axis_index] = loop.anchor_pose[loop.scan_axis_index] + tangent.progress_m;
    result.command_pose[loop.contact_axis_index] = loop.anchor_pose[loop.contact_axis_index] + loop.contact_direction_sign * normal.state.x_m;
    result.command_pose[loop.lateral_axis_index] = loop.anchor_pose[loop.lateral_axis_index] + tangent.lateral_offset_m;
    result.telemetry.tangent_progress_m = tangent.progress_m;
    if (tangent.saturated || tangent.progress_m >= mmToM(rt_phase_contract_.scan_follow.max_travel_mm)) {
      result.finished = true;
      result.verdict = RtPhaseVerdict::PhaseCompleted;
    }
  }
  const auto trim_anchor_pose = result.command_pose;
  applyLocalPitchTrim(result.command_pose, trim_anchor_pose, trim.trim_rad);
  result.telemetry.normal_force_error_n = normal.state.force_error_n;
  result.telemetry.estimated_normal_force_n = estimate.estimated_force_n;
  result.telemetry.normal_force_confidence = estimate.confidence;
  result.telemetry.normal_force_source = estimate.source;
  result.telemetry.pose_trim_rad = trim.trim_rad;
  result.telemetry.orientation_trim_saturated = trim.saturated;
  result.telemetry.admittance_displacement_m = normal.state.x_m;
  result.telemetry.admittance_velocity_m_s = normal.state.v_m_s;
  result.telemetry.admittance_saturated = normal.state.saturated;
  if (result.verdict == RtPhaseVerdict::Continue && (std::abs(normal.state.force_error_n) > rt_phase_contract_.common.max_force_error_n || normal.state.saturated)) {
    result.verdict = RtPhaseVerdict::NeedPauseHold;
  }
  last_phase_telemetry_ = result.telemetry;
  return result;
}

RtPhaseStepResult SdkRobotFacade::stepPauseHold(const RtObservedState& state) {
  RtPhaseStepResult result{};
  result.telemetry.phase_name = "pause_hold";
  if (!state.valid || state.stale) {
    result.verdict = RtPhaseVerdict::StaleState;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  auto& loop = rt_phase_loop_state_;
  if (!loop.hold_reference_initialized) {
    loop.hold_reference_pose = state.tcp_pose;
    loop.hold_reference_initialized = true;
  }
  const double dt = 1.0 / std::max(1, nominal_rt_loop_hz_);
  normal_admittance_controller_.configure(contact_control_contract_.pause_hold_admittance);
  const std::size_t axis = std::min<std::size_t>(5, loop.contact_axis_index == translationIndexForAxis(0) ? 0 : (loop.contact_axis_index == translationIndexForAxis(1) ? 1 : 2));
  NormalForceEstimatorInput input{};
  input.pressure_force_n = state.pressure_force_n;
  input.pressure_valid = state.pressure_valid;
  input.pressure_age_ms = state.pressure_age_ms;
  input.wrench_force_n = state.external_wrench[axis];
  input.wrench_valid = true;
  input.wrench_age_ms = state.age_ms;
  input.contact_direction_sign = loop.contact_direction_sign;
  const auto estimate = normal_force_estimator_.estimate(input);
  if (!estimate.valid) {
    result.verdict = RtPhaseVerdict::NeedRetreat;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  const auto command = normal_admittance_controller_.step(rt_phase_contract_.scan_follow.force_target_n, estimate.estimated_force_n, dt);
  result.command_pose = loop.hold_reference_pose;
  result.command_pose[loop.contact_axis_index] = loop.hold_reference_pose[loop.contact_axis_index] + loop.contact_direction_sign * command.state.x_m;
  result.telemetry.normal_force_error_n = command.state.force_error_n;
  result.telemetry.estimated_normal_force_n = estimate.estimated_force_n;
  result.telemetry.normal_force_confidence = estimate.confidence;
  result.telemetry.normal_force_source = estimate.source;
  result.telemetry.admittance_displacement_m = command.state.x_m;
  result.telemetry.admittance_velocity_m_s = command.state.v_m_s;
  result.telemetry.admittance_saturated = command.state.saturated;
  if (std::abs(command.state.force_error_n) > rt_phase_contract_.pause_hold.force_guard_n || command.state.saturated) {
    result.verdict = RtPhaseVerdict::NeedRetreat;
  }
  last_phase_telemetry_ = result.telemetry;
  return result;
}

RtPhaseStepResult SdkRobotFacade::stepControlledRetract(const RtObservedState& state) {
  RtPhaseStepResult result{};
  result.telemetry.phase_name = "controlled_retract";
  if (!state.valid || state.stale) {
    result.verdict = RtPhaseVerdict::StaleState;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  auto& loop = rt_phase_loop_state_;
  if (!loop.anchor_initialized) {
    loop.anchor_pose = state.tcp_pose;
    loop.anchor_initialized = true;
  }
  const double dt = 1.0 / std::max(1, nominal_rt_loop_hz_);
  loop.phase_time_s += dt;
  const std::size_t axis = std::min<std::size_t>(5, loop.contact_axis_index == translationIndexForAxis(0) ? 0 : (loop.contact_axis_index == translationIndexForAxis(1) ? 1 : 2));
  NormalForceEstimatorInput input{};
  input.pressure_force_n = state.pressure_force_n;
  input.pressure_valid = state.pressure_valid;
  input.pressure_age_ms = state.pressure_age_ms;
  input.wrench_force_n = state.external_wrench[axis];
  input.wrench_valid = true;
  input.wrench_age_ms = state.age_ms;
  input.contact_direction_sign = loop.contact_direction_sign;
  const auto estimate = normal_force_estimator_.estimate(input);
  const double target_velocity_mm_s = std::max(0.1, rt_config_.retreat_speed_mm_s);
  loop.retract_accel_mm_s2 = std::min(rt_phase_contract_.common.max_cart_acc_mm_s2,
                                      loop.retract_accel_mm_s2 + rt_phase_contract_.controlled_retract.jerk_limit_mm_s3 * dt);
  loop.retract_velocity_mm_s = std::min(target_velocity_mm_s,
                                        loop.retract_velocity_mm_s + loop.retract_accel_mm_s2 * dt);
  const double retract_step_m = mmToM(loop.retract_velocity_mm_s) * dt;
  const double release_force = std::abs(estimate.estimated_force_n);
  result.command_pose = loop.anchor_pose;
  if (!loop.retract_released) {
    loop.retract_progress_m += retract_step_m;
    result.command_pose[loop.contact_axis_index] = loop.anchor_pose[loop.contact_axis_index] - loop.contact_direction_sign * loop.retract_progress_m;
    if (release_force <= rt_phase_contract_.controlled_retract.release_force_n) {
      ++loop.release_cycles;
    } else {
      loop.release_cycles = 0;
    }
    if (loop.release_cycles >= static_cast<unsigned>(rt_phase_contract_.controlled_retract.release_cycles)) {
      loop.retract_released = true;
    }
    if (loop.retract_progress_m >= mmToM(rt_phase_contract_.controlled_retract.max_travel_mm)) {
      result.finished = true;
      result.verdict = RtPhaseVerdict::ExceededTravel;
      last_phase_telemetry_ = result.telemetry;
      return result;
    }
  } else {
    loop.retract_safe_gap_progress_m += retract_step_m;
    const double total = loop.retract_progress_m + loop.retract_safe_gap_progress_m;
    result.command_pose[loop.contact_axis_index] = loop.anchor_pose[loop.contact_axis_index] - loop.contact_direction_sign * total;
    if (loop.retract_safe_gap_progress_m >= mmToM(rt_phase_contract_.controlled_retract.safe_gap_mm)) {
      result.finished = true;
      result.verdict = RtPhaseVerdict::PhaseCompleted;
      last_phase_telemetry_ = result.telemetry;
      return result;
    }
  }
  result.telemetry.estimated_normal_force_n = estimate.estimated_force_n;
  result.telemetry.normal_force_confidence = estimate.confidence;
  result.telemetry.normal_force_source = estimate.source;
  result.telemetry.retract_progress_m = loop.retract_progress_m + loop.retract_safe_gap_progress_m;
  if (loop.phase_time_s * 1000.0 >= rt_phase_contract_.controlled_retract.timeout_ms) {
    result.finished = true;
    result.verdict = RtPhaseVerdict::NeedFaultStop;
  }
  last_phase_telemetry_ = result.telemetry;
  return result;
}


}  // namespace robot_core
