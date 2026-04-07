from __future__ import annotations

import re
from pathlib import Path


def test_status_presenters_only_reference_known_main_window_attributes() -> None:
    presenter_dir = Path(__file__).resolve().parents[1] / "spine_ultrasound_ui" / "views" / "status_presenters"
    referenced = set()
    for path in presenter_dir.glob("*.py"):
        text = path.read_text(encoding="utf-8")
        referenced.update(re.findall(r"window\.([A-Za-z_][A-Za-z0-9_]*)", text))

    assert referenced == {
        "_readiness_state",
        "_set_badge_state",
        "_system_state_kind",
        "assessment_page",
        "backend",
        "card_exp",
        "card_pose",
        "card_pressure",
        "card_quality",
        "card_readiness",
        "card_result",
        "card_state",
        "exp_id_label",
        "header_exp_pill",
        "header_mode_pill",
        "header_state_pill",
        "header_step_pill",
        "overview_page",
        "prepare_page",
        "readiness_label",
        "replay_page",
        "robot_monitor_page",
        "scan_page",
        "settings_page",
        "system_state_label",
        "vision_page",
    }
