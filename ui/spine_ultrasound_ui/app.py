from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.bootstrap import DesktopRuntimeSettings, build_controller
from spine_ultrasound_ui.main_window import MainWindow


def main() -> None:
    parser = argparse.ArgumentParser(description="Spine Ultrasound Platform")
    parser.add_argument("--backend", choices=["mock", "core", "api"], default=None)
    parser.add_argument("--workspace", default=str(Path.cwd() / "data"))
    parser.add_argument("--api-base-url", default=os.getenv("SPINE_API_BASE_URL", "http://127.0.0.1:8000"))
    args, _ = parser.parse_known_args()

    settings = DesktopRuntimeSettings.from_sources(
        backend_mode=args.backend,
        workspace_root=Path(args.workspace),
        api_base_url=args.api_base_url,
    )

    app = QApplication(sys.argv)
    app.setApplicationName("Spine Ultrasound Platform")
    app.setOrganizationName("OpenAI")
    controller = build_controller(settings)
    app.aboutToQuit.connect(controller.shutdown)
    window = MainWindow(controller)
    window.show()
    controller.start()
    sys.exit(app.exec())
