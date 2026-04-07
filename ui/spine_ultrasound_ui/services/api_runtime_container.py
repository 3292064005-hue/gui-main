from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.services.api_command_guard import ApiCommandGuardService
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter


@dataclass
class ApiRuntimeContainer:
    deployment_profile_service: DeploymentProfileService
    command_guard_service: ApiCommandGuardService
    runtime_adapter: HeadlessAdapter

    @classmethod
    def build(cls, *, settings: Any, env: dict[str, str] | None = None) -> "ApiRuntimeContainer":
        deployment_service = DeploymentProfileService(env)
        command_guard_service = ApiCommandGuardService(deployment_service, env)
        runtime_adapter = HeadlessAdapter(mode=settings.backend_mode, command_host=settings.command_host, command_port=settings.command_port, telemetry_host=settings.telemetry_host, telemetry_port=settings.telemetry_port)
        return cls(deployment_profile_service=deployment_service, command_guard_service=command_guard_service, runtime_adapter=runtime_adapter)
