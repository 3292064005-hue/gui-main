#include "robot_core/sdk_robot_facade_internal.h"

#include <sstream>
#include <stdexcept>

namespace robot_core {

using namespace sdk_robot_facade_internal;

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
    if (!owner_.liveBindingEstablished() && !owner_.runtimeConfig().allow_contract_shell_writes) {
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
    loop.anchor_pose = state.tcp_pose;
    loop.hold_reference_pose = state.tcp_pose;
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
    loop.anchor_pose = state.tcp_pose;
    loop.hold_reference_pose = state.tcp_pose;
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
  result.command_pose = loop.anchor_pose;
  result.command_pose[loop.scan_axis_index] = loop.anchor_pose[loop.scan_axis_index] + tangent.progress_m;
  result.command_pose[loop.contact_axis_index] = loop.anchor_pose[loop.contact_axis_index] + loop.contact_direction_sign * normal.state.x_m;
  result.command_pose[loop.lateral_axis_index] = loop.anchor_pose[loop.lateral_axis_index] + tangent.lateral_offset_m;
  const auto trim_anchor_pose = result.command_pose;
  applyLocalPitchTrim(result.command_pose, trim_anchor_pose, trim.trim_rad);
  result.telemetry.normal_force_error_n = normal.state.force_error_n;
  result.telemetry.estimated_normal_force_n = estimate.estimated_force_n;
  result.telemetry.normal_force_confidence = estimate.confidence;
  result.telemetry.normal_force_source = estimate.source;
  result.telemetry.tangent_progress_m = tangent.progress_m;
  result.telemetry.pose_trim_rad = trim.trim_rad;
  result.telemetry.orientation_trim_saturated = trim.saturated;
  result.telemetry.admittance_displacement_m = normal.state.x_m;
  result.telemetry.admittance_velocity_m_s = normal.state.v_m_s;
  result.telemetry.admittance_saturated = normal.state.saturated;
  if (tangent.saturated || tangent.progress_m >= mmToM(rt_phase_contract_.scan_follow.max_travel_mm)) {
    result.finished = true;
    result.verdict = RtPhaseVerdict::PhaseCompleted;
    last_phase_telemetry_ = result.telemetry;
    return result;
  }
  if (std::abs(normal.state.force_error_n) > rt_phase_contract_.common.max_force_error_n || normal.state.saturated) {
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

bool SdkRobotFacade::beginRtMainlineInternal(const std::string& phase, int nominal_loop_hz, std::string* reason) {
  const int phase_loop_hz = nominal_loop_hz > 0 ? nominal_loop_hz : nominal_rt_loop_hz_;
  if (!ensurePoweredAuto(reason)) return false;
  if (!ensureRtController(reason)) return false;
  rt_phase_contract_.common.max_cart_step_mm = rt_config_.rt_max_cart_step_mm;
  rt_phase_contract_.common.max_cart_vel_mm_s = rt_config_.rt_max_cart_vel_mm_s;
  rt_phase_contract_.common.max_cart_acc_mm_s2 = rt_config_.rt_max_cart_acc_mm_s2;
  rt_phase_contract_.common.max_pose_trim_deg = rt_config_.rt_max_pose_trim_deg;
  rt_phase_contract_.common.stale_state_timeout_ms = rt_config_.rt_stale_state_timeout_ms;
  rt_phase_contract_.common.phase_transition_debounce_cycles = rt_config_.rt_phase_transition_debounce_cycles;
  rt_phase_contract_.common.max_force_error_n = rt_config_.rt_max_force_error_n;
  rt_phase_contract_.common.max_integrator_n = rt_config_.rt_integrator_limit_n;
  rt_phase_contract_.seek_contact.force_target_n = rt_config_.contact_force_target_n;
  rt_phase_contract_.seek_contact.force_tolerance_n = rt_config_.contact_force_tolerance_n;
  rt_phase_contract_.seek_contact.establish_cycles = rt_config_.contact_establish_cycles;
  rt_phase_contract_.seek_contact.admittance_gain = rt_config_.normal_admittance_gain;
  rt_phase_contract_.seek_contact.damping_gain = rt_config_.normal_damping_gain;
  rt_phase_contract_.seek_contact.max_step_mm = rt_config_.seek_contact_max_step_mm;
  rt_phase_contract_.seek_contact.max_travel_mm = rt_config_.seek_contact_max_travel_mm;
  rt_phase_contract_.seek_contact.quiet_velocity_mm_s = rt_config_.normal_velocity_quiet_threshold_mm_s;
  rt_phase_contract_.scan_follow.force_target_n = rt_config_.scan_force_target_n;
  rt_phase_contract_.scan_follow.force_tolerance_n = rt_config_.scan_force_tolerance_n;
  rt_phase_contract_.scan_follow.normal_pi_kp = rt_config_.scan_normal_pi_kp;
  rt_phase_contract_.scan_follow.normal_pi_ki = rt_config_.scan_normal_pi_ki;
  rt_phase_contract_.scan_follow.tangent_speed_min_mm_s = rt_config_.scan_tangent_speed_min_mm_s;
  rt_phase_contract_.scan_follow.tangent_speed_max_mm_s = rt_config_.scan_tangent_speed_max_mm_s;
  rt_phase_contract_.scan_follow.pose_trim_gain = rt_config_.scan_pose_trim_gain;
  rt_phase_contract_.scan_follow.enable_lateral_modulation = rt_config_.scan_follow_enable_lateral_modulation;
  rt_phase_contract_.scan_follow.max_travel_mm = rt_config_.scan_follow_max_travel_mm;
  rt_phase_contract_.scan_follow.lateral_amplitude_mm = rt_config_.scan_follow_lateral_amplitude_mm;
  rt_phase_contract_.scan_follow.modulation_frequency_hz = rt_config_.scan_follow_frequency_hz;
  rt_phase_contract_.pause_hold.position_guard_mm = rt_config_.pause_hold_position_guard_mm;
  rt_phase_contract_.pause_hold.force_guard_n = rt_config_.pause_hold_force_guard_n;
  rt_phase_contract_.pause_hold.drift_kp = rt_config_.pause_hold_drift_kp;
  rt_phase_contract_.pause_hold.drift_ki = rt_config_.pause_hold_drift_ki;
  rt_phase_contract_.pause_hold.integrator_leak = rt_config_.pause_hold_integrator_leak;
  rt_phase_contract_.controlled_retract.release_force_n = rt_config_.retract_release_force_n;
  rt_phase_contract_.controlled_retract.release_cycles = rt_config_.retract_release_cycles;
  rt_phase_contract_.controlled_retract.safe_gap_mm = rt_config_.retract_safe_gap_mm;
  rt_phase_contract_.controlled_retract.max_travel_mm = rt_config_.retract_max_travel_mm;
  rt_phase_contract_.controlled_retract.jerk_limit_mm_s3 = rt_config_.retract_jerk_limit_mm_s3;
  rt_phase_contract_.controlled_retract.timeout_ms = rt_config_.retract_timeout_ms;
  rt_phase_contract_.controlled_retract.retract_travel_mm = rt_config_.retract_travel_mm;
  configureContactControllersFromRuntimeConfig();
  if (!validateRtControlContract(reason)) return false;
  if (!requireLiveWrite("beginRtMainline", reason)) return false;
  std::vector<std::string> rt_fields = {"q_m", "dq_m", "tau_m", "pos_m", "tau_ext_base"};
  if (!ensureRtStateStream(rt_fields, reason)) return false;
  if (!applyRtConfig(rt_config_, reason)) return false;
#ifdef ROBOT_CORE_WITH_XCORE_SDK
  if (live_binding_established_ && rt_controller_ != nullptr) {
    try {
      if (rt_loop_active_) {
        try { rt_controller_->stopLoop(); } catch (...) {}
        try { rt_controller_->stopMove(); } catch (...) {}
        rt_loop_active_ = false;
      }
      auto phase_impedance = rt_config_.cartesian_impedance;
      auto phase_wrench = rt_config_.desired_wrench_n;
      if (phase == "seek_contact") {
        phase_impedance[2] = std::min(phase_impedance[2], 800.0);
      } else if (phase == "pause_hold" || phase == "controlled_retract") {
        phase_wrench = {0.0, 0.0, 0.0, 0.0, 0.0, 0.0};
      }
      std::error_code phase_ec;
      rt_controller_->setCartesianImpedance(phase_impedance, phase_ec);
      if (!applyErrorCode("setCartesianImpedance(phase override)", phase_ec, reason)) return false;
      rt_controller_->setCartesianImpedanceDesiredTorque(phase_wrench, phase_ec);
      if (!applyErrorCode("setCartesianImpedanceDesiredTorque(phase override)", phase_ec, reason)) return false;
      resetRtPhaseIntegrators();
      active_rt_phase_ = phase;
      setRtPhaseCode(phase);
      rt_controller_->startMove(rokae::RtControllerMode::cartesianImpedance);
      auto phase_callback = [this, phase]() mutable {
        RtObservedState observed{};
        populateObservedState(observed, nullptr);
        RtPhaseStepResult result{};
        if (active_rt_phase_ == "seek_contact") {
          result = stepSeekContact(observed);
        } else if (active_rt_phase_ == "scan_follow") {
          result = stepScanFollow(observed);
        } else if (active_rt_phase_ == "pause_hold") {
          result = stepPauseHold(observed);
        } else if (active_rt_phase_ == "controlled_retract") {
          result = stepControlledRetract(observed);
        } else {
          result.command_pose = observed.valid ? observed.tcp_pose : defaultPoseMatrix();
          result.finished = true;
          result.verdict = RtPhaseVerdict::PhaseCompleted;
        }
        if (result.verdict != RtPhaseVerdict::Continue &&
            result.verdict != RtPhaseVerdict::PhaseCompleted &&
            result.verdict != RtPhaseVerdict::StaleState) {
          if (rt_phase_loop_state_.pending_transition_verdict == result.verdict) {
            ++rt_phase_loop_state_.pending_transition_cycles;
          } else {
            rt_phase_loop_state_.pending_transition_verdict = result.verdict;
            rt_phase_loop_state_.pending_transition_cycles = 1;
          }
          if (rt_phase_loop_state_.pending_transition_cycles < static_cast<unsigned>(std::max(1, rt_phase_contract_.common.phase_transition_debounce_cycles))) {
            result.verdict = RtPhaseVerdict::Continue;
          } else {
            rt_phase_loop_state_.pending_transition_verdict = RtPhaseVerdict::Continue;
            rt_phase_loop_state_.pending_transition_cycles = 0;
          }
        } else {
          rt_phase_loop_state_.pending_transition_verdict = RtPhaseVerdict::Continue;
          rt_phase_loop_state_.pending_transition_cycles = 0;
        }
        last_phase_telemetry_ = result.telemetry;
        rokae::CartesianPosition output{};
        if (result.command_pose == std::array<double, 16>{}) {
          result.command_pose = observed.valid ? observed.tcp_pose : defaultPoseMatrix();
        }
        clampCommandPose(result.command_pose, observed.valid ? observed.tcp_pose : defaultPoseMatrix());
        clampPoseTrim(result.command_pose, observed.valid ? observed.tcp_pose : defaultPoseMatrix());
        output.pos = result.command_pose;
        switch (result.verdict) {
          case RtPhaseVerdict::Continue:
            break;
          case RtPhaseVerdict::PhaseCompleted:
            output.setFinished();
            rt_loop_active_ = false;
            active_rt_phase_ = "idle";
            setRtPhaseCode("idle");
            break;
          case RtPhaseVerdict::NeedPauseHold:
            active_rt_phase_ = "pause_hold";
            resetRtPhaseIntegrators();
            setRtPhaseCode("pause_hold");
            break;
          case RtPhaseVerdict::NeedRetreat:
            active_rt_phase_ = "controlled_retract";
            resetRtPhaseIntegrators();
            setRtPhaseCode("controlled_retract");
            break;
          case RtPhaseVerdict::StaleState:
          case RtPhaseVerdict::NeedFaultStop:
          case RtPhaseVerdict::ExceededTravel:
          case RtPhaseVerdict::ExceededForce:
          case RtPhaseVerdict::InstabilityDetected:
            output.setFinished();
            rt_loop_active_ = false;
            active_rt_phase_ = "idle";
            binding_detail_ = "rt_fault_verdict";
            setRtPhaseCode("idle");
            break;
        }
        if (result.finished) {
          output.setFinished();
        }
        return output;
      };
      rt_controller_->setControlLoop<rokae::CartesianPosition>(phase_callback, 0, true);
      rt_controller_->startLoop(false);
      rt_loop_active_ = true;
    } catch (const std::exception& ex) {
      captureException("startMove(cartesianImpedance)", ex, reason);
      return false;
    }
  }
#endif
  active_rt_phase_ = phase;
  nominal_rt_loop_hz_ = phase_loop_hz;
  ++command_sequence_;
  registers_["spine.command.sequence"] = command_sequence_;
  setRtPhaseCode(phase);
  binding_detail_ = live_binding_established_ ? "rt_live_active" : "rt_contract_active";
  appendLog("beginRtMainline(phase=" + phase + ",nominal_loop_hz=" + std::to_string(nominal_rt_loop_hz_) + ")");
  refreshBindingTruth();
  return true;
}

void SdkRobotFacade::updateRtPhaseInternal(const std::string& phase, const std::string& detail) {
  active_rt_phase_ = phase;
  setRtPhaseCode(phase);
  appendLog("updateRtPhase(phase=" + phase + (detail.empty() ? "" : ",detail=" + detail) + ")");
}

void SdkRobotFacade::finishRtMainlineInternal(const std::string& phase, const std::string& detail) {
  std::string ignored;
  RtControlAdapter(*this).stop(&ignored);
  if (active_rt_phase_ == phase) active_rt_phase_ = "idle";
  binding_detail_ = "rt_finished";
  appendLog("finishRtMainline(phase=" + phase + (detail.empty() ? "" : ",detail=" + detail) + ")");
  refreshBindingTruth();
}


bool SdkRobotFacade::stopRt(std::string* reason) { return RtControlAdapter(*this).stop(reason); }
bool SdkRobotFacade::beginRtMainline(const std::string& phase, int nominal_loop_hz, std::string* reason) { return RtControlAdapter(*this).beginMainline(phase, nominal_loop_hz, reason); }
void SdkRobotFacade::updateRtPhase(const std::string& phase, const std::string& detail) { RtControlAdapter(*this).updatePhase(phase, detail); }
void SdkRobotFacade::finishRtMainline(const std::string& phase, const std::string& detail) { RtControlAdapter(*this).finishMainline(phase, detail); }

}  // namespace robot_core
