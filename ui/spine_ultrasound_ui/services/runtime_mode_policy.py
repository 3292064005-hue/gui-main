from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService

_DESKTOP_ALLOWED = {
    "dev": frozenset({"mock", "core", "api"}),
    "lab": frozenset({"core", "api"}),
    "research": frozenset({"core", "api"}),
    "clinical": frozenset({"core", "api"}),
    "review": frozenset({"core", "api"}),
}
_HEADLESS_ALLOWED = {
    "dev": frozenset({"mock", "core"}),
    "lab": frozenset({"core"}),
    "research": frozenset({"core"}),
    "clinical": frozenset({"core"}),
    "review": frozenset({"mock", "core"}),
}
_DEFAULT_BY_SURFACE = {
    "desktop": {
        "dev": "mock",
        "lab": "core",
        "research": "core",
        "clinical": "core",
        "review": "api",
    },
    "headless": {
        "dev": "mock",
        "lab": "core",
        "research": "core",
        "clinical": "core",
        "review": "core",
    },
}


@dataclass(frozen=True)
class RuntimeModeDecision:
    mode: str
    profile_name: str
    allowed_modes: tuple[str, ...]
    surface: str
    resolution_source: str
    requires_live_sdk: bool
    review_only: bool

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "profile_name": self.profile_name,
            "allowed_modes": list(self.allowed_modes),
            "surface": self.surface,
            "resolution_source": self.resolution_source,
            "requires_live_sdk": self.requires_live_sdk,
            "review_only": self.review_only,
        }


def _allowed_modes(*, surface: str, profile_name: str) -> tuple[str, ...]:
    if surface == "desktop":
        modes = _DESKTOP_ALLOWED.get(profile_name, _DESKTOP_ALLOWED["dev"])
    elif surface == "headless":
        modes = _HEADLESS_ALLOWED.get(profile_name, _HEADLESS_ALLOWED["dev"])
    else:
        raise ValueError(f"unsupported runtime surface: {surface}")
    return tuple(sorted(modes))


def _normalize_mode(value: str | None) -> str:
    return str(value or "").strip().lower()


def resolve_runtime_mode(
    *,
    explicit_mode: str | None,
    surface: str,
    config: RuntimeConfig | None = None,
    env: Mapping[str, str] | None = None,
) -> RuntimeModeDecision:
    """Resolve and validate the runtime backend mode for a surface.

    Args:
        explicit_mode: Mode supplied by the caller, CLI, or settings override.
        surface: Runtime surface identifier. Supported values are ``desktop`` and
            ``headless``.
        config: Optional runtime config used only for deployment-profile
            resolution.
        env: Optional environment mapping.

    Returns:
        Resolved, profile-validated backend decision.

    Raises:
        ValueError: Raised when the mode is unknown or disallowed for the
            resolved deployment profile.

    Boundary behaviour:
        - When no explicit mode is provided, the resolver chooses a documented
          default based on deployment profile and runtime surface.
        - Research and clinical surfaces do not silently fall back to mock;
          callers must run a live backend that matches the intended control
          plane.
        - Review headless defaults to ``core``; explicit ``mock`` is only for
          read-only evidence / replay / contract inspection flows.
    """
    source = dict(env if env is not None else os.environ)
    profile = DeploymentProfileService(source).resolve(config)
    normalized = _normalize_mode(explicit_mode)
    if normalized:
        resolution_source = "explicit"
    else:
        env_candidates = [source.get("SPINE_HEADLESS_BACKEND")] if surface == "headless" else [source.get("SPINE_UI_BACKEND")]
        normalized = next((value for value in (_normalize_mode(item) for item in env_candidates) if value), "")
        resolution_source = "environment" if normalized else "profile_default"
    if not normalized:
        normalized = _DEFAULT_BY_SURFACE[surface].get(profile.name, _DEFAULT_BY_SURFACE[surface]["dev"])
    allowed_modes = _allowed_modes(surface=surface, profile_name=profile.name)
    if normalized not in {"mock", "core", "api"}:
        raise ValueError(f"unsupported backend mode: {normalized or '<empty>'}")
    if normalized not in allowed_modes:
        allowed_csv = ", ".join(allowed_modes)
        raise ValueError(
            f"deployment profile '{profile.name}' on {surface} runtime only allows backend modes: {allowed_csv}; got '{normalized}'"
        )
    return RuntimeModeDecision(
        mode=normalized,
        profile_name=profile.name,
        allowed_modes=allowed_modes,
        surface=surface,
        resolution_source=resolution_source,
        requires_live_sdk=bool(profile.requires_live_sdk),
        review_only=bool(profile.review_only),
    )
