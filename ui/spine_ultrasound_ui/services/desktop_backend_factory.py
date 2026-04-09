from __future__ import annotations

from spine_ultrasound_ui.services.api_bridge_backend import ApiBridgeBackend
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.services.robot_core_client import RobotCoreClientBackend


class DesktopBackendFactory:
    @staticmethod
    def build(settings):
        if settings.backend_mode == "core":
            return RobotCoreClientBackend(settings.workspace_root, command_host=settings.robot_core_host, command_port=settings.robot_core_command_port, telemetry_host=settings.robot_core_host, telemetry_port=settings.robot_core_telemetry_port)
        if settings.backend_mode == "api":
            return ApiBridgeBackend(settings.workspace_root, base_url=settings.api_base_url, deployment_profile=settings.deployment_profile)
        return MockBackend(settings.workspace_root)
