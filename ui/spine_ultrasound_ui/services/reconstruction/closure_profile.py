from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.training.specs.common import load_structured_config


_REPO_ROOT = Path(__file__).resolve().parents[3]
_PROFILE_DIR = _REPO_ROOT / "configs" / "profiles"

_DEFAULT_PROFILE: dict[str, Any] = {
    "profile_name": "weighted_runtime",
    "profile_release_state": "research_validated",
    "closure_mode": "runtime_optional",
    "selection_policy": {
        "authoritative_only": False,
        "allow_quality_only": True,
        "allow_all_rows_fallback": True,
    },
    "runtime": {
        "frame_anatomy_runtime_config": "configs/models/frame_anatomy_keypoint_runtime.yaml",
    },
    "thresholds": {
        "min_reconstruction_points": 4,
        "min_cobb_curve_points": 4,
    },
    "closure_policy": {
        "measured_only": False,
        "hard_blockers": [
            "no_reconstructable_rows",
            "selection_empty",
            "no_frame_level_anatomy_points",
            "insufficient_curve_points_for_cobb",
        ],
        "contamination_reasons": [
            "registration_prior_curve_used",
            "curve_window_fallback_used",
        ],
        "blocked_reconstruction_sources": [],
        "blocked_measurement_sources": [],
    },
}


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    """Recursively merge profile dictionaries without mutating either input."""
    merged = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge(dict(merged[key]), value)
        else:
            merged[key] = value
    return merged


def _resolve_profile_path(requested: str) -> Path:
    """Resolve a profile name or config path into a concrete filesystem path."""
    raw = requested.strip()
    candidate = Path(raw)
    if candidate.is_absolute() or candidate.suffix.lower() in {".json", ".yaml", ".yml"}:
        return candidate if candidate.is_absolute() else (_REPO_ROOT / candidate)
    for suffix in (".json", ".yaml", ".yml"):
        path = _PROFILE_DIR / f"{raw}{suffix}"
        if path.exists():
            return path
    return _PROFILE_DIR / f"{raw}.json"


def load_reconstruction_profile(requested: str | None = None) -> dict[str, Any]:
    """Load the active reconstruction/assessment closure profile.

    Args:
        requested: Optional profile name or explicit config path. When omitted,
            the ``SPINE_RECONSTRUCTION_PROFILE`` environment variable is used,
            then the repository default ``weighted_runtime``.

    Returns:
        Fully merged profile payload with repository defaults applied.

    Raises:
        No exceptions are raised. Invalid or missing profile files fall back to
        repository defaults so callers can degrade explicitly.

    Boundary behaviour:
        Relative runtime-config paths are resolved against the repository root to
        keep profile activation stable across CLI, tests, and UI entry points.
        When loading fails, the returned profile carries ``profile_load_error``
        metadata so downstream reports can surface the degraded configuration
        state without aborting the runtime path.
    """
    raw = str(requested or os.environ.get("SPINE_RECONSTRUCTION_PROFILE") or "weighted_runtime").strip()
    path = _resolve_profile_path(raw)
    payload: dict[str, Any] = {}
    load_error = ""
    if path.exists():
        try:
            payload = load_structured_config(path)
        except Exception as exc:  # pragma: no cover - exercised via regression tests
            payload = {}
            load_error = f"{type(exc).__name__}: {exc}"
    else:
        load_error = f"profile_not_found:{path}"
    profile = _deep_merge(_DEFAULT_PROFILE, payload)
    profile["profile_name"] = str(payload.get("profile_name") or _DEFAULT_PROFILE["profile_name"])
    profile["requested_profile"] = raw
    profile["profile_config_path"] = str(path)
    profile["profile_load_error"] = load_error
    profile["profile_config_resolved"] = bool(path.exists() and not load_error)
    runtime = dict(profile.get("runtime", {}) or {})
    runtime_config = str(runtime.get("frame_anatomy_runtime_config", "") or "")
    if runtime_config:
        runtime_path = Path(runtime_config)
        runtime["frame_anatomy_runtime_config"] = str(runtime_path if runtime_path.is_absolute() else (_REPO_ROOT / runtime_path).resolve())
    profile["runtime"] = runtime
    return profile


def profile_name(profile: dict[str, Any]) -> str:
    """Return the normalized profile identifier used in runtime artifacts."""
    return str(profile.get("profile_name", "weighted_runtime") or "weighted_runtime")


def is_preweight_profile(profile: dict[str, Any]) -> bool:
    """Return whether the supplied profile enforces measured-only closure."""
    return bool(dict(profile.get("closure_policy", {}) or {}).get("measured_only", False))
