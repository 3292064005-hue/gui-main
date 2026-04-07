from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig


class MainlineRuntimeDoctorService:
    """Unify runtime-side contracts into a single operator-facing readiness verdict.

    This service intentionally does not replace the official runtime/core verdict.
    It summarizes whether the *governance shell* around the official SDK mainline
    is internally aligned: single control source, session freeze, motion/runtime
    contract, model authority, and deployment constraints.
    """

    def inspect(
        self,
        *,
        config: RuntimeConfig,
        sdk_runtime: dict[str, Any] | None = None,
        backend_link: dict[str, Any] | None = None,
        model_report: dict[str, Any] | None = None,
        session_governance: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        sdk_runtime = dict(sdk_runtime or {})
        backend_link = dict(backend_link or {})
        model_report = dict(model_report or {})
        session_governance = dict(session_governance or {})

        blockers: list[dict[str, Any]] = []
        warnings: list[dict[str, Any]] = []
        sections: dict[str, Any] = {}

        def push(target: list[dict[str, Any]], section: str, name: str, detail: str) -> None:
            target.append({"section": section, "name": name, "detail": detail})

        control = dict(sdk_runtime.get("control_governance_contract", {}))
        runtime_alignment = dict(sdk_runtime.get("runtime_alignment", {}))
        clinical = dict(sdk_runtime.get("clinical_mainline_contract", {}))
        capability = dict(sdk_runtime.get("capability_contract", {}))
        robot_family = dict(sdk_runtime.get("robot_family_contract", {}))
        vendor_boundary = dict(sdk_runtime.get("vendor_boundary_contract", {}))
        profile_matrix = dict(sdk_runtime.get("profile_matrix_contract", {}))
        model_authority = dict(sdk_runtime.get("model_authority_contract", {}))
        motion = dict(sdk_runtime.get("motion_contract", {}))
        session_freeze = dict(sdk_runtime.get("session_freeze", {}))
        session_drift = dict(sdk_runtime.get("session_drift_contract", {}))
        hardware_lifecycle = dict(sdk_runtime.get("hardware_lifecycle_contract", {}))
        rt_kernel = dict(sdk_runtime.get("rt_kernel_contract", {}))
        release_contract = dict(sdk_runtime.get("release_contract", {}))
        deployment = dict(sdk_runtime.get("deployment_contract", {}))
        environment = dict(sdk_runtime.get("environment_doctor", {}))
        controller_evidence = dict(sdk_runtime.get("controller_evidence", {}))
        recovery_contract = dict(sdk_runtime.get("recovery_contract", {}))
        safety_recovery_contract = dict(sdk_runtime.get("safety_recovery_contract", recovery_contract))
        dual_state_machine = dict(sdk_runtime.get("dual_state_machine_contract", {}))
        mainline_executor = dict(sdk_runtime.get("mainline_executor_contract", {}))
        mainline_task_tree = dict(sdk_runtime.get("mainline_task_tree", {}))

        expected_rt_mode = str(clinical.get("clinical_mainline_mode") or config.rt_mode)
        actual_rt_mode = str(motion.get("rt_mode") or config.rt_mode)
        if expected_rt_mode and actual_rt_mode and expected_rt_mode != actual_rt_mode:
            push(blockers, "clinical_mainline", "rt_mode_mismatch", f"runtime rt_mode={actual_rt_mode}, expected={expected_rt_mode}")

        if bool(control.get("single_control_source_required", config.requires_single_control_source)):
            ownership = dict(backend_link.get("control_plane", {})).get("control_authority", {}) or {}
            ownership_state = str(ownership.get("summary_state", ""))
            if ownership_state == "blocked":
                push(blockers, "control_governance", "control_authority_conflict", str(ownership.get("detail", "控制权冲突")))
            elif ownership_state in {"degraded", "warning"}:
                push(warnings, "control_governance", "control_authority_degraded", str(ownership.get("detail", "控制权非严格收敛")))

        session_locked = bool(session_freeze.get("session_locked"))
        if session_locked and not bool(control.get("session_binding_valid", True)):
            push(blockers, "session_freeze", "session_binding_invalid", str(control.get("detail") or "session 已锁定但 plan_hash/runtime bind 不一致"))
        elif not session_locked:
            push(warnings, "session_freeze", "session_not_locked_yet", "会话尚未冻结；启动链会在正式执行前完成 lock_session。")

        if session_locked and not bool(control.get("runtime_config_bound", False)):
            push(warnings, "session_freeze", "runtime_config_unbound", "运行时配置尚未形成冻结绑定。")

        final_verdict = dict(model_report.get("final_verdict", {}))
        verdict_kind = str(model_report.get("verdict_kind", ""))
        authority_source = str(model_report.get("authority_source", ""))
        explicit_authoritative = final_verdict.get("authoritative")
        verdict_authoritative = bool(explicit_authoritative) if explicit_authoritative is not None else (verdict_kind == "final" or authority_source == "cpp_robot_core")
        verdict_unavailable = (verdict_kind == "unavailable" or authority_source == "verdict_unavailable") or (bool(final_verdict) and not verdict_authoritative and explicit_authoritative is False)
        if final_verdict and not bool(final_verdict.get("accepted", False)):
            reason = str(final_verdict.get("reason", "runtime final verdict rejected"))
            if verdict_unavailable:
                push(warnings, "model_precheck", "authoritative_verdict_unavailable", reason)
            else:
                push(blockers, "model_precheck", "final_verdict_rejected", reason)
        elif verdict_unavailable:
            push(warnings, "model_precheck", "authoritative_verdict_unavailable", "当前尚未拿到 runtime authoritative verdict。")

        if not bool(model_authority.get("planner_supported", True)) or not bool(model_authority.get("xmate_model_supported", True)):
            push(warnings, "model_authority", "official_model_unavailable", "当前运行环境未确认官方 Planner/xMateModel 权威可用。")
        if model_authority and not bool(model_authority.get("authoritative_runtime", False)) and str(profile_matrix.get("name", "")) in {"research", "clinical"}:
            push(warnings, "model_authority", "authoritative_runtime_not_live", "当前 profile 期望 live/mainline 约束，但 authoritative runtime 仍未 ready。")

        if safety_recovery_contract:
            if str(safety_recovery_contract.get("summary_state", "ready")) == "blocked":
                push(blockers, "safety_recovery", "recovery_kernel_blocked", str(safety_recovery_contract.get("detail", "safety/recovery kernel blocked")))
            elif str(safety_recovery_contract.get("summary_state", "ready")) in {"warning", "degraded"}:
                push(warnings, "safety_recovery", "recovery_kernel_active", str(safety_recovery_contract.get("detail", "safety/recovery kernel active")))
            if not bool(safety_recovery_contract.get("runtime_guard_enforced", True)):
                push(blockers, "safety_recovery", "runtime_guard_missing", "safety/recovery contract 未声明 runtime guard 生效。")

        if environment.get("summary_state") == "blocked":
            push(blockers, "environment", "sdk_environment_blocked", str(environment.get("detail", "SDK 环境检查未通过。")))
        elif environment.get("summary_state") in {"warning", "degraded"}:
            push(warnings, "environment", "sdk_environment_warning", str(environment.get("detail", "SDK 环境存在告警。")))

        if runtime_alignment.get("sdk_available") is False:
            target = blockers if bool(profile_matrix.get("requires_live_sdk", False)) else warnings
            push(target, "runtime_alignment", "sdk_not_live", "当前为 contract/mock 对齐环境，未确认实机 SDK 已接管。")

        expected_family_rt = str(robot_family.get("clinical_rt_mode") or expected_rt_mode)
        if expected_family_rt and actual_rt_mode and expected_family_rt != actual_rt_mode:
            push(blockers, "robot_family", "family_rt_mode_mismatch", f"family clinical_rt_mode={expected_family_rt}, runtime rt_mode={actual_rt_mode}")
        if bool(control.get("single_control_source_required", config.requires_single_control_source)) and bool(robot_family.get("requires_single_control_source", config.requires_single_control_source)) is False:
            push(blockers, "robot_family", "family_single_source_mismatch", "robot family contract 未要求唯一控制源，不能进入主线执行。")

        if vendor_boundary:
            binding_mode = str(vendor_boundary.get("binding_mode", "unknown"))
            requires_live_sdk = bool(profile_matrix.get("requires_live_sdk", False))
            if binding_mode in {"unknown", "contract_only", "vendored_sdk_contract_shell", "live_binding_degraded"} and requires_live_sdk:
                push(blockers, "vendor_boundary", "vendor_boundary_not_live", "当前 profile 要求 live SDK/mainline 接管，但 vendor boundary 仍未建立真实 live binding。")
            elif binding_mode in {"unknown", "contract_only"}:
                push(warnings, "vendor_boundary", "vendor_boundary_not_live", "当前 profile 仍处于 contract-only vendor boundary。")
            if bool(vendor_boundary.get("single_control_source_required", config.requires_single_control_source)) and bool(vendor_boundary.get("control_source_exclusive", True)) is False:
                push(blockers, "vendor_boundary", "vendor_boundary_not_exclusive", "vendor boundary 未确认唯一控制源。")
            if bool(vendor_boundary.get("fixed_period_enforced", True)) is False:
                push(blockers, "vendor_boundary", "vendor_boundary_fixed_period_missing", "vendor boundary 未声明固定周期 RT 约束。")

        if profile_matrix:
            profile_name = str(profile_matrix.get("name", ""))
            if profile_name == "review" and bool(profile_matrix.get("allows_write_commands", True)):
                push(blockers, "deployment", "review_profile_writable", "review profile 不应允许写命令。")
            if profile_name == "clinical" and bool(profile_matrix.get("requires_hil_gate", False)) and str(release_contract.get("summary_state", "blocked")) != "ready":
                push(warnings, "deployment", "clinical_release_not_ready", "clinical profile 已启用，但 release contract 尚未 ready。")

        if bool(motion.get("nrt_contract", {}).get("degraded_without_sdk", False)):
            push(warnings, "motion_contract", "nrt_degraded", "NRT 主线仍处于 contract/degraded 包装态。")
        if bool(motion.get("rt_contract", {}).get("degraded_without_sdk", False)):
            push(warnings, "motion_contract", "rt_degraded", "RT 主线仍处于 contract/degraded 包装态。")

        if dual_state_machine:
            if not bool(dual_state_machine.get("execution_and_clinical_aligned", True)):
                push(blockers, "state_machine", "dual_state_machine_misaligned", str(dual_state_machine.get("detail", "执行状态机与临床任务状态机未对齐。")))
            elif str(dual_state_machine.get("summary_state", "ready")) in {"warning", "degraded"}:
                push(warnings, "state_machine", "dual_state_machine_warning", str(dual_state_machine.get("detail", "双层状态机存在告警。")))

        if mainline_executor:
            if not bool(mainline_executor.get("task_tree_aligned", True)):
                push(blockers, "mainline_executor", "task_tree_executor_misaligned", str(mainline_executor.get("detail", "executor 合同与任务树阶段不一致。")))
            rt_executor = dict(mainline_executor.get("rt_executor", {}))
            nrt_executor = dict(mainline_executor.get("nrt_executor", {}))
            if rt_executor.get("summary_state") in {"warning", "degraded"}:
                push(warnings, "mainline_executor", "rt_executor_warning", str(rt_executor.get("detail", "RT executor degraded")))
            if nrt_executor.get("summary_state") in {"warning", "degraded"}:
                push(warnings, "mainline_executor", "nrt_executor_warning", str(nrt_executor.get("detail", "NRT executor degraded")))
            if bool(control.get("single_control_source_required", config.requires_single_control_source)) and bool(nrt_executor.get("requires_single_control_source", True)) is False:
                push(blockers, "mainline_executor", "nrt_single_control_source_not_required", "NRT executor 未声明唯一控制源前置条件。")
            if bool(nrt_executor.get("requires_move_reset", True)) is False:
                push(blockers, "mainline_executor", "nrt_move_reset_missing", "NRT executor 未要求 moveReset；可能复用脏缓存。")
            if bool(rt_executor.get("fixed_period_enforced", True)) is False:
                push(blockers, "mainline_executor", "rt_fixed_period_missing", "RT executor 未声明固定周期执行。")
            if bool(rt_executor.get("network_guard_enabled", True)) is False:
                push(blockers, "mainline_executor", "rt_network_guard_missing", "RT executor 未声明 network guard。")
            if bool(rt_executor.get("network_healthy", True)) is False:
                push(blockers, "mainline_executor", "rt_executor_network_unhealthy", "RT executor 当前网络健康状态不满足主线执行要求。")

        if mainline_task_tree:
            if str(mainline_task_tree.get("summary_state", "ready")) == "blocked":
                push(blockers, "mainline_task_tree", "task_tree_blocked", str(mainline_task_tree.get("detail", "临床主线任务树阻塞。")))
            elif str(mainline_task_tree.get("summary_state", "ready")) == "warning":
                push(warnings, "mainline_task_tree", "task_tree_warning", str(mainline_task_tree.get("detail", "临床主线任务树告警。")))


        if session_drift and str(session_drift.get("summary_state", "ready")) == "blocked":
            push(blockers, "session_freeze", "session_freeze_drift", str(session_drift.get("detail", "session freeze drift detected")))

        if hardware_lifecycle:
            hardware_state = str(hardware_lifecycle.get("summary_state", "ready"))
            requires_live_sdk = bool(profile_matrix.get("requires_live_sdk", False))
            lifecycle_state = str(hardware_lifecycle.get("lifecycle_state", hardware_lifecycle.get("hardware_lifecycle_state", "")) or "")
            if hardware_state == "blocked":
                push(blockers, "hardware_lifecycle", "hardware_lifecycle_blocked", str(hardware_lifecycle.get("detail", "hardware lifecycle blocked")))
            elif hardware_state in {"warning", "degraded"}:
                target = blockers if requires_live_sdk else warnings
                push(target, "hardware_lifecycle", "hardware_lifecycle_warning", str(hardware_lifecycle.get("detail", "hardware lifecycle warning")))
            if requires_live_sdk and lifecycle_state in {"", "disconnected", "network_degraded", "contract_shell_ready", "connected"}:
                push(blockers, "hardware_lifecycle", "live_takeover_not_ready", "当前 profile 要求 live takeover ready，但硬件生命周期仍未达到 auto/rt ready。")
            if bool(control.get("single_control_source_required", config.requires_single_control_source)) and bool(hardware_lifecycle.get("control_source_exclusive", True)) is False:
                push(blockers, "hardware_lifecycle", "control_source_not_exclusive", "硬件生命周期未确认唯一控制源；实机接管不应继续。")
            if bool(hardware_lifecycle.get("network_healthy", True)) is False:
                push(blockers, "hardware_lifecycle", "network_unhealthy", "硬件生命周期报告网络不健康；禁止进入主线执行。")

        if rt_kernel:
            if bool(rt_kernel.get("monitors", {}).get("reference_limiter")) is False:
                push(blockers, "rt_kernel", "reference_limiter_missing", "RT kernel 缺少 reference limiter。")
            if bool(rt_kernel.get("monitors", {}).get("freshness_guard")) is False:
                push(blockers, "rt_kernel", "freshness_guard_missing", "RT kernel 缺少 freshness guard。")
            if bool(rt_kernel.get("monitors", {}).get("jitter_monitor")) is False:
                push(warnings, "rt_kernel", "jitter_monitor_missing", "RT kernel 未声明 jitter monitor。")
            if bool(rt_kernel.get("monitors", {}).get("network_guard", rt_kernel.get("network_guard_enabled", False))) is False:
                push(blockers, "rt_kernel", "network_guard_missing", "RT kernel 缺少 network guard。")
            if bool(rt_kernel.get("fixed_period_enforced", False)) is False:
                push(blockers, "rt_kernel", "fixed_period_not_enforced", "RT kernel 未声明固定周期执行；不满足 1kHz 主线约束。")
            if bool(rt_kernel.get("network_healthy", True)) is False:
                push(blockers, "rt_kernel", "rt_network_unhealthy", "RT kernel 报告网络不健康；禁止继续接触/扫查主线。")
            if int(rt_kernel.get("overrun_count", 0) or 0) > 0:
                push(warnings, "rt_kernel", "rt_cycle_overrun_detected", f"RT kernel 观测到 overrun_count={int(rt_kernel.get('overrun_count', 0) or 0)}。")
            if str(rt_kernel.get("summary_state", "ready")) in {"warning", "degraded"}:
                push(warnings, "rt_kernel", "rt_kernel_warning", str(rt_kernel.get("detail", "rt kernel warning")))

        if session_governance.get("summary_state") == "blocked":
            push(blockers, "session_governance", "session_governance_blocked", str(session_governance.get("detail", "会话治理阻塞。")))
        elif session_governance.get("summary_state") == "warning":
            push(warnings, "session_governance", "session_governance_warning", str(session_governance.get("detail", "会话治理告警。")))

        if release_contract.get("summary_state") == "blocked":
            if session_locked or bool(release_contract.get("compile_ready")) or bool(release_contract.get("ready_for_approach")) or bool(release_contract.get("ready_for_scan")):
                push(blockers, "release_contract", "release_gate_blocked", str(release_contract.get("detail", "release contract blocked")))
            else:
                push(warnings, "release_contract", "release_gate_pending", str(release_contract.get("detail", "release contract pending until session lock")))

        if deployment.get("summary_state") in {"warning", "degraded"}:
            push(warnings, "deployment", "deployment_profile_warning", str(deployment.get("detail", deployment.get("summary_label", "deployment degraded"))))

        if controller_evidence and not str(controller_evidence.get("last_event", "")):
            push(warnings, "controller_evidence", "no_recent_controller_event", "尚未形成可关联的 controller event/evidence。")

        sections["control_governance"] = {
            "summary_state": "ready" if not any(item["section"] == "control_governance" for item in blockers + warnings) else ("blocked" if any(item["section"] == "control_governance" for item in blockers) else "warning"),
            "summary_label": "唯一控制源" if bool(control.get("single_control_source_required", config.requires_single_control_source)) else "控制源可共享",
            "detail": str(control.get("detail", "single control source contract")),
            "contract": control,
        }
        sections["session_freeze"] = {
            "summary_state": "ready" if session_locked and bool(control.get("session_binding_valid", True)) else ("warning" if not session_locked else "blocked"),
            "summary_label": "会话冻结已绑定" if session_locked else "会话待冻结",
            "detail": str(session_drift.get("detail") or control.get("detail") or session_governance.get("detail") or "session freeze contract"),
            "contract": {**session_freeze, "drift": session_drift},
        }
        sections["clinical_mainline"] = {
            "summary_state": "ready" if expected_rt_mode == actual_rt_mode else "blocked",
            "summary_label": "临床主线对齐",
            "detail": f"expected_rt_mode={expected_rt_mode}, runtime_rt_mode={actual_rt_mode}",
            "contract": clinical,
        }
        model_authority_state = "ready" if final_verdict.get("accepted", False) else ("warning" if verdict_unavailable else "blocked")
        sections["model_authority"] = {
            "summary_state": model_authority_state,
            "summary_label": "模型权威裁决",
            "detail": str(final_verdict.get("reason") or model_report.get("detail") or "model authority contract"),
            "contract": model_authority,
        }
        sections["runtime_alignment"] = {
            "summary_state": "ready" if runtime_alignment.get("sdk_available") else "warning",
            "summary_label": "SDK 运行时对齐",
            "detail": str(runtime_alignment.get("source", "runtime alignment contract")),
            "contract": runtime_alignment,
        }
        sections["robot_family"] = {
            "summary_state": "ready" if not any(item["section"] == "robot_family" for item in blockers + warnings) else ("blocked" if any(item["section"] == "robot_family" for item in blockers) else "warning"),
            "summary_label": str(robot_family.get("family_label", "机器人族能力矩阵")),
            "detail": str(robot_family.get("detail", "robot family contract")),
            "contract": robot_family,
        }
        sections["vendor_boundary"] = {
            "summary_state": "ready" if not any(item["section"] == "vendor_boundary" for item in blockers + warnings) else ("blocked" if any(item["section"] == "vendor_boundary" for item in blockers) else "warning"),
            "summary_label": str(vendor_boundary.get("summary_label", "Vendor Boundary")),
            "detail": str(vendor_boundary.get("detail", "vendor boundary contract")),
            "contract": vendor_boundary,
        }
        sections["deployment_profile"] = {
            "summary_state": "ready" if not any(item["section"] == "deployment" for item in blockers + warnings) else ("blocked" if any(item["section"] == "deployment" for item in blockers) else "warning"),
            "summary_label": str(profile_matrix.get("name", "deployment profile")),
            "detail": str(profile_matrix.get("description", "deployment profile contract")),
            "contract": profile_matrix,
        }
        sections["state_machine"] = {
            "summary_state": str(dual_state_machine.get("summary_state", "unknown")),
            "summary_label": str(dual_state_machine.get("summary_label", "双层状态机")),
            "detail": str(dual_state_machine.get("detail", "dual state machine contract")),
            "contract": dual_state_machine,
        }
        sections["mainline_executor"] = {
            "summary_state": str(mainline_executor.get("summary_state", "unknown")),
            "summary_label": str(mainline_executor.get("summary_label", "主线执行器")),
            "detail": str(mainline_executor.get("detail", "mainline executor contract")),
            "contract": mainline_executor,
        }
        sections["mainline_task_tree"] = {
            "summary_state": str(mainline_task_tree.get("summary_state", "unknown")),
            "summary_label": str(mainline_task_tree.get("summary_label", "临床主线任务树")),
            "detail": str(mainline_task_tree.get("detail", "mainline task tree contract")),
            "contract": mainline_task_tree,
        }
        sections["environment"] = {
            "summary_state": str(environment.get("summary_state", "unknown")),
            "summary_label": str(environment.get("summary_label", "SDK 环境")),
            "detail": str(environment.get("detail", "SDK environment doctor")),
            "contract": environment,
        }

        sections["hardware_lifecycle"] = {
            "summary_state": str(hardware_lifecycle.get("summary_state", "unknown")),
            "summary_label": str(hardware_lifecycle.get("summary_label", "硬件生命周期")),
            "detail": str(hardware_lifecycle.get("detail", "hardware lifecycle contract")),
            "contract": hardware_lifecycle,
        }
        sections["rt_kernel"] = {
            "summary_state": str(rt_kernel.get("summary_state", "unknown")),
            "summary_label": str(rt_kernel.get("summary_label", "RT 内核")),
            "detail": str(rt_kernel.get("detail", "rt kernel contract")),
            "contract": rt_kernel,
        }

        summary_state = "ready"
        if blockers:
            summary_state = "blocked"
        elif warnings:
            summary_state = "warning"

        return {
            "summary_state": summary_state,
            "summary_label": {
                "ready": "运行主线治理通过",
                "warning": "运行主线治理告警",
                "blocked": "运行主线治理阻塞",
            }[summary_state],
            "detail": "官方 SDK 主线、会话冻结、唯一控制源、模型裁决与环境检查的统一治理结果。",
            "blockers": blockers,
            "warnings": warnings,
            "sections": sections,
            "expected_rt_mode": expected_rt_mode,
            "runtime_rt_mode": actual_rt_mode,
            "session_locked": bool(session_freeze.get("session_locked")),
            "final_verdict_accepted": bool(final_verdict.get("accepted", False)),
            "single_control_source_required": bool(control.get("single_control_source_required", config.requires_single_control_source)),
            "sdk_live": bool(runtime_alignment.get("sdk_available", False)),
            "hardware_lifecycle_live": bool(hardware_lifecycle.get("live_takeover_ready", False)),
            "session_freeze_drift_count": len(session_drift.get("drifts", [])),
        }
