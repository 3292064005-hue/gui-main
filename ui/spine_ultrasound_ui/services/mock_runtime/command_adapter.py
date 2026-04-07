from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from spine_ultrasound_ui.models import RuntimeConfig, ScanPlan, SystemState
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope
from spine_ultrasound_ui.services.pressure_sensor_service import create_force_sensor_provider
from spine_ultrasound_ui.utils.sdk_unit_contract import build_sdk_boundary_contract
from spine_ultrasound_ui.utils import ensure_dir, now_ns
from spine_ultrasound_ui.utils.runtime_fingerprint import payload_hash


class MockRuntimeCommandAdapterMixin:
        def handle_command(self, command: str, payload: Optional[dict] = None) -> ReplyEnvelope:
            payload = payload or {}
            handler = getattr(self, f"_cmd_{command}", None)
            if handler is None:
                return ReplyEnvelope(ok=False, message=f"unsupported command: {command}")
            return handler(payload)

        def _cmd_query_controller_log(self, payload: dict) -> ReplyEnvelope:
            count = int(payload.get("count", 10) or 10)
            return ReplyEnvelope(ok=True, message="query_controller_log accepted", data={"logs": self.controller_logs[:max(1, count)]})

        def _cmd_query_rl_projects(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="query_rl_projects accepted", data={"projects": list(self.rl_projects), "status": dict(self.rl_status)})

        def _cmd_run_rl_project(self, payload: dict) -> ReplyEnvelope:
            project = str(payload.get("project", self.config.rl_project_name or "spine_mainline"))
            task = str(payload.get("task", self.config.rl_task_name or "scan"))
            candidates = {item["name"]: item for item in self.rl_projects}
            if project not in candidates:
                return ReplyEnvelope(ok=False, message=f"unknown RL project: {project}")
            if task not in list(candidates[project].get("tasks", [])):
                return ReplyEnvelope(ok=False, message=f"unknown RL task: {task}")
            self.rl_status.update({"loaded_project": project, "loaded_task": task, "running": True})
            self.execution_state = SystemState.AUTO_READY if self.execution_state in {SystemState.CONNECTED, SystemState.POWERED} else self.execution_state
            self._append_controller_log("INFO", f"RL project started: {project}/{task}")
            return ReplyEnvelope(ok=True, message="run_rl_project accepted", data={"status": dict(self.rl_status)})

        def _cmd_pause_rl_project(self, payload: dict) -> ReplyEnvelope:
            del payload
            self.rl_status["running"] = False
            self._append_controller_log("INFO", "RL project paused")
            return ReplyEnvelope(ok=True, message="pause_rl_project accepted", data={"status": dict(self.rl_status)})

        def _cmd_query_path_lists(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="query_path_lists accepted", data={"paths": list(self.path_library), "drag": dict(self.drag_state)})

        def _cmd_enable_drag(self, payload: dict) -> ReplyEnvelope:
            self.drag_state = {
                "enabled": True,
                "space": str(payload.get("space", "cartesian")),
                "type": str(payload.get("type", "admittance")),
            }
            self._append_controller_log("INFO", f"drag enabled: {self.drag_state['space']}/{self.drag_state['type']}")
            return ReplyEnvelope(ok=True, message="enable_drag accepted", data={"drag": dict(self.drag_state)})

        def _cmd_disable_drag(self, payload: dict) -> ReplyEnvelope:
            del payload
            self.drag_state["enabled"] = False
            self._append_controller_log("INFO", "drag disabled")
            return ReplyEnvelope(ok=True, message="disable_drag accepted", data={"drag": dict(self.drag_state)})

        def _cmd_replay_path(self, payload: dict) -> ReplyEnvelope:
            path_name = str(payload.get("name", "spine_demo_path"))
            match = next((item for item in self.path_library if item.get("name") == path_name), None)
            if match is None:
                return ReplyEnvelope(ok=False, message=f"unknown path: {path_name}")
            self._append_controller_log("INFO", f"path replay started: {path_name}")
            return ReplyEnvelope(ok=True, message="replay_path accepted", data={"path": dict(match)})

        def _cmd_get_io_snapshot(self, payload: dict) -> ReplyEnvelope:
            del payload
            snapshot = dict(self.io_state)
            snapshot["xpanel_vout_mode"] = self.config.xpanel_vout_mode
            return ReplyEnvelope(ok=True, message="get_io_snapshot accepted", data=snapshot)

        def _cmd_get_register_snapshot(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_register_snapshot accepted", data={"registers": dict(self.io_state.get("registers", {}))})

        def _cmd_get_safety_config(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(
                ok=True,
                message="get_safety_config accepted",
                data={
                    "collision_detection_enabled": self.config.collision_detection_enabled,
                    "collision_sensitivity": self.config.collision_sensitivity,
                    "collision_behavior": self.config.collision_behavior,
                    "collision_fallback_mm": self.config.collision_fallback_mm,
                    "soft_limit_enabled": self.config.soft_limit_enabled,
                    "joint_soft_limit_margin_deg": self.config.joint_soft_limit_margin_deg,
                    "singularity_avoidance_enabled": self.config.singularity_avoidance_enabled,
                },
            )

        def _cmd_get_motion_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(
                ok=True,
                message="get_motion_contract accepted",
                data={
                    "rt_mode": self.config.rt_mode,
                    "network_tolerance_percent": self.config.rt_network_tolerance_percent,
                    "preferred_link": self.config.preferred_link,
                    "filters": {
                        "joint_hz": self.config.joint_filter_hz,
                        "cart_hz": self.config.cart_filter_hz,
                        "torque_hz": self.config.torque_filter_hz,
                    },
                    "collision_behavior": self.config.collision_behavior,
                    "collision_detection_enabled": self.config.collision_detection_enabled,
                    "soft_limit_enabled": self.config.soft_limit_enabled,
                    "sdk_boundary_units": build_sdk_boundary_contract(fc_frame_matrix=self.config.fc_frame_matrix, tcp_frame_matrix=self.config.tcp_frame_matrix, load_com_mm=self.config.load_com_mm),
                },
            )

        def _cmd_get_runtime_alignment(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_runtime_alignment accepted", data=self._runtime_alignment_payload())

        def _cmd_get_xmate_model_summary(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_xmate_model_summary accepted", data=self._xmate_model_summary_payload())

        def _cmd_get_sdk_runtime_config(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_sdk_runtime_config accepted", data=self._sdk_runtime_config_payload())

        def _cmd_get_identity_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_identity_contract accepted", data=self._identity_payload())

        def _cmd_get_robot_family_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_robot_family_contract accepted", data=self._robot_family_contract_payload())

        def _cmd_get_vendor_boundary_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_vendor_boundary_contract accepted", data=self._vendor_boundary_contract_payload())

        def _cmd_get_clinical_mainline_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_clinical_mainline_contract accepted", data=self._clinical_mainline_contract_payload())

        def _cmd_get_session_freeze(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_session_freeze accepted", data=self._session_freeze_payload())

        def _cmd_get_authoritative_runtime_envelope(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_authoritative_runtime_envelope accepted", data=self._authoritative_runtime_envelope_payload())

        def _cmd_get_session_drift_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_session_drift_contract accepted", data=self._session_drift_contract_payload())

        def _cmd_get_hardware_lifecycle_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_hardware_lifecycle_contract accepted", data=self._hardware_lifecycle_contract_payload())

        def _cmd_get_rt_kernel_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_rt_kernel_contract accepted", data=self._rt_kernel_contract_payload())

        def _cmd_get_control_governance_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_control_governance_contract accepted", data=self._control_governance_contract_payload())

        def _cmd_get_controller_evidence(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_controller_evidence accepted", data=self._controller_evidence_payload())

        def _cmd_get_dual_state_machine_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_dual_state_machine_contract accepted", data=self._dual_state_machine_contract_payload())

        def _cmd_get_mainline_executor_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_mainline_executor_contract accepted", data=self._mainline_executor_contract_payload())

        def _cmd_get_mainline_task_tree(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_mainline_task_tree accepted", data=self._mainline_task_tree_payload())

        def _cmd_get_recovery_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_recovery_contract accepted", data=self._recovery_contract_payload())

        def _cmd_get_safety_recovery_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_safety_recovery_contract accepted", data=self._safety_recovery_contract_payload())

        def _cmd_get_capability_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_capability_contract accepted", data=self._capability_contract_payload())

        def _cmd_get_model_authority_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_model_authority_contract accepted", data=self._model_authority_contract_payload())

        def _cmd_get_release_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_release_contract accepted", data=self._release_contract_payload())

        def _cmd_get_deployment_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_deployment_contract accepted", data=self._deployment_contract_payload())

        def _cmd_get_fault_injection_contract(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message="get_fault_injection_contract accepted", data=self._fault_injection_contract_payload())

        def _cmd_inject_fault(self, payload: dict) -> ReplyEnvelope:
            fault = str(payload.get("fault_name", "")).strip()
            if not fault:
                return ReplyEnvelope(ok=False, message="fault_name missing")
            self.injected_faults.add(fault)
            if fault == "pressure_stale":
                self.force_sensor_stale_ticks = max(self.force_sensor_stale_ticks, max(2, int(self.config.pressure_stale_ms / 100)))
                self.pressure_fresh = False
            elif fault == "rt_jitter_high":
                self.rt_jitter_ok = False
            elif fault == "overpressure":
                self.pressure_current = max(self.config.pressure_upper + 0.5, self.force_control["max_z_force_n"] + 0.5)
            elif fault == "collision_event":
                self.pending_alarms.append({
                    "severity": "RECOVERABLE_FAULT", "source": "collision", "message": "模拟碰撞事件", "session_id": self.session_id,
                    "segment_id": int(self.active_segment), "event_ts_ns": now_ns(), "workflow_step": "fault_injection", "request_id": "", "auto_action": "safe_retreat"
                })
                self.execution_state = SystemState.RETREATING
                self.retreat_ticks_remaining = max(self.retreat_ticks_remaining, 10)
            elif fault == "plan_hash_mismatch":
                self.plan_hash = f"mismatch:{self.plan_hash or 'empty'}"
            elif fault == "estop_latch":
                self.execution_state = SystemState.ESTOP
                self.fault_code = "ESTOP_INJECTED"
            else:
                self.injected_faults.discard(fault)
                return ReplyEnvelope(ok=False, message=f"unsupported fault injection: {fault}")
            self._append_controller_log("WARN", f"fault injected: {fault}", source="fault_injection")
            return ReplyEnvelope(ok=True, message="inject_fault accepted", data=self._fault_injection_contract_payload())

        def _cmd_clear_injected_faults(self, payload: dict) -> ReplyEnvelope:
            del payload
            self.injected_faults.clear()
            self.rt_jitter_ok = True
            self.force_sensor_stale_ticks = 0
            self.force_sensor_timeout_alarm = False
            self.force_sensor_estop_alarm = False
            if self.execution_state == SystemState.ESTOP and self.fault_code == "ESTOP_INJECTED":
                self.execution_state = SystemState.AUTO_READY if self.operate_mode == "automatic" and self.powered else (SystemState.POWERED if self.powered else SystemState.CONNECTED)
                self.fault_code = ""
            self._append_controller_log("INFO", "fault injections cleared", source="fault_injection")
            return ReplyEnvelope(ok=True, message="clear_injected_faults accepted", data=self._fault_injection_contract_payload())

        def _cmd_connect_robot(self, payload: dict) -> ReplyEnvelope:
            del payload
            if self.execution_state not in {SystemState.BOOT, SystemState.DISCONNECTED}:
                return ReplyEnvelope(ok=False, message="robot already connected")
            self.execution_state = SystemState.CONNECTED
            self.controller_online = True
            self.devices = {
                "robot": self._device(True, "online", "xMate3 robot_core 已连接"),
                "camera": self._device(True, "online", "摄像头在线"),
                "pressure": self._device(True, "online", f"压力传感器在线 ({self.force_sensor_provider_name})"),
                "ultrasound": self._device(True, "online", "超声设备在线"),
            }
            self.last_event = "robot_connected"
            self._append_controller_log("INFO", f"robot connected: remote={self.config.remote_ip} local={self.config.local_ip}")
            return ReplyEnvelope(ok=True, message="connect_robot accepted")

        def _cmd_disconnect_robot(self, payload: dict) -> ReplyEnvelope:
            del payload
            config = self.config
            self.__init__()
            self.config = config
            return ReplyEnvelope(ok=True, message="disconnect_robot accepted")

        def _cmd_power_on(self, payload: dict) -> ReplyEnvelope:
            del payload
            if self.execution_state == SystemState.DISCONNECTED:
                return ReplyEnvelope(ok=False, message="robot not connected")
            self.powered = True
            self.execution_state = SystemState.POWERED
            self.last_event = "power_on"
            self._append_controller_log("INFO", "power on")
            return ReplyEnvelope(ok=True, message="power_on accepted")

        def _cmd_power_off(self, payload: dict) -> ReplyEnvelope:
            del payload
            self.powered = False
            self.execution_state = SystemState.CONNECTED
            self.operate_mode = "manual"
            self.last_event = "power_off"
            return ReplyEnvelope(ok=True, message="power_off accepted")

        def _cmd_set_auto_mode(self, payload: dict) -> ReplyEnvelope:
            del payload
            if not self.powered:
                return ReplyEnvelope(ok=False, message="robot not powered")
            self.operate_mode = "automatic"
            self.execution_state = SystemState.AUTO_READY
            self._append_controller_log("INFO", "operate mode -> automatic")
            return ReplyEnvelope(ok=True, message="set_auto_mode accepted")

        def _cmd_set_manual_mode(self, payload: dict) -> ReplyEnvelope:
            del payload
            self.operate_mode = "manual"
            self.execution_state = SystemState.POWERED if self.powered else SystemState.CONNECTED
            return ReplyEnvelope(ok=True, message="set_manual_mode accepted")

        def _cmd_validate_setup(self, payload: dict) -> ReplyEnvelope:
            del payload
            safety = self._safety_status()
            ok = safety["safe_to_arm"]
            return ReplyEnvelope(ok=ok, message="setup validated" if ok else "setup invalid", data=safety)

        def _cmd_lock_session(self, payload: dict) -> ReplyEnvelope:
            if self.execution_state != SystemState.AUTO_READY:
                return ReplyEnvelope(ok=False, message="core not ready for session lock")
            self.session_id = str(payload.get("session_id", ""))
            if not self.session_id:
                return ReplyEnvelope(ok=False, message="session_id missing")
            self.locked_scan_plan_hash = str(payload.get("scan_plan_hash", ""))
            config_snapshot = dict(payload.get("config_snapshot", {}))
            if config_snapshot:
                self.config = RuntimeConfig.from_dict(config_snapshot)
            capability_report = self.capability_service.build(self.config, {"operate_mode": self.operate_mode, "powered": self.powered})
            blockers = list(capability_report.get("blockers", []))
            if blockers:
                self.session_id = ""
                self.locked_scan_plan_hash = ""
                return ReplyEnvelope(ok=False, message=str(blockers[0].get("detail", blockers[0].get("name", "configuration blocked"))))
            self.tool_ready = bool(self.config.tool_name)
            self.tcp_ready = bool(self.config.tcp_name)
            self.load_ready = self.config.load_kg > 0.0
            self.session_dir = ensure_dir(Path(str(payload.get("session_dir", "."))))
            self.device_roster = dict(payload.get("device_roster", {}))
            self.force_sensor_provider_name = str(payload.get("force_sensor_provider", self.config.force_sensor_provider))
            self.force_sensor_provider = create_force_sensor_provider(self.force_sensor_provider_name)
            self._open_recorders(self.session_dir, self.session_id)
            self.locked_runtime_config_hash = payload_hash(self._runtime_profile_payload())
            sdk_boundary = build_sdk_boundary_contract(fc_frame_matrix=self.config.fc_frame_matrix, tcp_frame_matrix=self.config.tcp_frame_matrix, load_com_mm=self.config.load_com_mm)
            self.locked_sdk_boundary_hash = str(sdk_boundary.get('contract_hash', ''))
            self.locked_executor_hash = payload_hash(self._executor_profile_payload())
            self.session_locked_ts_ns = now_ns()
            self.execution_state = SystemState.SESSION_LOCKED
            self._append_controller_log("INFO", f"session locked: {self.session_id}")
            self.recovery_reason = ""
            self.last_recovery_action = "session_locked"
            self.last_event = "session_locked"
            return ReplyEnvelope(ok=True, message="lock_session accepted", data={"session_id": self.session_id})

        def _cmd_load_scan_plan(self, payload: dict) -> ReplyEnvelope:
            if self.execution_state not in {SystemState.SESSION_LOCKED, SystemState.PATH_VALIDATED, SystemState.SCAN_COMPLETE}:
                return ReplyEnvelope(ok=False, message="session not locked")
            plan_payload = dict(payload.get("scan_plan", {}))
            validation_error = self._validate_scan_plan(plan_payload)
            if validation_error:
                return ReplyEnvelope(ok=False, message=validation_error)
            self.scan_plan = plan_payload
            self.plan_hash = self._plan_hash(plan_payload)
            if self.locked_scan_plan_hash and self.plan_hash and self.locked_scan_plan_hash != self.plan_hash:
                self.scan_plan = None
                self.plan_hash = ""
                return ReplyEnvelope(ok=False, message="locked scan_plan_hash does not match loaded plan")
            self.path_index = 0
            self.progress_pct = 0.0
            self.active_segment = 0
            self.execution_state = SystemState.PATH_VALIDATED
            self._append_controller_log("INFO", f"scan plan loaded: {plan_payload.get('plan_id', '-')}")
            self.contact_stable = False
            self.recovery_reason = ""
            self.last_recovery_action = "load_scan_plan"
            self.last_event = "scan_plan_loaded"
            return ReplyEnvelope(ok=True, message="load_scan_plan accepted", data={"plan_id": plan_payload.get("plan_id", "")})

        def _cmd_approach_prescan(self, payload: dict) -> ReplyEnvelope:
            del payload
            if self.execution_state != SystemState.PATH_VALIDATED:
                return ReplyEnvelope(ok=False, message="scan plan not ready")
            self.execution_state = SystemState.APPROACHING
            self.contact_stable = False
            self.recommended_action = "SEEK_CONTACT"
            return ReplyEnvelope(ok=True, message="approach_prescan accepted")

        def _cmd_seek_contact(self, payload: dict) -> ReplyEnvelope:
            del payload
            if self.execution_state not in {SystemState.APPROACHING, SystemState.PATH_VALIDATED}:
                return ReplyEnvelope(ok=False, message="cannot seek contact from current state")
            self.execution_state = SystemState.CONTACT_STABLE
            self.contact_mode = "STABLE_CONTACT"
            self.contact_confidence = 0.82
            self.contact_stable = True
            self.recommended_action = "START_SCAN"
            self.last_recovery_action = "contact_stable"
            return ReplyEnvelope(ok=True, message="seek_contact accepted")

        def _cmd_start_scan(self, payload: dict) -> ReplyEnvelope:
            del payload
            if self.execution_state not in {SystemState.CONTACT_STABLE, SystemState.PAUSED_HOLD}:
                return ReplyEnvelope(ok=False, message="cannot start scan before contact is stable")
            self.execution_state = SystemState.SCANNING
            self.contact_mode = "STABLE_CONTACT"
            self.contact_stable = True
            self.recovery_reason = ""
            self.last_recovery_action = "start_scan"
            self.recommended_action = "SCAN"
            self.last_event = "scan_started"
            self._append_controller_log("INFO", "scan started")
            return ReplyEnvelope(ok=True, message="start_scan accepted")

        def _cmd_pause_scan(self, payload: dict) -> ReplyEnvelope:
            del payload
            if self.execution_state != SystemState.SCANNING:
                return ReplyEnvelope(ok=False, message="scan not active")
            self.execution_state = SystemState.PAUSED_HOLD
            self.contact_mode = "HOLDING_CONTACT"
            self.contact_stable = True
            self.recovery_reason = "operator_pause"
            self.last_recovery_action = "pause_hold"
            self.recommended_action = "RESUME_OR_RETREAT"
            return ReplyEnvelope(ok=True, message="pause_scan accepted")

        def _cmd_resume_scan(self, payload: dict) -> ReplyEnvelope:
            del payload
            if self.execution_state != SystemState.PAUSED_HOLD:
                return ReplyEnvelope(ok=False, message="scan not paused")
            self.execution_state = SystemState.SCANNING
            self.contact_mode = "STABLE_CONTACT"
            self.contact_stable = True
            self.recovery_reason = ""
            self.last_recovery_action = "resume_scan"
            self.recommended_action = "SCAN"
            return ReplyEnvelope(ok=True, message="resume_scan accepted")

        def _cmd_safe_retreat(self, payload: dict) -> ReplyEnvelope:
            del payload
            if self.execution_state in {SystemState.DISCONNECTED, SystemState.BOOT, SystemState.ESTOP}:
                return ReplyEnvelope(ok=False, message="cannot retreat from current state")
            self.execution_state = SystemState.RETREATING
            self.retreat_ticks_remaining = 6
            self.contact_mode = "NO_CONTACT"
            self.contact_stable = False
            self.recovery_reason = "requested_safe_retreat"
            self.last_recovery_action = "safe_retreat"
            self.recommended_action = "WAIT_RETREAT_COMPLETE"
            self.last_event = "safe_retreat"
            self._append_controller_log("WARN", "safe retreat requested")
            return ReplyEnvelope(ok=True, message="safe_retreat accepted")

        def _cmd_go_home(self, payload: dict) -> ReplyEnvelope:
            del payload
            self.tcp_pose = {"x": 0.0, "y": 0.0, "z": 240.0, "rx": 180.0, "ry": 0.0, "rz": 90.0}
            self.last_event = "go_home"
            self._append_controller_log("INFO", "go home")
            return ReplyEnvelope(ok=True, message="go_home accepted")

        def _cmd_clear_fault(self, payload: dict) -> ReplyEnvelope:
            del payload
            if self.execution_state != SystemState.FAULT:
                return ReplyEnvelope(ok=False, message="no fault to clear")
            self.fault_code = ""
            self.execution_state = SystemState.PATH_VALIDATED if self.scan_plan else SystemState.AUTO_READY
            return ReplyEnvelope(ok=True, message="clear_fault accepted")

        def _cmd_emergency_stop(self, payload: dict) -> ReplyEnvelope:
            del payload
            self.execution_state = SystemState.ESTOP
            self.fault_code = "ESTOP"
            self.last_event = "emergency_stop"
            self._queue_alarm("FATAL_FAULT", "safety", "急停触发", workflow_step="emergency_stop", auto_action="estop")
            self._append_controller_log("ERROR", "emergency stop")
            return ReplyEnvelope(ok=True, message="emergency_stop accepted")

        def _cmd_compile_scan_plan(self, payload: dict) -> ReplyEnvelope:
            verdict = self.compile_scan_plan_verdict(payload.get('scan_plan'), payload.get('config_snapshot'))
            return ReplyEnvelope(ok=bool(verdict.get('final_verdict', {}).get('accepted', False)), message=str(verdict.get('detail', 'compile_scan_plan evaluated')), data={'final_verdict': verdict})

        def _cmd_query_final_verdict(self, payload: dict) -> ReplyEnvelope:
            del payload
            return ReplyEnvelope(ok=True, message='final verdict snapshot', data={'final_verdict': dict(self.last_final_verdict)})
