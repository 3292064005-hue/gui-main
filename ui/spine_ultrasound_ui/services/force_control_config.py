from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any


DEFAULT_FORCE_CONTROL_CONFIG = {
    "max_z_force_n": 35.0,
    "warning_z_force_n": 25.0,
    "max_xy_force_n": 20.0,
    "desired_contact_force_n": 10.0,
    "emergency_retract_mm": 50.0,
    "force_filter_cutoff_hz": 30.0,
    "sensor_timeout_ms": 500,
    "stale_telemetry_ms": 250,
    "force_settle_window_ms": 150,
    "resume_force_band_n": 1.5,
}


def force_control_config_path() -> Path:
    return Path(__file__).resolve().parents[2] / "configs" / "force_control.json"


@lru_cache(maxsize=1)
def load_force_control_config() -> dict[str, Any]:
    path = force_control_config_path()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return dict(DEFAULT_FORCE_CONTROL_CONFIG)
    except json.JSONDecodeError as exc:
        raise ValueError(f"invalid force_control.json: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError("force_control.json must contain a JSON object")
    merged = dict(DEFAULT_FORCE_CONTROL_CONFIG)
    merged.update(raw)
    return merged
