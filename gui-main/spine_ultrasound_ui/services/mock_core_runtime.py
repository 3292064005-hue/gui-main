from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Optional

from spine_ultrasound_ui.core.session_recorders import JsonlRecorder
from spine_ultrasound_ui.models import RuntimeConfig, SystemState
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.force_control_config import load_force_control_config
from spine_ultrasound_ui.services.mainline_task_tree_service import MainlineTaskTreeService
from spine_ultrasound_ui.services.mock_runtime.command_adapter import MockRuntimeCommandAdapterMixin
from spine_ultrasound_ui.services.mock_runtime.contract_surface import MockRuntimeContractSurfaceMixin
from spine_ultrasound_ui.services.mock_runtime.scenario_engine import MockRuntimeScenarioEngineMixin
from spine_ultrasound_ui.services.pressure_sensor_service import ForceSensorProvider, create_force_sensor_provider
from spine_ultrasound_ui.services.robot_family_registry_service import RobotFamilyRegistryService
from spine_ultrasound_ui.services.robot_identity_service import RobotIdentityService
from spine_ultrasound_ui.services.sdk_capability_service import SdkCapabilityService
from spine_ultrasound_ui.services.xmate_model_service import XMateModelService


class MockCoreRuntime(
    MockRuntimeScenarioEngineMixin,
    MockRuntimeContractSurfaceMixin,
    MockRuntimeCommandAdapterMixin,
):
    """State-owning mock runtime façade.

    The runtime keeps external construction and public method names stable while
    delegating scenario evolution, contract surface generation, and command
    handling to dedicated helper mixins under ``services/mock_runtime``.
    """

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
        self.locked_runtime_config_hash = ""
        self.locked_sdk_boundary_hash = ""
        self.locked_executor_hash = ""
        self.recovery_reason = ""
        self.last_recovery_action = ""
        self.image_quality = 0.82
        self.feature_confidence = 0.76
        self.quality_score = 0.79
        self.last_event = "-"
        self.last_controller_log = "-"
        self.controller_logs: list[dict[str, Any]] = [
            {"level": "INFO", "message": "mock runtime booted", "source": "runtime"},
        ]
        self.rl_projects: list[dict[str, Any]] = [
            {"name": "spine_mainline", "tasks": ["scan", "prep", "retreat"]},
            {"name": "spine_research", "tasks": ["sweep", "contact_probe"]},
        ]
        self.rl_status = {"loaded_project": "", "loaded_task": "", "running": False, "rate": 1.0, "loop": False}
        self.path_library: list[dict[str, Any]] = [
            {"name": "spine_demo_path", "rate": 0.5, "points": 128},
            {"name": "thoracic_followup", "rate": 0.4, "points": 92},
        ]
        self.drag_state = {"enabled": False, "space": "cartesian", "type": "admittance"}
        self.io_state = {
            "di": {"board0_port0": False, "board0_port1": True},
            "do": {"board0_port0": False, "board0_port1": False},
            "ai": {"board0_port0": 0.12},
            "ao": {"board0_port0": 0.0},
            "registers": {"spine.session.segment": 0, "spine.session.frame": 0},
        }
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
            "robot": self._device(False, "offline", "xMate3 控制器未连接"),
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
        self.model_service = XMateModelService()
        self.mainline_task_tree = MainlineTaskTreeService()
        self.identity_service = RobotIdentityService()
        self.family_registry = RobotFamilyRegistryService(self.identity_service)
        self.deployment_profiles = DeploymentProfileService({"SPINE_LAB_MODE": "1"})
        self.clinical_config_service = ClinicalConfigService()
        self.capability_service = SdkCapabilityService()
        self.last_final_verdict: dict[str, Any] = {}
        self.session_locked_ts_ns = 0
        self.locked_scan_plan_hash = ""
        self.injected_faults: set[str] = set()

    def update_runtime_config(self, config: RuntimeConfig) -> None:
        """Update the runtime configuration and refresh force-sensor bindings.

        Args:
            config: Incoming runtime configuration snapshot.

        Returns:
            None.
        """
        self.config = config
        self.force_sensor_provider_name = config.force_sensor_provider
        self.force_sensor_provider = create_force_sensor_provider(config.force_sensor_provider)
        self._append_controller_log(
            "INFO",
            f"runtime config updated: rt_mode={config.rt_mode}, collision={config.collision_detection_enabled}, soft_limit={config.soft_limit_enabled}",
        )
