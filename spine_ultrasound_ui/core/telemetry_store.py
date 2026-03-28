from __future__ import annotations

from dataclasses import asdict
from typing import Any, Dict, Optional

from spine_ultrasound_ui.models import CoreStateSnapshot, DeviceHealth, RecorderStatus, RunMetrics, SafetyStatus, SystemState, TcpPose
from spine_ultrasound_ui.services.ipc_protocol import TelemetryEnvelope


class TelemetryStore:
    def __init__(self) -> None:
        self.core_state = CoreStateSnapshot(execution_state=SystemState.BOOT.value)
        self.safety_status = SafetyStatus()
        self.recorder_status = RecorderStatus()
        self.metrics = RunMetrics()
        self.devices: Dict[str, DeviceHealth] = {
            "robot": DeviceHealth(False, "offline", "等待控制器连接", False, 0),
            "camera": DeviceHealth(False, "offline", "等待摄像头连接", False, 0),
            "pressure": DeviceHealth(False, "offline", "等待压力传感器连接", False, 0),
            "ultrasound": DeviceHealth(False, "offline", "等待超声设备连接", False, 0),
        }
        self.robot = {
            "powered": False,
            "operate_mode": "manual",
            "armed": False,
            "fault_code": "",
            "session_id": "",
            "last_event": "-",
            "last_controller_log": "-",
        }
        self.topic_timestamps_ns: Dict[str, int] = {}

    def apply(self, env: TelemetryEnvelope) -> Optional[dict[str, Any]]:
        data = env.data
        self.topic_timestamps_ns[env.topic] = int(env.ts_ns or 0)
        if env.topic == "core_state":
            self.core_state = CoreStateSnapshot(
                execution_state=str(data.get("execution_state", self.core_state.execution_state)),
                armed=bool(data.get("armed", False)),
                fault_code=str(data.get("fault_code", "")),
                active_segment=int(data.get("active_segment", 0)),
                progress_pct=float(data.get("progress_pct", 0.0)),
                session_id=str(data.get("session_id", "")),
            )
            self.robot["armed"] = self.core_state.armed
            self.robot["fault_code"] = self.core_state.fault_code
            self.robot["session_id"] = self.core_state.session_id
            return None
        if env.topic == "robot_state":
            self.robot["powered"] = bool(data.get("powered", False))
            self.robot["operate_mode"] = str(data.get("operate_mode", "manual"))
            self.robot["last_event"] = str(data.get("last_event", "-"))
            self.robot["last_controller_log"] = str(data.get("last_controller_log", "-"))
            self.metrics.joint_pos = list(data.get("joint_pos", self.metrics.joint_pos))
            self.metrics.joint_vel = list(data.get("joint_vel", self.metrics.joint_vel))
            self.metrics.joint_torque = list(data.get("joint_torque", self.metrics.joint_torque))
            self.metrics.cart_force = list(data.get("cart_force", self.metrics.cart_force))
            pose = data.get("tcp_pose", {})
            if isinstance(pose, dict):
                self.metrics.tcp_pose = TcpPose(**{k: float(pose.get(k, 0.0)) for k in ["x", "y", "z", "rx", "ry", "rz"]})
            return None
        if env.topic == "contact_state":
            self.metrics.contact_mode = str(data.get("mode", self.metrics.contact_mode))
            self.metrics.contact_confidence = float(data.get("confidence", self.metrics.contact_confidence))
            self.metrics.pressure_current = float(data.get("pressure_current", self.metrics.pressure_current))
            self.metrics.pressure_error = self.metrics.pressure_current - self.metrics.pressure_target
            self.metrics.recommended_action = str(data.get("recommended_action", self.metrics.recommended_action))
            return None
        if env.topic == "scan_progress":
            self.metrics.segment_id = int(data.get("active_segment", self.metrics.segment_id))
            self.metrics.path_index = int(data.get("path_index", self.metrics.path_index))
            self.metrics.scan_progress = float(data.get("overall_progress", self.metrics.scan_progress))
            self.metrics.frame_id = int(data.get("frame_id", self.metrics.frame_id))
            return None
        if env.topic == "device_health":
            for name, raw in dict(data.get("devices", {})).items():
                self.devices[name] = DeviceHealth(
                    connected=bool(raw.get("connected", False)),
                    health=str(raw.get("health", "offline")),
                    detail=str(raw.get("detail", "")),
                    fresh=bool(raw.get("fresh", False)),
                    last_ts_ns=int(raw.get("last_ts_ns", 0)),
                )
            return None
        if env.topic == "safety_status":
            self.safety_status = SafetyStatus(
                safe_to_arm=bool(data.get("safe_to_arm", False)),
                safe_to_scan=bool(data.get("safe_to_scan", False)),
                active_interlocks=list(data.get("active_interlocks", [])),
            )
            return None
        if env.topic == "recording_status":
            self.recorder_status = RecorderStatus(
                session_id=str(data.get("session_id", "")),
                recording=bool(data.get("recording", False)),
                dropped_samples=int(data.get("dropped_samples", 0)),
                last_flush_ns=int(data.get("last_flush_ns", 0)),
            )
            return None
        if env.topic == "quality_feedback":
            self.metrics.image_quality = float(data.get("image_quality", self.metrics.image_quality))
            self.metrics.feature_confidence = float(data.get("feature_confidence", self.metrics.feature_confidence))
            self.metrics.quality_score = float(data.get("quality_score", self.metrics.quality_score))
            return None
        if env.topic == "alarm_event":
            return {
                "severity": str(data.get("severity", "WARN")),
                "source": str(data.get("source", "robot_core")),
                "message": str(data.get("message", "未知告警")),
                "session_id": str(data.get("session_id", "")),
                "segment_id": int(data.get("segment_id", 0)),
                "event_ts_ns": int(data.get("event_ts_ns", env.ts_ns or 0)),
                "workflow_step": str(data.get("workflow_step", "")),
                "request_id": str(data.get("request_id", "")),
                "auto_action": str(data.get("auto_action", "")),
            }
        return None

    def device_roster(self) -> dict[str, Any]:
        return {name: asdict(device) for name, device in self.devices.items()}
