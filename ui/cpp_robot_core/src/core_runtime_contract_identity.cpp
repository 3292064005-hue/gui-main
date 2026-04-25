#include "robot_core/core_runtime.h"

#include "core_runtime_contract_json_helpers.h"
#include "robot_core/core_runtime_contract_publisher.h"
#include "robot_core/robot_family_descriptor.h"
#include "robot_core/robot_identity_contract.h"
#include "robot_core/safety_decision.h"

namespace robot_core {

using namespace contract_json;

std::string CoreRuntime::robotFamilyContractJsonLocked() const {
  using namespace json;
  const auto family = resolveRobotFamilyDescriptor(state_store_.config.robot_model, state_store_.config.sdk_robot_class, state_store_.config.axis_count);
  return object({
      field("summary_state", quote("ready")),
      field("summary_label", quote(family.family_label)),
      field("detail", quote("Robot family capabilities are derived from the frozen family descriptor matrix.")),
      field("family_key", quote(family.family_key)),
      field("family_label", quote(family.family_label)),
      field("robot_model", quote(family.robot_model)),
      field("sdk_robot_class", quote(family.sdk_robot_class)),
      field("axis_count", std::to_string(family.axis_count)),
      field("clinical_rt_mode", quote(family.clinical_rt_mode)),
      field("supports_xmate_model", boolLiteral(family.supports_xmate_model)),
      field("supports_planner", boolLiteral(family.supports_planner)),
      field("supports_drag", boolLiteral(family.supports_drag)),
      field("supports_path_replay", boolLiteral(family.supports_path_replay)),
      field("requires_single_control_source", boolLiteral(family.requires_single_control_source)),
      field("preferred_link", quote(family.preferred_link)),
      field("supported_nrt_profiles", stringArray(family.supported_nrt_profiles)),
      field("supported_rt_phases", stringArray(family.supported_rt_phases))
  });
}

std::string CoreRuntime::vendorBoundaryContractJsonLocked() const {
  using namespace json;
  const bool sdk_detected = procedure_executor_.sdk_robot.sdkAvailable();
  const bool live_binding = procedure_executor_.sdk_robot.liveBindingEstablished();
  const std::string summary_state = live_binding ? std::string("ready") : (sdk_detected ? std::string("warning") : std::string("blocked"));
  return object({
      field("summary_state", quote(summary_state)),
      field("summary_label", quote(live_binding ? std::string("vendor boundary live") : std::string("vendor boundary contract"))),
      field("detail", quote(live_binding ? std::string("Vendor boundary owns a live SDK binding with exclusive-control and fixed-period RT semantics.") : std::string("Vendor boundary contract is present, but real live binding/lifecycle readiness/exclusive-control evidence is not yet established."))),
      field("binding_mode", quote(procedure_executor_.sdk_robot.sdkBindingMode())),
      field("runtime_source", quote(procedure_executor_.sdk_robot.runtimeSource())),
      field("single_control_source_required", boolLiteral(state_store_.config.requires_single_control_source)),
      field("live_evidence_bundle_required", boolLiteral(true)),
      field("control_source_exclusive", boolLiteral(procedure_executor_.sdk_robot.controlSourceExclusive())),
      field("fixed_period_enforced", boolLiteral(true)),
      field("network_healthy", boolLiteral(procedure_executor_.sdk_robot.networkHealthy())),
      field("active_nrt_profile", quote(procedure_executor_.sdk_robot.activeNrtProfile())),
      field("active_rt_phase", quote(procedure_executor_.sdk_robot.activeRtPhase())),
      field("nominal_rt_loop_hz", std::to_string(procedure_executor_.sdk_robot.nominalRtLoopHz()))
  });
}

std::string CoreRuntime::capabilityContractJsonLocked() const {
  const auto& identity = resolveRobotIdentity(state_store_.config.robot_model, state_store_.config.sdk_robot_class, state_store_.config.axis_count);
  using namespace json;
  const bool live_binding = procedure_executor_.sdk_robot.liveBindingEstablished();
  auto module_entry = [&](const std::string& module, bool enabled, const std::string& status, const std::string& purpose, bool vendor_supported = true, bool runtime_implemented = true, bool live_required = false) {
    return object({field("module", quote(module)), field("enabled", boolLiteral(enabled)), field("status", quote(status)), field("purpose", quote(purpose)), field("vendor_supported", boolLiteral(vendor_supported)), field("runtime_implemented", boolLiteral(runtime_implemented)), field("live_binding_established", boolLiteral(live_required ? live_binding : false))});
  };
  std::vector<std::string> modules;
  modules.push_back(module_entry("rokae::Robot", true, "ready", "连接、上电、模式切换、姿态/关节/日志/工具工件查询", true, true, true));
  modules.push_back(module_entry("rokae::RtMotionControl", state_store_.config.rt_mode == identity.clinical_mainline_mode && state_store_.config.rt_mode != "directTorque", state_store_.config.rt_mode == identity.clinical_mainline_mode && state_store_.config.rt_mode != "directTorque" ? "ready" : "policy_blocked", "1 kHz 实时阻抗/位置控制主线", true, true, true));
  modules.push_back(module_entry("rokae::Planner", identity.supports_planner, identity.supports_planner ? "ready" : "unsupported", "S 曲线/点位跟随的上位机路径规划", true, true, false));
  modules.push_back(module_entry("rokae::xMateModel", identity.supports_xmate_model, identity.supports_xmate_model ? (procedure_executor_.sdk_robot.xmateModelAvailable() ? "ready" : "degraded") : "unsupported", "正逆解、雅可比、动力学前向计算", true, true, true));
  modules.push_back(module_entry("通信 I/O", true, "ready", "DI/DO/AI/AO、寄存器、xPanel 供电配置", true, true, true));
  modules.push_back(module_entry("RL 工程", true, "ready", "projectsInfo / loadProject / runProject / pauseProject", true, true, true));
  modules.push_back(module_entry("协作功能", identity.supports_drag || identity.supports_path_replay, identity.supports_drag || identity.supports_path_replay ? "ready" : "unsupported", "拖动示教、路径录制/回放、奇异规避", true, true, true));
  std::vector<std::string> blockers; std::vector<std::string> warnings; appendMainlineContractIssuesLocked(&blockers, &warnings);
  return object({
      field("robot_model", quote(identity.robot_model)),
      field("sdk_robot_class", quote(identity.sdk_robot_class)),
      field("controller_version", quote(identity.controller_version)),
      field("preferred_link", quote(state_store_.config.preferred_link)),
      field("rt_loop_hz", std::to_string(1000)),
      field("scan_rt_mode", quote(state_store_.config.rt_mode)),
      field("runtime_source", quote(procedure_executor_.sdk_robot.runtimeSource())),
      field("live_binding_established", boolLiteral(live_binding)),
      field("modules", objectArray(modules)),
      field("blockers", objectArray([&](){ std::vector<std::string> items; for (const auto& b: blockers) items.push_back(summaryEntry("capability", b)); return items; }())),
      field("warnings", objectArray([&](){ std::vector<std::string> items; for (const auto& w: warnings) items.push_back(summaryEntry("capability", w)); return items; }())),
      field("clinical_policy", object({field("mainline_scan_mode", quote(identity.clinical_mainline_mode)), field("direct_torque_allowed", boolLiteral(false)), field("single_control_source_required", boolLiteral(identity.requires_single_control_source))}))
  });
}

std::string CoreRuntime::modelAuthorityContractJsonLocked() const {
  using namespace json;
  const auto snapshot = services_.model_authority.snapshot(state_store_.config, procedure_executor_.sdk_robot);
  std::vector<std::string> warnings;
  warnings.reserve(snapshot.warnings.size());
  for (const auto& item : snapshot.warnings) {
    warnings.push_back(summaryEntry("model_authority", item));
  }
  return object({
      field("authoritative_kernel", quote(snapshot.authority_source)),
      field("runtime_source", quote(snapshot.runtime_source)),
      field("family_key", quote(snapshot.family_key)),
      field("family_label", quote(snapshot.family_label)),
      field("robot_model", quote(snapshot.robot_model)),
      field("sdk_robot_class", quote(snapshot.sdk_robot_class)),
      field("planner_supported", boolLiteral(snapshot.planner_supported)),
      field("xmate_model_supported", boolLiteral(snapshot.xmate_model_supported)),
      field("authoritative_precheck", boolLiteral(snapshot.authoritative_precheck)),
      field("authoritative_runtime", boolLiteral(snapshot.authoritative_runtime)),
      field("approximate_advisory_allowed", boolLiteral(snapshot.approximate_advisory_allowed)),
      field("planner_primitives", stringArray(snapshot.planner_primitives)),
      field("model_methods", stringArray(snapshot.model_methods)),
      field("warnings", objectArray(warnings))
  });
}

}  // namespace robot_core
