#include "robot_core/core_runtime.h"

#include "core_runtime_query_json_helpers.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {

using namespace query_json;

std::string CoreRuntime::handleMotionQueryCommandLocked(const RuntimeCommandInvocation& invocation) {
  const auto& command = invocation.command;
  if (command == "get_motion_contract") {
           const auto* request = invocation.requestAs<GetMotionContractRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: get_motion_contract");
           }
           (void)request;
           const auto runtime_cfg = this->procedure_executor_.sdk_robot.queryPort().runtimeConfig();
           const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
           const auto data = json::object(std::vector<std::string>{
               json::field("rt_mode", json::quote(this->state_store_.config.rt_mode)),
               json::field("clinical_mainline_mode", json::quote(identity.clinical_mainline_mode)),
               json::field("network_tolerance_percent", std::to_string(runtime_cfg.rt_network_tolerance_percent)),
               json::field("preferred_link", json::quote(runtime_cfg.preferred_link)),
               json::field("collision_behavior", json::quote(this->state_store_.config.collision_behavior)),
               json::field("collision_detection_enabled", json::boolLiteral(this->state_store_.config.collision_detection_enabled)),
               json::field("soft_limit_enabled", json::boolLiteral(this->state_store_.config.soft_limit_enabled)),
               json::field("single_control_source_required", json::boolLiteral(runtime_cfg.requires_single_control_source)),
               json::field("clinical_allowed_modes", json::stringArray(identity.clinical_allowed_modes)),
               json::field("contact_force_target_n", json::formatDouble(runtime_cfg.contact_force_target_n)),
               json::field("scan_force_target_n", json::formatDouble(runtime_cfg.scan_force_target_n)),
               json::field("retract_timeout_ms", json::formatDouble(runtime_cfg.retract_timeout_ms)),
               json::field("cartesian_impedance", vectorJson(this->state_store_.config.cartesian_impedance)),
               json::field("desired_wrench_n", vectorJson(this->state_store_.config.desired_wrench_n)),
               json::field("sdk_boundary_units", json::object(std::vector<std::string>{
                   json::field("ui_length_unit", json::quote(runtime_cfg.ui_length_unit)),
                   json::field("sdk_length_unit", json::quote(runtime_cfg.sdk_length_unit)),
                   json::field("boundary_normalized", json::boolLiteral(runtime_cfg.boundary_normalized)),
                   json::field("fc_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix_m))),
                   json::field("tcp_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix_m))),
                   json::field("load_com_m", vectorJson(array3ToVector(runtime_cfg.load_com_m)))
               })),
               json::field("nrt_contract", json::object(std::vector<std::string>{
                   json::field("active_profile", json::quote(this->procedure_executor_.nrt_motion_service.snapshot().active_profile)),
                   json::field("last_command", json::quote(this->procedure_executor_.nrt_motion_service.snapshot().last_command)),
                   json::field("command_count", std::to_string(this->procedure_executor_.nrt_motion_service.snapshot().command_count)),
                   json::field("degraded_without_sdk", json::boolLiteral(this->procedure_executor_.nrt_motion_service.snapshot().degraded_without_sdk))
               })),
               json::field("rt_contract", json::object(std::vector<std::string>{
                   json::field("phase", json::quote(this->procedure_executor_.rt_motion_service.snapshot().phase)),
                   json::field("last_event", json::quote(this->procedure_executor_.rt_motion_service.snapshot().last_event)),
                   json::field("loop_active", json::boolLiteral(this->procedure_executor_.rt_motion_service.snapshot().loop_active)),
                   json::field("move_active", json::boolLiteral(this->procedure_executor_.rt_motion_service.snapshot().move_active)),
                   json::field("pause_hold", json::boolLiteral(this->procedure_executor_.rt_motion_service.snapshot().pause_hold)),
                   json::field("degraded_without_sdk", json::boolLiteral(this->procedure_executor_.rt_motion_service.snapshot().degraded_without_sdk)),
                   json::field("desired_contact_force_n", json::formatDouble(this->procedure_executor_.rt_motion_service.snapshot().desired_contact_force_n)),
                   json::field("current_period_ms", json::formatDouble(this->procedure_executor_.rt_motion_service.snapshot().current_period_ms))
               })),
               json::field("filters", json::object(std::vector<std::string>{
                   json::field("joint_hz", json::formatDouble(runtime_cfg.joint_filter_hz)),
                   json::field("cart_hz", json::formatDouble(runtime_cfg.cart_filter_hz)),
                   json::field("torque_hz", json::formatDouble(runtime_cfg.torque_filter_hz))
               }))
           });
           return this->replyJson(invocation.request_id, true, "get_motion_contract accepted", data);
  }
  if (command == "get_runtime_alignment") {
           const auto* request = invocation.requestAs<GetRuntimeAlignmentRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: get_runtime_alignment");
           }
           (void)request;
           const auto runtime_cfg = this->procedure_executor_.sdk_robot.queryPort().runtimeConfig();
           const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
           const auto data = json::object(std::vector<std::string>{
               json::field("sdk_family", json::quote("ROKAE xCore SDK (C++)")),
               json::field("robot_model", json::quote(identity.robot_model)),
               json::field("sdk_robot_class", json::quote(identity.sdk_robot_class)),
               json::field("axis_count", std::to_string(identity.axis_count)),
               json::field("controller_series", json::quote(identity.controller_series)),
               json::field("controller_version", json::quote(identity.controller_version)),
               json::field("remote_ip", json::quote(runtime_cfg.remote_ip)),
               json::field("local_ip", json::quote(runtime_cfg.local_ip)),
               json::field("preferred_link", json::quote(runtime_cfg.preferred_link)),
               json::field("rt_mode", json::quote(this->state_store_.config.rt_mode)),
               json::field("single_control_source", json::boolLiteral(runtime_cfg.requires_single_control_source)),
               json::field("sdk_available", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().sdkAvailable())),
               json::field("sdk_binding_mode", json::quote(this->procedure_executor_.sdk_robot.queryPort().sdkBindingMode())),
               json::field("control_source_exclusive", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().controlSourceExclusive())),
               json::field("network_healthy", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().networkHealthy())),
               json::field("motion_channel_ready", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().motionChannelReady())),
               json::field("state_channel_ready", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().stateChannelReady())),
               json::field("aux_channel_ready", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().auxChannelReady())),
               json::field("nominal_rt_loop_hz", std::to_string(this->procedure_executor_.sdk_robot.queryPort().nominalRtLoopHz())),
               json::field("active_rt_phase", json::quote(this->procedure_executor_.sdk_robot.queryPort().activeRtPhase())),
               json::field("active_nrt_profile", json::quote(this->procedure_executor_.sdk_robot.queryPort().activeNrtProfile())),
               json::field("command_sequence", std::to_string(this->procedure_executor_.sdk_robot.queryPort().commandSequence())),
               json::field("hardware_lifecycle_state", json::quote(this->procedure_executor_.sdk_robot.queryPort().hardwareLifecycleState())),
               json::field("live_binding_established", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().liveBindingEstablished())),
               json::field("live_takeover_ready", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().liveTakeoverReady())),
               json::field("current_runtime_source", json::quote(this->procedure_executor_.sdk_robot.queryPort().runtimeSource()))
           });
           return this->replyJson(invocation.request_id, true, "get_runtime_alignment accepted", data);
  }
  if (command == "get_xmate_model_summary") {
           const auto* request = invocation.requestAs<GetXmateModelSummaryRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: get_xmate_model_summary");
           }
           (void)request;
           const auto runtime_cfg = this->procedure_executor_.sdk_robot.queryPort().runtimeConfig();
           const auto identity = resolveRobotIdentity(runtime_cfg.robot_model, runtime_cfg.sdk_robot_class, runtime_cfg.axis_count);
           const auto data = json::object(std::vector<std::string>{
               json::field("robot_model", json::quote(identity.robot_model)),
               json::field("sdk_robot_class", json::quote(identity.sdk_robot_class)),
               json::field("xmate_model_available", json::boolLiteral(this->procedure_executor_.sdk_robot.queryPort().xmateModelAvailable())),
               json::field("supports_planner", json::boolLiteral(identity.supports_planner)),
               json::field("supports_xmate_model", json::boolLiteral(identity.supports_xmate_model)),
               json::field("approximate", json::boolLiteral(!(this->procedure_executor_.sdk_robot.queryPort().xmateModelAvailable() && identity.supports_xmate_model))),
               json::field("source", json::quote(this->procedure_executor_.sdk_robot.queryPort().runtimeSource())),
               json::field("dh_parameters", dhArrayJson(identity.official_dh_parameters))
           });
           return this->replyJson(invocation.request_id, true, "get_xmate_model_summary accepted", data);
  }
  if (command == "get_sdk_runtime_config") {
           const auto* request = invocation.requestAs<GetSdkRuntimeConfigRequest>();
           if (request == nullptr) {
             return this->replyJson(invocation.request_id, false, "typed request mismatch: get_sdk_runtime_config");
           }
           (void)request;
           const auto runtime_cfg = this->procedure_executor_.sdk_robot.queryPort().runtimeConfig();
  
           std::vector<std::string> common_fields;
           common_fields.emplace_back(json::field("rt_stale_state_timeout_ms", json::formatDouble(runtime_cfg.rt_stale_state_timeout_ms)));
           common_fields.emplace_back(json::field("rt_phase_transition_debounce_cycles", std::to_string(runtime_cfg.rt_phase_transition_debounce_cycles)));
           common_fields.emplace_back(json::field("rt_max_cart_step_mm", json::formatDouble(runtime_cfg.rt_max_cart_step_mm)));
           common_fields.emplace_back(json::field("rt_max_cart_vel_mm_s", json::formatDouble(runtime_cfg.rt_max_cart_vel_mm_s)));
           common_fields.emplace_back(json::field("rt_max_cart_acc_mm_s2", json::formatDouble(runtime_cfg.rt_max_cart_acc_mm_s2)));
           common_fields.emplace_back(json::field("rt_max_pose_trim_deg", json::formatDouble(runtime_cfg.rt_max_pose_trim_deg)));
           common_fields.emplace_back(json::field("rt_max_force_error_n", json::formatDouble(runtime_cfg.rt_max_force_error_n)));
           common_fields.emplace_back(json::field("rt_integrator_limit_n", json::formatDouble(runtime_cfg.rt_integrator_limit_n)));
           const auto common_obj = json::object(common_fields);
  
           std::vector<std::string> contact_control_fields;
           contact_control_fields.emplace_back(json::field("mode", json::quote(runtime_cfg.contact_control.mode)));
           contact_control_fields.emplace_back(json::field("virtual_mass", json::formatDouble(runtime_cfg.contact_control.virtual_mass)));
           contact_control_fields.emplace_back(json::field("virtual_damping", json::formatDouble(runtime_cfg.contact_control.virtual_damping)));
           contact_control_fields.emplace_back(json::field("virtual_stiffness", json::formatDouble(runtime_cfg.contact_control.virtual_stiffness)));
           contact_control_fields.emplace_back(json::field("force_deadband_n", json::formatDouble(runtime_cfg.contact_control.force_deadband_n)));
           contact_control_fields.emplace_back(json::field("max_normal_step_mm", json::formatDouble(runtime_cfg.contact_control.max_normal_step_mm)));
           contact_control_fields.emplace_back(json::field("max_normal_velocity_mm_s", json::formatDouble(runtime_cfg.contact_control.max_normal_velocity_mm_s)));
           contact_control_fields.emplace_back(json::field("max_normal_acc_mm_s2", json::formatDouble(runtime_cfg.contact_control.max_normal_acc_mm_s2)));
           contact_control_fields.emplace_back(json::field("max_normal_travel_mm", json::formatDouble(runtime_cfg.contact_control.max_normal_travel_mm)));
           contact_control_fields.emplace_back(json::field("anti_windup_limit_n", json::formatDouble(runtime_cfg.contact_control.anti_windup_limit_n)));
           contact_control_fields.emplace_back(json::field("integrator_leak", json::formatDouble(runtime_cfg.contact_control.integrator_leak)));
           const auto contact_control_obj = json::object(contact_control_fields);
  
           std::vector<std::string> force_estimator_fields;
           force_estimator_fields.emplace_back(json::field("preferred_source", json::quote(runtime_cfg.force_estimator.preferred_source)));
           force_estimator_fields.emplace_back(json::field("pressure_weight", json::formatDouble(runtime_cfg.force_estimator.pressure_weight)));
           force_estimator_fields.emplace_back(json::field("wrench_weight", json::formatDouble(runtime_cfg.force_estimator.wrench_weight)));
           force_estimator_fields.emplace_back(json::field("stale_timeout_ms", std::to_string(runtime_cfg.force_estimator.stale_timeout_ms)));
           force_estimator_fields.emplace_back(json::field("timeout_ms", std::to_string(runtime_cfg.force_estimator.timeout_ms)));
           force_estimator_fields.emplace_back(json::field("auto_bias_zero", json::boolLiteral(runtime_cfg.force_estimator.auto_bias_zero)));
           force_estimator_fields.emplace_back(json::field("min_confidence", json::formatDouble(runtime_cfg.force_estimator.min_confidence)));
           const auto force_estimator_obj = json::object(force_estimator_fields);
  
           std::vector<std::string> orientation_trim_fields;
           orientation_trim_fields.emplace_back(json::field("gain", json::formatDouble(runtime_cfg.orientation_trim.gain)));
           orientation_trim_fields.emplace_back(json::field("max_trim_deg", json::formatDouble(runtime_cfg.orientation_trim.max_trim_deg)));
           orientation_trim_fields.emplace_back(json::field("lowpass_hz", json::formatDouble(runtime_cfg.orientation_trim.lowpass_hz)));
           const auto orientation_trim_obj = json::object(orientation_trim_fields);
  
           std::vector<std::string> seek_contact_fields;
           seek_contact_fields.emplace_back(json::field("contact_force_target_n", json::formatDouble(runtime_cfg.contact_force_target_n)));
           seek_contact_fields.emplace_back(json::field("contact_force_tolerance_n", json::formatDouble(runtime_cfg.contact_force_tolerance_n)));
           seek_contact_fields.emplace_back(json::field("contact_establish_cycles", std::to_string(runtime_cfg.contact_establish_cycles)));
           seek_contact_fields.emplace_back(json::field("normal_admittance_gain", json::formatDouble(runtime_cfg.normal_admittance_gain)));
           seek_contact_fields.emplace_back(json::field("normal_damping_gain", json::formatDouble(runtime_cfg.normal_damping_gain)));
           seek_contact_fields.emplace_back(json::field("seek_contact_max_step_mm", json::formatDouble(runtime_cfg.seek_contact_max_step_mm)));
           seek_contact_fields.emplace_back(json::field("seek_contact_max_travel_mm", json::formatDouble(runtime_cfg.seek_contact_max_travel_mm)));
           seek_contact_fields.emplace_back(json::field("normal_velocity_quiet_threshold_mm_s", json::formatDouble(runtime_cfg.normal_velocity_quiet_threshold_mm_s)));
           seek_contact_fields.emplace_back(json::field("contact_control", contact_control_obj));
           seek_contact_fields.emplace_back(json::field("force_estimator", force_estimator_obj));
           const auto seek_contact_obj = json::object(seek_contact_fields);
  
           std::vector<std::string> scan_follow_fields;
           scan_follow_fields.emplace_back(json::field("scan_force_target_n", json::formatDouble(runtime_cfg.scan_force_target_n)));
           scan_follow_fields.emplace_back(json::field("scan_force_tolerance_n", json::formatDouble(runtime_cfg.scan_force_tolerance_n)));
           scan_follow_fields.emplace_back(json::field("scan_normal_pi_kp", json::formatDouble(runtime_cfg.scan_normal_pi_kp)));
           scan_follow_fields.emplace_back(json::field("scan_normal_pi_ki", json::formatDouble(runtime_cfg.scan_normal_pi_ki)));
           scan_follow_fields.emplace_back(json::field("scan_tangent_speed_min_mm_s", json::formatDouble(runtime_cfg.scan_tangent_speed_min_mm_s)));
           scan_follow_fields.emplace_back(json::field("scan_tangent_speed_max_mm_s", json::formatDouble(runtime_cfg.scan_tangent_speed_max_mm_s)));
           scan_follow_fields.emplace_back(json::field("scan_pose_trim_gain", json::formatDouble(runtime_cfg.scan_pose_trim_gain)));
           scan_follow_fields.emplace_back(json::field("scan_follow_enable_lateral_modulation", json::boolLiteral(runtime_cfg.scan_follow_enable_lateral_modulation)));
           scan_follow_fields.emplace_back(json::field("scan_follow_max_travel_mm", json::formatDouble(runtime_cfg.scan_follow_max_travel_mm)));
           scan_follow_fields.emplace_back(json::field("scan_follow_lateral_amplitude_mm", json::formatDouble(runtime_cfg.scan_follow_lateral_amplitude_mm)));
           scan_follow_fields.emplace_back(json::field("scan_follow_frequency_hz", json::formatDouble(runtime_cfg.scan_follow_frequency_hz)));
           scan_follow_fields.emplace_back(json::field("orientation_trim", orientation_trim_obj));
           const auto scan_follow_obj = json::object(scan_follow_fields);
  
           std::vector<std::string> pause_hold_fields;
           pause_hold_fields.emplace_back(json::field("pause_hold_position_guard_mm", json::formatDouble(runtime_cfg.pause_hold_position_guard_mm)));
           pause_hold_fields.emplace_back(json::field("pause_hold_force_guard_n", json::formatDouble(runtime_cfg.pause_hold_force_guard_n)));
           pause_hold_fields.emplace_back(json::field("pause_hold_drift_kp", json::formatDouble(runtime_cfg.pause_hold_drift_kp)));
           pause_hold_fields.emplace_back(json::field("pause_hold_drift_ki", json::formatDouble(runtime_cfg.pause_hold_drift_ki)));
           pause_hold_fields.emplace_back(json::field("pause_hold_integrator_leak", json::formatDouble(runtime_cfg.pause_hold_integrator_leak)));
           const auto pause_hold_obj = json::object(pause_hold_fields);
  
           std::vector<std::string> retract_fields;
           retract_fields.emplace_back(json::field("retract_release_force_n", json::formatDouble(runtime_cfg.retract_release_force_n)));
           retract_fields.emplace_back(json::field("retract_release_cycles", std::to_string(runtime_cfg.retract_release_cycles)));
           retract_fields.emplace_back(json::field("retract_safe_gap_mm", json::formatDouble(runtime_cfg.retract_safe_gap_mm)));
           retract_fields.emplace_back(json::field("retract_max_travel_mm", json::formatDouble(runtime_cfg.retract_max_travel_mm)));
           retract_fields.emplace_back(json::field("retract_jerk_limit_mm_s3", json::formatDouble(runtime_cfg.retract_jerk_limit_mm_s3)));
           retract_fields.emplace_back(json::field("retract_timeout_ms", json::formatDouble(runtime_cfg.retract_timeout_ms)));
           retract_fields.emplace_back(json::field("retract_travel_mm", json::formatDouble(runtime_cfg.retract_travel_mm)));
           const auto retract_obj = json::object(retract_fields);
  
           std::vector<std::string> rt_phase_fields;
           rt_phase_fields.emplace_back(json::field("common", common_obj));
           rt_phase_fields.emplace_back(json::field("seek_contact", seek_contact_obj));
           rt_phase_fields.emplace_back(json::field("scan_follow", scan_follow_obj));
           rt_phase_fields.emplace_back(json::field("pause_hold", pause_hold_obj));
           rt_phase_fields.emplace_back(json::field("controlled_retract", retract_obj));
           const auto rt_phase_contract = json::object(rt_phase_fields);
  
           std::vector<std::string> data_fields;
           data_fields.emplace_back(json::field("robot_model", json::quote(runtime_cfg.robot_model)));
           data_fields.emplace_back(json::field("sdk_robot_class", json::quote(runtime_cfg.sdk_robot_class)));
           data_fields.emplace_back(json::field("remote_ip", json::quote(runtime_cfg.remote_ip)));
           data_fields.emplace_back(json::field("local_ip", json::quote(runtime_cfg.local_ip)));
           data_fields.emplace_back(json::field("axis_count", std::to_string(runtime_cfg.axis_count)));
           data_fields.emplace_back(json::field("rt_network_tolerance_percent", std::to_string(runtime_cfg.rt_network_tolerance_percent)));
           data_fields.emplace_back(json::field("joint_filter_hz", json::formatDouble(runtime_cfg.joint_filter_hz)));
           data_fields.emplace_back(json::field("cart_filter_hz", json::formatDouble(runtime_cfg.cart_filter_hz)));
           data_fields.emplace_back(json::field("torque_filter_hz", json::formatDouble(runtime_cfg.torque_filter_hz)));
           data_fields.emplace_back(json::field("fc_frame_type", json::quote(this->state_store_.config.fc_frame_type)));
           data_fields.emplace_back(json::field("cartesian_impedance", vectorJson(array6ToVector(runtime_cfg.cartesian_impedance))));
           data_fields.emplace_back(json::field("desired_wrench_n", vectorJson(array6ToVector(runtime_cfg.desired_wrench_n))));
           data_fields.emplace_back(json::field("fc_frame_matrix", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix))));
           data_fields.emplace_back(json::field("tcp_frame_matrix", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix))));
           data_fields.emplace_back(json::field("load_com_mm", vectorJson(array3ToVector(runtime_cfg.load_com_mm))));
           data_fields.emplace_back(json::field("fc_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.fc_frame_matrix_m))));
           data_fields.emplace_back(json::field("tcp_frame_matrix_m", vectorJson(array16ToVector(runtime_cfg.tcp_frame_matrix_m))));
           data_fields.emplace_back(json::field("load_com_m", vectorJson(array3ToVector(runtime_cfg.load_com_m))));
           data_fields.emplace_back(json::field("rt_stale_state_timeout_ms", json::formatDouble(runtime_cfg.rt_stale_state_timeout_ms)));
           data_fields.emplace_back(json::field("rt_phase_transition_debounce_cycles", std::to_string(runtime_cfg.rt_phase_transition_debounce_cycles)));
           data_fields.emplace_back(json::field("rt_max_cart_step_mm", json::formatDouble(runtime_cfg.rt_max_cart_step_mm)));
           data_fields.emplace_back(json::field("contact_force_target_n", json::formatDouble(runtime_cfg.contact_force_target_n)));
           data_fields.emplace_back(json::field("scan_force_target_n", json::formatDouble(runtime_cfg.scan_force_target_n)));
           data_fields.emplace_back(json::field("retract_timeout_ms", json::formatDouble(runtime_cfg.retract_timeout_ms)));
           data_fields.emplace_back(json::field("ui_length_unit", json::quote(runtime_cfg.ui_length_unit)));
           data_fields.emplace_back(json::field("sdk_length_unit", json::quote(runtime_cfg.sdk_length_unit)));
           data_fields.emplace_back(json::field("boundary_normalized", json::boolLiteral(runtime_cfg.boundary_normalized)));
           data_fields.emplace_back(json::field("runtime_config_contract_digest", json::quote(this->state_store_.config.runtime_config_contract_digest)));
           data_fields.emplace_back(json::field("runtime_config_schema_version", json::quote(this->state_store_.config.runtime_config_schema_version)));
           data_fields.emplace_back(json::field("load_inertia", vectorJson(array6ToVector(runtime_cfg.load_inertia))));
           data_fields.emplace_back(json::field("contact_control", contact_control_obj));
           data_fields.emplace_back(json::field("force_estimator", force_estimator_obj));
           data_fields.emplace_back(json::field("orientation_trim", orientation_trim_obj));
           data_fields.emplace_back(json::field("rt_phase_contract", rt_phase_contract));
           const auto data = json::object(data_fields);
           return this->replyJson(invocation.request_id, true, "get_sdk_runtime_config accepted", data);
  }
  return {};
}

}  // namespace robot_core
