from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.core import AppController
from spine_ultrasound_ui.main_window import MainWindow
from spine_ultrasound_ui.services import MockBackend, RobotCoreClientBackend


def build_backend(mode: str, root_dir: Path):
    if mode == "core":
        host = os.getenv("ROBOT_CORE_HOST", "127.0.0.1")
        command_port = int(os.getenv("ROBOT_CORE_COMMAND_PORT", "5656"))
        telemetry_port = int(os.getenv("ROBOT_CORE_TELEMETRY_PORT", "5657"))
        return RobotCoreClientBackend(root_dir, command_host=host, command_port=command_port, telemetry_host=host, telemetry_port=telemetry_port)
    return MockBackend(root_dir)


def main() -> None:
    parser = argparse.ArgumentParser(description="Spine Ultrasound Platform")
    parser.add_argument("--backend", choices=["mock", "core"], default=os.getenv("SPINE_UI_BACKEND", "mock"))
    parser.add_argument("--workspace", default=str(Path.cwd() / "data"))
    args, _ = parser.parse_known_args()

    app = QApplication(sys.argv)
    app.setApplicationName("Spine Ultrasound Platform")
    app.setOrganizationName("OpenAI")
    root_dir = Path(args.workspace)
    backend = build_backend(args.backend, root_dir)
    controller = AppController(root_dir, backend)
    app.aboutToQuit.connect(controller.shutdown)
    window = MainWindow(controller)
    window.show()
    controller.start()
    sys.exit(app.exec())
