from __future__ import annotations

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.desktop_backend_factory import DesktopBackendFactory


class DesktopControllerFactory:
    @staticmethod
    def build(settings) -> AppController:
        backend = DesktopBackendFactory.build(settings)
        return AppController(settings.workspace_root, backend)
