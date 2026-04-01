from __future__ import annotations

import json
import os
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.contracts import schema_catalog
from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.event_bus import EventBus
from spine_ultrasound_ui.services.mock_backend import MockBackend


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_event_bus_delivers_latest_value():
    bus = EventBus()
    sub = bus.subscribe({"core_state"})
    bus.publish({"topic": "core_state", "data": {"execution_state": "AUTO_READY"}})
    assert sub.get(timeout=0.1)["data"]["execution_state"] == "AUTO_READY"
    bus.unsubscribe(sub)


def test_schema_catalog_includes_runtime_and_session_schemas():
    catalog = schema_catalog()
    assert "runtime/command_v1.schema.json" in catalog
    assert "session/lineage.schema.json" in catalog


def test_session_intelligence_artifacts_are_materialized(tmp_path):
    _app()
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    controller.connect_robot()
    controller.power_on()
    controller.set_auto_mode()
    controller.create_experiment()
    controller.run_localization()
    controller.generate_path()
    controller.start_scan()
    controller.pause_scan()
    controller.resume_scan()
    controller.safe_retreat()
    controller.save_results()
    controller.export_summary()

    session_dir = controller.session_service.current_session_dir
    assert session_dir is not None
    lineage = json.loads((session_dir / "meta" / "lineage.json").read_text(encoding="utf-8"))
    resume_state = json.loads((session_dir / "meta" / "resume_state.json").read_text(encoding="utf-8"))
    recovery_report = json.loads((session_dir / "export" / "recovery_report.json").read_text(encoding="utf-8"))
    incidents = json.loads((session_dir / "derived" / "incidents" / "session_incidents.json").read_text(encoding="utf-8"))
    resume_decision = json.loads((session_dir / "meta" / "resume_decision.json").read_text(encoding="utf-8"))
    manifest = json.loads((session_dir / "meta" / "manifest.json").read_text(encoding="utf-8"))

    assert lineage["lineage"][0]["kind"] == "registration"
    assert resume_state["plan_hash"] == manifest["scan_plan_hash"]
    assert "summary" in recovery_report
    assert incidents["summary"]["count"] >= 0
    assert "resume_allowed" in resume_decision
    assert manifest["artifacts"]["lineage"] == "meta/lineage.json"
    assert manifest["artifacts"]["resume_state"] == "meta/resume_state.json"
    assert manifest["artifacts"]["resume_decision"] == "meta/resume_decision.json"
    assert manifest["artifacts"]["recovery_report"] == "export/recovery_report.json"
    assert manifest["artifacts"]["session_incidents"] == "derived/incidents/session_incidents.json"
