from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend


def test_app_controller_emits_control_plane_and_profile(tmp_path: Path) -> None:
    backend = MockBackend(tmp_path)
    controller = AppController(tmp_path, backend)
    payloads: list[dict] = []
    controller.status_updated.connect(lambda payload: payloads.append(payload))
    controller.start()
    assert payloads
    payload = payloads[-1]
    assert "control_plane_snapshot" in payload
    assert "deployment_profile" in payload
    assert payload["control_plane_snapshot"]["summary_state"] in {"ready", "degraded", "blocked"}
