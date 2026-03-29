from __future__ import annotations

import math
import random
from pathlib import Path
from typing import Any, Dict, List, Optional

from spine_ultrasound_ui.core.session_recorders import JsonlRecorder
from spine_ultrasound_ui.models import RuntimeConfig, SystemState
from spine_ultrasound_ui.services.force_control_config import load_force_control_config
from spine_ultrasound_ui.services.ipc_protocol import ReplyEnvelope, TelemetryEnvelope
from spine_ultrasound_ui.services.pressure_sensor_service import ForceSensorProvider, create_force_sensor_provider
from spine_ultrasound_ui.utils import ensure_dir, now_ns


class MockCoreRuntime:
    def __init__(self) -> None:
        self.config = RuntimeConfig()
        self.force_control = load_force_control_config()
        self.execution_state = SystemState.DISCONNECTED
        self.controller_online = False
        self.powered = False
        self.operate_mode = "manual"
        self.fault_code = ""
        self.session_id = ""
        self.session_dir: Optional[Path] = None
        self.scan_plan: Optional[dict] = None
        self.phase = 0.0
        self.frame_id = 0
        self.path_index = 0
        self.progress_pct = 0.0
        self.active_segment = 0
        self.pressure_current = 0.0
        self.contact_mode = "NO_CONTACT"
        self.contact_confidence = 0.0
        self.contact_stable = False
        self.recommended_action = "IDLE"
        self.plan_hash = ""
        self.recovery_reason = ""
        self.last_recovery_action = ""
        self.image_quality = 0.82
        self.feature_confidence = 0.76
        self.quality_score = 0.79
        self.last_event = "-"
        self.last_controller_log = "-"
        self.retreat_ticks_remaining = 0
        self.dropped_samples = 0
        self.last_flush_ns = 0
        self.recorders: dict[str, JsonlRecorder] = {}
        self.device_roster: Dict[str, Any] = {}
        self.tool_ready = False
        self.tcp_ready = False
        self.load_ready = False
        self.pressure_fresh = False
        self.robot_state_fresh = False
        self.rt_jitter_ok = True
        self.force_sensor_provider_name = "mock_force_sensor"
        self.force_sensor_provider: ForceSensorProvider = create_force_sensor_provider(self.force_sensor_provider_name)
        self.force_sensor_status = "ok"
        self.force_sensor_source = self.force_sensor_provider_name
        self.force_sensor_stale_ticks = 0
        self.force_sensor_timeout_alarm = False
        self.force_sensor_estop_alarm = False
        self.devices = {
            "robot": self._device(False, "offline", "xMate ER3 控制器未连接"),
            "camera": self._device(False, "offline", "摄像头未连接"),
            "pressure": self._device(False, "offline", "压力传感器未连接"),
            "ultrasound": self._device(False, "offline", "超声设备未连接"),
        }
        self.tcp_pose = {"x": 0.0, "y": 0.0, "z": 240.0, "rx": 180.0, "ry": 0.0, "rz": 90.0}
        self.joint_pos = [0.0] * 6
        self.joint_vel = [0.0] * 6
        self.joint_torque = [0.0] * 6
        self.cart_force = [0.0] * 6
        self.pending_alarms: list[dict[str, Any]] = []

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        self.config = config
        self.force_sensor_provider_name = config.force_sensor_provider
        self.force_sensor_provider = create_force_sensor_provider(config.force_sensor_provider)

    def handle_command(self, command: str, payload: Optional[dict] = None) -> ReplyEnvelope:
        payload = payload or {}
        handler = getattr(self, f"_cmd_{command}", None)
        if handler is None:
            return ReplyEnvelope(ok=False, message=f"unsupported command: {command}")
        return handler(payload)

    def tick(self) -> list[TelemetryEnvelope]:
        self.phase += 0.15
        self.frame_id += 1
        self.image_quality = 0.78 + 0.12 * math.sin(self.phase * 0.7)
        self.feature_confidence = 0.74 + 0.10 * math.cos(self.phase * 0.45)
        self.quality_score = round((self.image_quality + self.feature_confidence) / 2.0, 3)
        self._update_robot_kinematics()
        self._update_contact_and_progress()
        ts_ns = now_ns()
        self._refresh_device_health(ts_ns)
        self._record_core_streams(ts_ns)
        return self.telemetry_snapshot(ts_ns=ts_ns)

    def telemetry_snapshot(self, ts_ns: Optional[int] = None) -> list[TelemetryEnvelope]:
        ts_ns = ts_ns or now_ns()
        messages = [
            TelemetryEnvelope(
                topic="core_state",
                ts_ns=ts_ns,
                data={
                    "execution_state": self.execution_state.value,
                    "armed": bool(self.session_id and self.scan_plan and self.execution_state not in {SystemState.FAULT, SystemState.ESTOP}),
                    "fault_code": self.fault_code,
                    "active_segment": self.active_segment,
                    "progress_pct": self.progress_pct,
                    "session_id": self.session_id,
                    "recovery_state": self._recovery_state(),
                    "plan_hash": self.plan_hash,
                    "contact_stable": self.contact_stable,
                },
            ),
            TelemetryEnvelope(
                topic="robot_state",
                ts_ns=ts_ns,
                data={
                    "powered": self.powered,
                    "operate_mode": self.operate_mode,
                    "joint_pos": self.joint_pos,
                    "joint_vel": self.joint_vel,
                    "joint_torque": self.joint_torque,
                    "cart_force": self.cart_force,
                    "tcp_pose": self.tcp_pose,
                    "last_event": self.last_event,
                    "last_controller_log": self.last_controller_log,
                },
            ),
            TelemetryEnvelope(
                topic="contact_state",
                ts_ns=ts_ns,
                data={
                    "mode": self.contact_mode,
                    "confidence": self.contact_confidence,
                    "pressure_current": self.pressure_current,
                    "recommended_action": self.recommended_action,
                    "contact_stable": self.contact_stable,
                },
            ),
            TelemetryEnvelope(
                topic="scan_progress",
                ts_ns=ts_ns,
                data={
                    "active_segment": self.active_segment,
                    "path_index": self.path_index,
                    "overall_progress": self.progress_pct,
                    "frame_id": self.frame_id,
                },
            ),
            TelemetryEnvelope(topic="device_health", ts_ns=ts_ns, data={"devices": self.devices}),
            TelemetryEnvelope(topic="safety_status", ts_ns=ts_ns, data=self._safety_status()),
            TelemetryEnvelope(
                topic="recording_status",
                ts_ns=ts_ns,
                data={
                    "session_id": self.session_id,
                    "recording": bool(self.recorders),
                    "dropped_samples": self.dropped_samples,
                    "last_flush_ns": self.last_flush_ns,
                },
            ),
            TelemetryEnvelope(
                topic="quality_feedback",
                ts_ns=ts_ns,
                data={
                    "image_quality": self.image_quality,
                    "feature_confidence": self.feature_confidence,
                    "quality_score": self.quality_score,
                    "need_resample": self.quality_score < self.config.image_quality_threshold,
                },
            ),
        ]
        for alarm in self.pending_alarms:
            messages.append(TelemetryEnvelope(topic="alarm_event", ts_ns=ts_ns, data=alarm))
        self.pending_alarms.clear()
        return messages

    def _cmd_connect_robot(self, payload: dict) -> ReplyEnvelope:
        del payload
        if self.execution_state not in {SystemState.BOOT, SystemState.DISCONNECTED}:
            return ReplyEnvelope(ok=False, message="robot already connected")
        self.execution_state = SystemState.CONNECTED
        self.controller_online = True
        self.devices = {
            "robot": self._device(True, "online", "xMate ER3 robot_core 已连接"),
            "camera": self._device(True, "online", "摄像头在线"),
            "pressure": self._device(True, "online", f"压力传感器在线 ({self.force_sensor_provider_name})"),
            "ultrasound": self._device(True, "online", "超声设备在线"),
        }
        self.last_event = "robot_connected"
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
        config_snapshot = dict(payload.get("config_snapshot", {}))
        if config_snapshot:
            self.config = RuntimeConfig.from_dict(config_snapshot)
        self.tool_ready = bool(self.config.tool_name)
        self.tcp_ready = bool(self.config.tcp_name)
        self.load_ready = self.config.load_kg > 0.0
        self.session_dir = ensure_dir(Path(str(payload.get("session_dir", "."))))
        self.device_roster = dict(payload.get("device_roster", {}))
        self.force_sensor_provider_name = str(payload.get("force_sensor_provider", self.config.force_sensor_provider))
        self.force_sensor_provider = create_force_sensor_provider(self.force_sensor_provider_name)
        self._open_recorders(self.session_dir, self.session_id)
        self.execution_state = SystemState.SESSION_LOCKED
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
        self.path_index = 0
        self.progress_pct = 0.0
        self.active_segment = 0
        self.execution_state = SystemState.PATH_VALIDATED
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
        return ReplyEnvelope(ok=True, message="safe_retreat accepted")

    def _cmd_go_home(self, payload: dict) -> ReplyEnvelope:
        del payload
        self.tcp_pose = {"x": 0.0, "y": 0.0, "z": 240.0, "rx": 180.0, "ry": 0.0, "rz": 90.0}
        self.last_event = "go_home"
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
        return ReplyEnvelope(ok=True, message="emergency_stop accepted")

    def _update_robot_kinematics(self) -> None:
        self.joint_pos = [round(math.sin(self.phase * 0.1 + i * 0.2), 4) for i in range(6)]
        self.joint_vel = [round(0.08 * math.cos(self.phase * 0.2 + i * 0.15), 4) for i in range(6)]
        self.joint_torque = [round(0.45 * math.sin(self.phase * 0.16 + i * 0.18), 4) for i in range(6)]
        z_base = 240.0
        if self.execution_state == SystemState.APPROACHING:
            z_base = 220.0
        elif self.execution_state in {SystemState.CONTACT_SEEKING, SystemState.CONTACT_STABLE, SystemState.SCANNING, SystemState.PAUSED_HOLD}:
            z_base = 205.0
        elif self.execution_state == SystemState.RETREATING:
            z_base = 230.0
        self.tcp_pose = {
            "x": round(118.0 + 8.0 * math.sin(self.phase * 0.2), 2),
            "y": round(15.0 + 5.0 * math.cos(self.phase * 0.25), 2),
            "z": round(z_base + 2.5 * math.sin(self.phase * 0.33), 2),
            "rx": 180.0,
            "ry": round(0.3 * math.sin(self.phase), 3),
            "rz": 90.0,
        }

    def _update_contact_and_progress(self) -> None:
        force_sample = self.force_sensor_provider.read_sample(
            contact_active=self.execution_state in {SystemState.CONTACT_SEEKING, SystemState.CONTACT_STABLE, SystemState.SCANNING, SystemState.PAUSED_HOLD},
            desired_force_n=float(self.force_control["desired_contact_force_n"]),
        )
        self.force_sensor_status = force_sample.status
        self.force_sensor_source = force_sample.source
        measured_pressure = abs(float(force_sample.wrench_n[2])) if force_sample.status == "ok" else 0.0
        if force_sample.status == "ok":
            self.force_sensor_stale_ticks = 0
        else:
            self.force_sensor_stale_ticks += 1
        if self.execution_state == SystemState.CONTACT_SEEKING:
            self.pressure_current = round(max(measured_pressure, 0.0), 3)
            self.contact_mode = "SEEKING_CONTACT"
            self.contact_confidence = 0.72
            self.contact_stable = False
            self.recommended_action = "WAIT_CONTACT_STABLE"
        elif self.execution_state == SystemState.CONTACT_STABLE:
            self.pressure_current = round(measured_pressure if measured_pressure > 0.0 else self.config.pressure_target, 3)
            self.contact_mode = "STABLE_CONTACT"
            self.contact_confidence = 0.84
            self.contact_stable = True
            self.recommended_action = "START_SCAN"
        elif self.execution_state == SystemState.SCANNING:
            total_points = max(sum(len(segment.get("waypoints", [])) for segment in self.scan_plan.get("segments", [])) if self.scan_plan else 0, 120)
            self.path_index += 1
            self.progress_pct = min(100.0, self.progress_pct + 100.0 / total_points)
            self.active_segment = self._segment_for_path_index()
            self.pressure_current = round(measured_pressure if measured_pressure > 0.0 else self.config.pressure_target + 0.08 * math.sin(self.phase) + random.uniform(-0.03, 0.03), 3)
            self.contact_mode = "STABLE_CONTACT"
            self.contact_confidence = 0.87
            self.contact_stable = True
            self.recommended_action = "SCAN"
            if self.pressure_current > self.config.pressure_upper:
                self.execution_state = SystemState.PAUSED_HOLD
                self.contact_mode = "OVERPRESSURE"
                self.contact_stable = False
                self.recovery_reason = "pressure_over_upper_limit"
                self.last_recovery_action = "pause_hold"
                self.recommended_action = "CONTROLLED_RETRACT"
                self._queue_alarm(
                    "RECOVERABLE_FAULT",
                    "contact",
                    "压力超上限，已进入保持状态",
                    workflow_step="scan_monitor",
                    auto_action="pause_hold",
                )
            if self.progress_pct >= 100.0:
                self.execution_state = SystemState.SCAN_COMPLETE
                self.contact_mode = "NO_CONTACT"
                self.contact_stable = False
                self.recovery_reason = ""
                self.last_recovery_action = "scan_complete"
                self.recommended_action = "POSTPROCESS"
                self.last_event = "scan_complete"
        elif self.execution_state == SystemState.PAUSED_HOLD:
            self.pressure_current = round(measured_pressure if measured_pressure > 0.0 else max(self.config.pressure_target - 0.03, 0.0), 3)
            self.contact_mode = "HOLDING_CONTACT"
            self.contact_confidence = 0.75
            self.contact_stable = True
            self.recommended_action = "RESUME_OR_RETREAT"
        elif self.execution_state == SystemState.RETREATING:
            self.pressure_current = 0.0
            self.contact_confidence = 0.0
            self.contact_mode = "NO_CONTACT"
            self.contact_stable = False
            self.recommended_action = "WAIT_RETREAT_COMPLETE"
            self.retreat_ticks_remaining -= 1
            if self.retreat_ticks_remaining <= 0:
                self.execution_state = SystemState.PATH_VALIDATED if self.scan_plan else SystemState.AUTO_READY
                self.recovery_reason = ""
                self.last_recovery_action = "retreat_complete"
                self.recommended_action = "IDLE"
        else:
            self.pressure_current = max(0.0, measured_pressure)
            self.contact_confidence = 0.0
            self.contact_mode = "NO_CONTACT"
            self.contact_stable = False
            self.recommended_action = "IDLE"
        self.cart_force = [0.02, 0.01, round(self.pressure_current, 3), 0.0, 0.0, 0.0]

    def _segment_for_path_index(self) -> int:
        if not self.scan_plan:
            return 0
        segments = self.scan_plan.get("segments", [])
        if not segments:
            return 0
        points_seen = 0
        for segment in segments:
            points_seen += max(len(segment.get("waypoints", [])), 1)
            if self.path_index <= points_seen:
                return int(segment.get("segment_id", 0))
        return int(segments[-1].get("segment_id", 0))

    def _recovery_state(self) -> str:
        if self.execution_state == SystemState.ESTOP:
            return "ESTOP_LATCHED"
        if self.execution_state == SystemState.FAULT:
            return "CONTROLLED_RETRACT"
        if self.execution_state == SystemState.PAUSED_HOLD:
            return "HOLDING"
        if self.execution_state in {SystemState.RETREATING, SystemState.SCAN_COMPLETE, SystemState.CONTACT_STABLE}:
            return "RETRY_READY" if self.execution_state != SystemState.CONTACT_STABLE else "IDLE"
        return "IDLE"

    def _safety_status(self) -> dict[str, Any]:
        interlocks = []
        if not self.controller_online or self.execution_state in {SystemState.BOOT, SystemState.DISCONNECTED}:
            interlocks.append("controller_offline")
        if not self.powered:
            interlocks.append("power_off")
        if self.operate_mode != "automatic":
            interlocks.append("not_in_automatic_mode")
        if not self.tool_ready:
            interlocks.append("tool_unvalidated")
        if not self.tcp_ready:
            interlocks.append("tcp_unvalidated")
        if not self.load_ready:
            interlocks.append("load_unvalidated")
        if not self.session_id:
            interlocks.append("session_unlocked")
        if not self.scan_plan:
            interlocks.append("scan_plan_missing")
        if not self.pressure_fresh:
            interlocks.append("pressure_stale")
        if not self.robot_state_fresh:
            interlocks.append("robot_state_stale")
        if self.pressure_current > self.config.pressure_upper:
            interlocks.append("pressure_over_upper_limit")
        if not self.rt_jitter_ok:
            interlocks.append("rt_jitter_high")
        if self.execution_state in {SystemState.FAULT, SystemState.ESTOP}:
            interlocks.append("fault_active")
        safe_to_arm = self.powered and self.operate_mode == "automatic" and self.execution_state not in {SystemState.DISCONNECTED, SystemState.ESTOP}
        safe_to_scan = safe_to_arm and not {
            "session_unlocked",
            "scan_plan_missing",
            "pressure_over_upper_limit",
            "fault_active",
            "pressure_stale",
            "robot_state_stale",
            "tool_unvalidated",
            "tcp_unvalidated",
            "load_unvalidated",
            "rt_jitter_high",
        } & set(interlocks)
        return {
            "safe_to_arm": safe_to_arm,
            "safe_to_scan": safe_to_scan,
            "active_interlocks": interlocks,
            "recovery_reason": self.recovery_reason,
            "last_recovery_action": self.last_recovery_action,
            "max_z_force_n": self.force_control["max_z_force_n"],
            "warning_z_force_n": self.force_control["warning_z_force_n"],
            "max_xy_force_n": self.force_control["max_xy_force_n"],
            "desired_contact_force_n": self.force_control["desired_contact_force_n"],
        }

    def _refresh_device_health(self, ts_ns: int) -> None:
        self.pressure_fresh = False
        self.robot_state_fresh = False
        stale_telemetry_ms = int(self.force_control["stale_telemetry_ms"])
        timeout_ms = int(self.force_control["sensor_timeout_ms"])
        current_stale_ms = self.force_sensor_stale_ticks * 100
        for name, device in self.devices.items():
            device["fresh"] = device["connected"]
            device["last_ts_ns"] = ts_ns if device["connected"] else 0
            if device["connected"] and name == "pressure":
                self.pressure_fresh = self.force_sensor_status == "ok" and current_stale_ms < stale_telemetry_ms
                device["fresh"] = self.pressure_fresh
                device["health"] = "online" if self.pressure_fresh else "degraded"
                device["detail"] = (
                    f"{self.force_sensor_source} fresh"
                    if self.pressure_fresh
                    else f"{self.force_sensor_source} stale ({current_stale_ms} ms)"
                )
            if device["connected"] and name == "robot":
                self.robot_state_fresh = True
            if self.execution_state in {SystemState.FAULT, SystemState.ESTOP} and name == "robot":
                device["health"] = "fault"
                device["detail"] = "机器人控制器处于故障或急停状态"
        if current_stale_ms >= stale_telemetry_ms and not self.force_sensor_timeout_alarm:
            self._queue_alarm(
                "WARN",
                "sensor",
                "力传感器数据陈旧，已触发 stale telemetry 告警",
                workflow_step="telemetry_watchdog",
                auto_action="mark_stale",
            )
            self.force_sensor_timeout_alarm = True
        if current_stale_ms < stale_telemetry_ms:
            self.force_sensor_timeout_alarm = False
        if self.execution_state == SystemState.SCANNING and current_stale_ms >= timeout_ms and not self.force_sensor_estop_alarm:
            self.execution_state = SystemState.PAUSED_HOLD
            self.contact_mode = "SENSOR_STALE"
            self.contact_stable = False
            self.recovery_reason = "sensor_timeout"
            self.last_recovery_action = "pause_hold"
            self.recommended_action = "CONTROLLED_RETRACT"
            self._queue_alarm(
                "RECOVERABLE_FAULT",
                "sensor",
                "力传感器超时，已进入保持状态",
                workflow_step="scan_monitor",
                auto_action="pause_hold",
            )
            self.force_sensor_estop_alarm = True
        if self.execution_state in {SystemState.SCANNING, SystemState.PAUSED_HOLD} and current_stale_ms >= timeout_ms * 2 and self.fault_code != "SENSOR_TIMEOUT":
            self.execution_state = SystemState.ESTOP
            self.fault_code = "SENSOR_TIMEOUT"
            self.contact_stable = False
            self.recovery_reason = "sensor_timeout_escalated"
            self.last_recovery_action = "estop"
            self._queue_alarm(
                "FATAL_FAULT",
                "sensor",
                "力传感器连续超时，已升级为急停",
                workflow_step="scan_monitor",
                auto_action="estop",
            )
        if current_stale_ms < timeout_ms:
            self.force_sensor_estop_alarm = False

    def _record_core_streams(self, ts_ns: int) -> None:
        if not self.recorders:
            return
        robot_payload = {
            "powered": self.powered,
            "operate_mode": self.operate_mode,
            "joint_pos": self.joint_pos,
            "joint_vel": self.joint_vel,
            "joint_torque": self.joint_torque,
            "cart_force": self.cart_force,
            "tcp_pose": self.tcp_pose,
        }
        contact_payload = {
            "mode": self.contact_mode,
            "confidence": self.contact_confidence,
            "pressure_current": self.pressure_current,
            "recommended_action": self.recommended_action,
            "contact_stable": self.contact_stable,
        }
        progress_payload = {
            "execution_state": self.execution_state.value,
            "active_segment": self.active_segment,
            "path_index": self.path_index,
            "progress_pct": self.progress_pct,
            "frame_id": self.frame_id,
        }
        self.recorders["robot_state"].append(robot_payload, source_ts_ns=ts_ns)
        self.recorders["contact_state"].append(contact_payload, source_ts_ns=ts_ns)
        self.recorders["scan_progress"].append(progress_payload, source_ts_ns=ts_ns)
        self.last_flush_ns = now_ns()

    def _open_recorders(self, session_dir: Path, session_id: str) -> None:
        core_root = ensure_dir(session_dir / "raw" / "core")
        self.recorders = {
            "robot_state": JsonlRecorder(core_root / "robot_state.jsonl", session_id),
            "contact_state": JsonlRecorder(core_root / "contact_state.jsonl", session_id),
            "scan_progress": JsonlRecorder(core_root / "scan_progress.jsonl", session_id),
            "alarm_event": JsonlRecorder(core_root / "alarm_event.jsonl", session_id),
        }

    def _queue_alarm(
        self,
        severity: str,
        source: str,
        message: str,
        *,
        workflow_step: str = "",
        request_id: str = "",
        auto_action: str = "",
    ) -> None:
        ts_ns = now_ns()
        alarm = {
            "severity": severity,
            "source": source,
            "message": message,
            "session_id": self.session_id,
            "segment_id": self.active_segment,
            "event_ts_ns": ts_ns,
            "workflow_step": workflow_step,
            "request_id": request_id,
            "auto_action": auto_action,
        }
        self.pending_alarms.append(alarm)
        recorder = self.recorders.get("alarm_event")
        if recorder is not None:
            recorder.append(alarm, source_ts_ns=ts_ns)
        self.last_controller_log = message
        if severity == "FATAL_FAULT":
            self.fault_code = source.upper()
            self.recovery_reason = source
            self.last_recovery_action = auto_action or severity.lower()
            self.execution_state = SystemState.FAULT if self.execution_state != SystemState.ESTOP else SystemState.ESTOP

    @staticmethod
    def _plan_hash(plan_payload: dict[str, Any]) -> str:
        import hashlib
        import json
        return hashlib.sha256(json.dumps(plan_payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    @staticmethod
    def _validate_scan_plan(plan_payload: dict[str, Any]) -> str:
        segments = list(plan_payload.get("segments") or [])
        if not segments:
            return "scan plan missing segments"
        if not isinstance(plan_payload.get("approach_pose"), dict) or not isinstance(plan_payload.get("retreat_pose"), dict):
            return "scan plan missing approach/retreat poses"
        previous_segment = 0
        for segment in segments:
            segment_id = int(segment.get("segment_id", 0) or 0)
            if segment_id <= 0:
                return "scan plan contains invalid segment id"
            if previous_segment and segment_id != previous_segment + 1:
                return "scan plan segment ids must be contiguous"
            previous_segment = segment_id
            waypoints = list(segment.get("waypoints") or [])
            if not waypoints:
                return f"segment {segment_id} has no waypoints"
        return ""


    @staticmethod
    def _device(connected: bool, health: str, detail: str) -> Dict[str, Any]:
        return {
            "connected": connected,
            "health": health,
            "detail": detail,
            "fresh": connected,
            "last_ts_ns": 0,
        }
