#include "robot_core/core_runtime.h"

#include "core_runtime_contract_json_helpers.h"
#include "robot_core/core_runtime_contract_publisher.h"
#include "robot_core/robot_family_descriptor.h"
#include "robot_core/robot_identity_contract.h"
#include "robot_core/safety_decision.h"

namespace robot_core {

using namespace contract_json;

std::string CoreRuntime::releaseContractJsonInternal() const {
  using namespace json;
  const auto safety = evaluateSafetyLocked();
  const bool freeze_consistent = sessionFreezeConsistentLocked();
  const bool compile_ready = evidence_projector_.last_final_verdict.accepted && freeze_consistent;
  std::vector<std::string> blockers; std::vector<std::string> warnings; appendMainlineContractIssuesLocked(&blockers, &warnings);
  for (const auto& item : evidence_projector_.last_final_verdict.blockers) blockers.push_back(item);
  for (const auto& item : evidence_projector_.last_final_verdict.warnings) warnings.push_back(item);
  const bool release_allowed = compile_ready && safety.active_interlocks.empty();
  return object({
      field("summary_state", quote(release_allowed ? std::string("ready") : std::string("blocked"))),
      field("session_locked", boolLiteral(!state_store_.session_id.empty())),
      field("session_freeze_consistent", boolLiteral(freeze_consistent)),
      field("locked_scan_plan_hash", quote(state_store_.locked_scan_plan_hash)),
      field("active_plan_hash", quote(state_store_.plan_hash)),
      field("runtime_source", quote(procedure_executor_.sdk_robot.runtimeSource())),
      field("compile_ready", boolLiteral(compile_ready)),
      field("ready_for_approach", boolLiteral(compile_ready && state_store_.execution_state == RobotCoreState::PathValidated)),
      field("ready_for_scan", boolLiteral(compile_ready && state_store_.execution_state == RobotCoreState::ContactStable)),
      field("release_recommendation", quote(release_allowed ? std::string("allow") : std::string("block"))),
      field("active_interlocks", stringArray(safety.active_interlocks)),
      field("final_verdict", object({field("accepted", boolLiteral(evidence_projector_.last_final_verdict.accepted)), field("policy_state", quote(evidence_projector_.last_final_verdict.policy_state)), field("reason", quote(evidence_projector_.last_final_verdict.reason)), field("evidence_id", quote(evidence_projector_.last_final_verdict.evidence_id))})),
      field("blockers", objectArray([&](){ std::vector<std::string> items; for (const auto& b: blockers) items.push_back(summaryEntry("release", b)); return items; }())),
      field("warnings", objectArray([&](){ std::vector<std::string> items; for (const auto& w: warnings) items.push_back(summaryEntry("release", w)); return items; }())),
      field("active_injections", stringArray([&](){ std::vector<std::string> items(authority_kernel_.injected_faults.begin(), authority_kernel_.injected_faults.end()); return items; }()))
  });
}

std::string CoreRuntime::deploymentContractJsonInternal() const {
  using namespace json;
  const auto identity = resolveRobotIdentity(state_store_.config.robot_model, state_store_.config.sdk_robot_class, state_store_.config.axis_count);
  return object({
      field("runtime_source", quote(procedure_executor_.sdk_robot.runtimeSource())),
      field("vendored_sdk_required", boolLiteral(true)),
      field("vendored_sdk_detected", boolLiteral(procedure_executor_.sdk_robot.sdkAvailable())),
      field("live_binding_established", boolLiteral(procedure_executor_.sdk_robot.liveBindingEstablished())),
      field("xmate_model_detected", boolLiteral(procedure_executor_.sdk_robot.xmateModelAvailable())),
      field("preferred_link", quote(identity.preferred_link)),
      field("single_control_source_required", boolLiteral(identity.requires_single_control_source)),
      field("required_host_dependencies", stringArray({"cmake", "g++/clang++", "openssl headers", "eigen headers"})),
      field("required_runtime_materials", stringArray({"configs/tls/runtime/*", "vendored librokae include/lib/external"})),
      field("bringup_sequence", stringArray({"doctor_runtime.py", "generate_dev_tls_cert.sh", "start_real.sh", "run.py --backend core"})),
      field("systemd_units", stringArray({"spine-cpp-core.service", "spine-python-api.service", "spine-ultrasound.target"})),
      field("summary_label", quote("cpp deployment contract"))
  });
}

}  // namespace robot_core
