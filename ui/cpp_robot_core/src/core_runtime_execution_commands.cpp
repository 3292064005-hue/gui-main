#include "robot_core/core_runtime.h"

#include <algorithm>
#include <filesystem>
#include <functional>
#include <unordered_map>

#include "json_utils.h"
#include "core_runtime_command_helpers.h"
#include "robot_core/robot_identity_contract.h"

namespace robot_core {

std::string CoreRuntime::handleExecutionCommand(const RuntimeCommandInvocation& invocation) {
  std::lock_guard<std::mutex> state_lock(state_store_.mutex);
  const auto& command = invocation.command;
  const auto allow_command = [this](const std::string& action, std::string* reason) -> bool {
    return procedure_executor_.state_machine_guard.allow(action, state_store_.execution_state, reason);
  };
  const auto validate_rt_phase = [this](const std::string& fallback_message, std::string* out_reason) -> bool {
    std::string phase_reason;
    const bool ok = services_.model_authority.validateRtPhaseTargetDelta(state_store_.config, procedure_executor_.sdk_robot, &phase_reason) &&
                    services_.model_authority.validateRtPhaseWorkspace(state_store_.config, procedure_executor_.sdk_robot, &phase_reason) &&
                    services_.model_authority.validateRtPhaseSingularityMargin(state_store_.config, procedure_executor_.sdk_robot, &phase_reason);
    if (!ok && out_reason != nullptr) {
      *out_reason = phase_reason.empty() ? fallback_message : phase_reason;
    }
    return ok;
  };
  using ExecutionHandler = std::function<std::string(CoreRuntime*, const RuntimeCommandInvocation&)>;
  const auto start_procedure_action = [allow_command, validate_rt_phase](CoreRuntime* self, const std::string& command_name, const std::string& procedure_name, const RuntimeCommandInvocation& inv) {
  std::string reason;
  if (!allow_command(command_name, &reason)) {
    return self->replyJson(inv.request_id, false, reason);
  }
  if (!self->sessionFreezeConsistentLocked()) {
    return self->replyJson(inv.request_id, false, "start_procedure blocked by runtime freeze gate");
  }
  if (!validate_rt_phase(command_name + std::string(" precheck failed"), &reason)) {
    return self->replyJson(inv.request_id, false, reason);
  }
  if (procedure_name != "scan") {
    return self->replyJson(inv.request_id, false, "unsupported procedure: " + procedure_name);
  }
  if (!self->configureActiveSegmentLocked(&reason)) {
    return self->replyJson(inv.request_id, false, reason.empty() ? "active segment configuration failed" : reason);
  }
  self->procedure_executor_.scan_procedure_active = true;
  if (self->state_store_.execution_state == RobotCoreState::PausedHold || self->state_store_.execution_state == RobotCoreState::ContactStable) {
    if (!self->startPlanDrivenScanLocked(&reason)) {
      return self->replyJson(inv.request_id, false, reason.empty() ? "resume start_procedure failed" : reason);
    }
    return self->replyJson(inv.request_id, true, "start_procedure accepted");
  }
  if (self->state_store_.execution_state != RobotCoreState::PathValidated) {
    return self->replyJson(inv.request_id, false, "start_procedure requires PATH_VALIDATED, CONTACT_STABLE, or PAUSED_HOLD");
  }
  if (!self->procedure_executor_.nrt_motion_service.approachPrescan(&reason)) {
    self->state_store_.execution_state = RobotCoreState::Fault;
    return self->replyJson(inv.request_id, false, reason.empty() ? "approach_prescan failed" : reason);
  }
  self->state_store_.execution_state = RobotCoreState::Approaching;
  self->state_store_.state_reason = "approach_prescan";
  self->state_store_.contact_state.recommended_action = "SEEK_CONTACT";
  if (!self->procedure_executor_.rt_motion_service.seekContact()) {
    self->state_store_.execution_state = RobotCoreState::Fault;
    return self->replyJson(inv.request_id, false, "seek_contact failed");
  }
  self->state_store_.execution_state = RobotCoreState::ContactSeeking;
  self->state_store_.state_reason = "waiting_for_contact_stability";
  self->state_store_.contact_state.mode = "SEEKING_CONTACT";
  self->state_store_.contact_state.recommended_action = "WAIT_CONTACT_STABLE";
  return self->replyJson(inv.request_id, true, "start_procedure accepted");
};
  const std::unordered_map<std::string, ExecutionHandler> handlers = {
      {"approach_prescan", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ApproachPrescanRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: approach_prescan");
         }
         (void)request;
         if (self->state_store_.execution_state != RobotCoreState::PathValidated) {
           return self->replyJson(inv.request_id, false, "scan plan not ready");
         }
         if (!self->sessionFreezeConsistentLocked()) {
           return self->replyJson(inv.request_id, false, "approach_prescan blocked by runtime freeze gate");
         }
         std::string reason;
         if (!self->procedure_executor_.nrt_motion_service.approachPrescan(&reason)) {
           self->state_store_.execution_state = RobotCoreState::Fault;
           return self->replyJson(inv.request_id, false, reason.empty() ? "approach_prescan failed" : reason);
         }
         self->state_store_.execution_state = RobotCoreState::Approaching;
         self->state_store_.state_reason = "approach_prescan";
         self->state_store_.contact_state.recommended_action = "SEEK_CONTACT";
         return self->replyJson(inv.request_id, true, "approach_prescan accepted");
       }},
      {"seek_contact", [allow_command, validate_rt_phase](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<SeekContactRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: seek_contact");
         }
         (void)request;
         std::string reason;
         if (!allow_command("seek_contact", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->sessionFreezeConsistentLocked()) {
           return self->replyJson(inv.request_id, false, "seek_contact blocked by runtime freeze gate");
         }
         if (!validate_rt_phase("seek_contact precheck failed", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->procedure_executor_.rt_motion_service.seekContact()) {
           return self->replyJson(inv.request_id, false, "seek_contact failed");
         }
         self->state_store_.execution_state = RobotCoreState::ContactSeeking;
         self->state_store_.state_reason = "waiting_for_contact_stability";
         self->state_store_.contact_state.mode = "SEEKING_CONTACT";
         self->state_store_.contact_state.recommended_action = "WAIT_CONTACT_STABLE";
         return self->replyJson(inv.request_id, true, "seek_contact accepted");
       }},
      {"start_procedure", [start_procedure_action](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<StartProcedureRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: start_procedure");
         }
         return start_procedure_action(self, "start_procedure", request->procedure, inv);
       }},
      {"pause_scan", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<PauseScanRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: pause_scan");
         }
         (void)request;
         if (self->state_store_.execution_state != RobotCoreState::Scanning) {
           return self->replyJson(inv.request_id, false, "scan not active");
         }
         self->procedure_executor_.rt_motion_service.pauseAndHold();
         self->procedure_executor_.recovery_manager.pauseAndHold();
         self->procedure_executor_.sdk_robot.collaborationPort().setRlStatus(self->state_store_.config.rl_project_name, self->state_store_.config.rl_task_name, false);
         self->state_store_.execution_state = RobotCoreState::PausedHold;
         self->state_store_.state_reason = "pause_hold";
         self->state_store_.contact_state.mode = "HOLDING_CONTACT";
         self->state_store_.contact_state.recommended_action = "RESUME_OR_RETREAT";
         return self->replyJson(inv.request_id, true, "pause_scan accepted");
       }},
      {"resume_scan", [validate_rt_phase](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ResumeScanRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: resume_scan");
         }
         (void)request;
         if (!self->sessionFreezeConsistentLocked()) {
           return self->replyJson(inv.request_id, false, "resume_scan blocked by runtime freeze gate");
         }
         if (self->state_store_.execution_state != RobotCoreState::PausedHold) {
           return self->replyJson(inv.request_id, false, "scan not paused");
         }
         std::string reason;
         if (!validate_rt_phase("resume_scan precheck failed", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->startPlanDrivenScanLocked(&reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "resume_scan failed" : reason);
         }
         self->procedure_executor_.recovery_manager.cancelRetry();
         return self->replyJson(inv.request_id, true, "resume_scan accepted");
       }},
      {"stop_scan", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<StopScanRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: stop_scan");
         }
         (void)request;
         std::string reason;
         if (!allow_command("stop_scan", &reason)) return self->replyJson(inv.request_id, false, reason);
         const bool completes_scan = self->state_store_.execution_state == RobotCoreState::Scanning || self->state_store_.execution_state == RobotCoreState::PausedHold;
         const auto rt_retract = self->procedure_executor_.rt_motion_service.controlledRetract();
         if (!rt_retract.canProceedToNrtRetreat()) {
           self->state_store_.execution_state = RobotCoreState::Fault;
           self->procedure_executor_.sdk_robot.collaborationPort().setRlStatus(self->state_store_.config.rl_project_name, self->state_store_.config.rl_task_name, false);
           self->state_store_.fault_code = "STOP_SCAN_RT_RETRACT_FAILED";
           self->queueAlarmLocked("RECOVERABLE_FAULT", "recovery", "结束本轮扫查失败：RT受控回撤未闭环", "stop_scan", rt_retract.reason, "controlled_retract_incomplete");
           return self->replyJson(inv.request_id, false, std::string("stop_scan blocked before post_scan_home: ") + rt_retract.reason);
         }
         if (!self->procedure_executor_.nrt_motion_service.postScanHome(&reason)) {
           self->state_store_.execution_state = RobotCoreState::Fault;
           self->procedure_executor_.sdk_robot.collaborationPort().setRlStatus(self->state_store_.config.rl_project_name, self->state_store_.config.rl_task_name, false);
           self->state_store_.fault_code = "STOP_SCAN_POST_HOME_FAILED";
           self->queueAlarmLocked("RECOVERABLE_FAULT", "recovery", "结束本轮扫查失败：post_scan_home 未闭环", "stop_scan", reason, "post_scan_home_failed");
           return self->replyJson(inv.request_id, false, reason.empty() ? "stop_scan failed" : reason);
         }
         self->procedure_executor_.recovery_manager.controlledRetract();
         self->procedure_executor_.sdk_robot.collaborationPort().setRlStatus(self->state_store_.config.rl_project_name, self->state_store_.config.rl_task_name, false);
         self->state_store_.execution_state = RobotCoreState::Retreating;
         self->state_store_.state_reason = completes_scan ? "stop_scan" : "stop_scan_before_scan_complete";
         self->state_store_.retreat_ticks_remaining = 10;
         self->state_store_.retreat_completion_state = completes_scan ? RobotCoreState::ScanComplete : RobotCoreState::PathValidated;
         self->state_store_.contact_state.mode = "NO_CONTACT";
         self->state_store_.contact_state.recommended_action = completes_scan ? "WAIT_SCAN_COMPLETE" : "WAIT_RETREAT_COMPLETE";
         self->procedure_executor_.scan_procedure_active = false;
         return self->replyJson(inv.request_id, true, completes_scan ? "stop_scan accepted" : "stop_scan accepted before scan completion");
       }},
      {"safe_retreat", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<SafeRetreatRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: safe_retreat");
         }
         (void)request;
         std::string reason;
         if (!allow_command("safe_retreat", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto rt_retract = self->procedure_executor_.rt_motion_service.controlledRetract();
         if (!rt_retract.canProceedToNrtRetreat()) {
           self->state_store_.execution_state = RobotCoreState::Fault;
           self->procedure_executor_.sdk_robot.collaborationPort().setRlStatus(self->state_store_.config.rl_project_name, self->state_store_.config.rl_task_name, false);
           self->state_store_.fault_code = "SAFE_RETREAT_RT_RETRACT_FAILED";
           self->queueAlarmLocked("RECOVERABLE_FAULT", "recovery", "安全退让失败：RT受控回撤未闭环", "safe_retreat", rt_retract.reason, "controlled_retract_incomplete");
           return self->replyJson(inv.request_id, false, std::string("safe_retreat blocked before NRT retreat: ") + rt_retract.reason);
         }
         if (!self->procedure_executor_.nrt_motion_service.safeRetreat(&reason)) {
           self->state_store_.execution_state = RobotCoreState::Fault;
           self->procedure_executor_.sdk_robot.collaborationPort().setRlStatus(self->state_store_.config.rl_project_name, self->state_store_.config.rl_task_name, false);
           self->state_store_.fault_code = "SAFE_RETREAT_FAILED";
           self->queueAlarmLocked("RECOVERABLE_FAULT", "recovery", "安全退让失败", "safe_retreat", reason, "controlled_retract_failed");
           return self->replyJson(inv.request_id, false, reason.empty() ? "safe_retreat failed" : reason);
         }
         self->procedure_executor_.recovery_manager.controlledRetract();
         self->procedure_executor_.sdk_robot.collaborationPort().setRlStatus(self->state_store_.config.rl_project_name, self->state_store_.config.rl_task_name, false);
         self->state_store_.execution_state = RobotCoreState::Retreating;
         self->state_store_.state_reason = "safe_retreat";
         self->state_store_.retreat_ticks_remaining = 30;
         self->state_store_.retreat_completion_state = self->state_store_.plan_loaded ? RobotCoreState::PathValidated : RobotCoreState::AutoReady;
         self->state_store_.contact_state.mode = "NO_CONTACT";
         self->state_store_.contact_state.recommended_action = "WAIT_RETREAT_COMPLETE";
         return self->replyJson(inv.request_id, true, "safe_retreat accepted");
       }},
      {"go_home", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<GoHomeRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: go_home");
         }
         (void)request;
         std::string reason;
         if (!allow_command("go_home", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const bool ok = self->procedure_executor_.nrt_motion_service.goHome(&reason);
         return self->replyJson(inv.request_id, ok, ok ? "go_home accepted" : (reason.empty() ? "go_home failed" : reason));
       }},
      {"run_rl_project", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<RunRlProjectRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: run_rl_project");
         }
         std::string reason;
         if (!allow_command("run_rl_project", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto project = request->project.value_or(self->state_store_.config.rl_project_name);
         const auto task = request->task.value_or(self->state_store_.config.rl_task_name);
         if (!self->procedure_executor_.sdk_robot.collaborationPort().runRlProject(project, task, &reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "run_rl_project failed" : reason);
         }
         self->procedure_executor_.sdk_robot.collaborationPort().setRlStatus(project, task, true);
         return self->replyJson(inv.request_id, true, "run_rl_project accepted");
       }},
      {"pause_rl_project", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<PauseRlProjectRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: pause_rl_project");
         }
         (void)request;
         std::string reason;
         if (!allow_command("pause_rl_project", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->procedure_executor_.sdk_robot.collaborationPort().pauseRlProject(&reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "pause_rl_project failed" : reason);
         }
         self->procedure_executor_.sdk_robot.collaborationPort().setRlStatus(self->state_store_.config.rl_project_name, self->state_store_.config.rl_task_name, false);
         return self->replyJson(inv.request_id, true, "pause_rl_project accepted");
       }},
      {"enable_drag", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<EnableDragRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: enable_drag");
         }
         std::string reason;
         if (!allow_command("enable_drag", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto space = request->space.value_or("cartesian");
         const auto type = request->type.value_or("admittance");
         if (!self->procedure_executor_.sdk_robot.collaborationPort().enableDrag(space, type, &reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "enable_drag failed" : reason);
         }
         self->procedure_executor_.sdk_robot.collaborationPort().setDragState(true, space, type);
         return self->replyJson(inv.request_id, true, "enable_drag accepted");
       }},
      {"disable_drag", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<DisableDragRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: disable_drag");
         }
         (void)request;
         std::string reason;
         if (!allow_command("disable_drag", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->procedure_executor_.sdk_robot.collaborationPort().disableDrag(&reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "disable_drag failed" : reason);
         }
         self->procedure_executor_.sdk_robot.collaborationPort().setDragState(false, "cartesian", "admittance");
         return self->replyJson(inv.request_id, true, "disable_drag accepted");
       }},
      {"replay_path", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ReplayPathRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: replay_path");
         }
         std::string reason;
         if (!allow_command("replay_path", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto name = request->name.value_or("spine_demo_path");
         const auto rate = request->rate.value_or(0.5);
         if (!self->procedure_executor_.sdk_robot.collaborationPort().replayPath(name, rate, &reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "replay_path failed" : reason);
         }
         return self->replyJson(inv.request_id, true, "replay_path accepted");
       }},
      {"start_record_path", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<StartRecordPathRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: start_record_path");
         }
         std::string reason;
         if (!allow_command("start_record_path", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto duration_s = request->duration_s.value_or(60);
         if (!self->procedure_executor_.sdk_robot.collaborationPort().startRecordPath(duration_s, &reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "start_record_path failed" : reason);
         }
         return self->replyJson(inv.request_id, true, "start_record_path accepted");
       }},
      {"stop_record_path", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<StopRecordPathRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: stop_record_path");
         }
         (void)request;
         std::string reason;
         if (!allow_command("stop_record_path", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->procedure_executor_.sdk_robot.collaborationPort().stopRecordPath(&reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "stop_record_path failed" : reason);
         }
         return self->replyJson(inv.request_id, true, "stop_record_path accepted");
       }},
      {"cancel_record_path", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<CancelRecordPathRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: cancel_record_path");
         }
         (void)request;
         std::string reason;
         if (!allow_command("cancel_record_path", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         if (!self->procedure_executor_.sdk_robot.collaborationPort().cancelRecordPath(&reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "cancel_record_path failed" : reason);
         }
         return self->replyJson(inv.request_id, true, "cancel_record_path accepted");
       }},
      {"save_record_path", [allow_command](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<SaveRecordPathRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: save_record_path");
         }
         std::string reason;
         if (!allow_command("save_record_path", &reason)) {
           return self->replyJson(inv.request_id, false, reason);
         }
         const auto name = request->name.value_or("spine_demo_path");
         const auto save_as = request->save_as.value_or(name);
         if (!self->procedure_executor_.sdk_robot.collaborationPort().saveRecordPath(name, save_as, &reason)) {
           return self->replyJson(inv.request_id, false, reason.empty() ? "save_record_path failed" : reason);
         }
         return self->replyJson(inv.request_id, true, "save_record_path accepted");
       }},
      {"clear_fault", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<ClearFaultRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: clear_fault");
         }
         (void)request;
         if (self->state_store_.execution_state != RobotCoreState::Fault) {
           return self->replyJson(inv.request_id, false, "no fault to clear");
         }
         self->state_store_.fault_code.clear();
         self->state_store_.execution_state = self->state_store_.plan_loaded ? RobotCoreState::PathValidated : RobotCoreState::AutoReady;
         return self->replyJson(inv.request_id, true, "clear_fault accepted");
       }},
      {"emergency_stop", [](CoreRuntime* self, const RuntimeCommandInvocation& inv) {
         const auto* request = inv.requestAs<EmergencyStopRequest>();
         if (request == nullptr) {
           return self->replyJson(inv.request_id, false, "typed request mismatch: emergency_stop");
         }
         (void)request;
         self->procedure_executor_.rt_motion_service.stop();
         self->procedure_executor_.recovery_manager.cancelRetry();
         self->procedure_executor_.recovery_manager.latchEstop();
         self->state_store_.execution_state = RobotCoreState::Estop;
         self->state_store_.fault_code = "ESTOP";
         self->queueAlarmLocked("FATAL_FAULT", "safety", "急停触发");
         return self->replyJson(inv.request_id, true, "emergency_stop accepted");
       }},
  };
  const auto it = handlers.find(command);
  if (it == handlers.end()) {
    return replyJson(invocation.request_id, false, "unsupported command: " + command);
  }
  return it->second(this, invocation);
}


}  // namespace robot_core
