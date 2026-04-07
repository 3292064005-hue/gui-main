from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.desktop_backend_factory import DesktopBackendFactory
from spine_ultrasound_ui.services.runtime_mode_policy import resolve_runtime_mode
from spine_ultrasound_ui.services.desktop_controller_factory import DesktopControllerFactory


@dataclass(frozen=True)
class DesktopRuntimeSettings:
    backend_mode: str
    workspace_root: Path
    api_base_url: str
    robot_core_host: str
    robot_core_command_port: int
    robot_core_telemetry_port: int
    deployment_profile: str
    backend_resolution_source: str
    allowed_backend_modes: tuple[str, ...]

    @classmethod
    def from_sources(cls, *, backend_mode: str | None, workspace_root: Path, api_base_url: str | None = None) -> "DesktopRuntimeSettings":
        """Resolve desktop runtime settings from explicit sources and profile policy.

        Args:
            backend_mode: Optional desktop backend override from CLI or caller.
            workspace_root: Workspace root used by the desktop controller.
            api_base_url: Optional API base URL override.

        Returns:
            Profile-validated desktop runtime settings.

        Raises:
            ValueError: Raised when the requested backend mode is incompatible
                with the resolved deployment profile.
        """
        decision = resolve_runtime_mode(explicit_mode=backend_mode, surface="desktop")
        return cls(
            backend_mode=decision.mode,
            workspace_root=workspace_root,
            api_base_url=api_base_url or os.getenv("SPINE_API_BASE_URL", "http://127.0.0.1:8000"),
            robot_core_host=os.getenv("ROBOT_CORE_HOST", "127.0.0.1"),
            robot_core_command_port=int(os.getenv("ROBOT_CORE_COMMAND_PORT", "5656")),
            robot_core_telemetry_port=int(os.getenv("ROBOT_CORE_TELEMETRY_PORT", "5657")),
            deployment_profile=decision.profile_name,
            backend_resolution_source=decision.resolution_source,
            allowed_backend_modes=decision.allowed_modes,
        )


def build_backend(settings: DesktopRuntimeSettings):
    return DesktopBackendFactory.build(settings)


def build_controller(settings: DesktopRuntimeSettings) -> AppController:
    return DesktopControllerFactory.build(settings)
