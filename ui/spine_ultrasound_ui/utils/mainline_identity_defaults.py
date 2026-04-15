from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class MainlineIdentityDefaults:
    family_key: str = "xmate3_cobot_6"
    robot_model: str = "xmate3"
    display_name: str = "xMate3"
    sdk_robot_class: str = "xMateRobot"
    axis_count: int = 6
    controller_family: str = "xCore"
    controller_version: str = "v2.1+"
    preferred_link: str = "wired_direct"
    clinical_mainline_mode: str = "cartesianImpedance"


def _load_registry() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[2] / "configs" / "robot_identity_mainline.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        data = {}
    return data if isinstance(data, dict) else {}


def load_mainline_identity_defaults() -> MainlineIdentityDefaults:
    data = _load_registry()

    def _string(key: str, default: str) -> str:
        value = data.get(key, default)
        return str(value) if value not in (None, "") else default

    def _integer(key: str, default: int) -> int:
        try:
            return int(data.get(key, default))
        except Exception:
            return int(default)

    return MainlineIdentityDefaults(
        family_key=_string("family_key", MainlineIdentityDefaults.family_key),
        robot_model=_string("robot_model", MainlineIdentityDefaults.robot_model),
        display_name=_string("display_name", MainlineIdentityDefaults.display_name),
        sdk_robot_class=_string("sdk_robot_class", MainlineIdentityDefaults.sdk_robot_class),
        axis_count=_integer("axis_count", MainlineIdentityDefaults.axis_count),
        controller_family=_string("controller_family", MainlineIdentityDefaults.controller_family),
        controller_version=_string("controller_version", MainlineIdentityDefaults.controller_version),
        preferred_link=_string("preferred_link", MainlineIdentityDefaults.preferred_link),
        clinical_mainline_mode=_string("clinical_mainline_mode", MainlineIdentityDefaults.clinical_mainline_mode),
    )


MAINLINE_IDENTITY_DEFAULTS = load_mainline_identity_defaults()
