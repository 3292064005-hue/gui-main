from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig

_PROFILE_ORDER = ("dev", "lab", "research", "clinical", "review")
_PROFILE_ALIASES = {"mock": "dev", "hil": "research", "prod": "clinical"}


@dataclass(frozen=True)
class DeploymentProfile:
    name: str
    allows_write_commands: bool
    requires_strict_control_authority: bool
    requires_session_evidence_seal: bool
    review_only: bool
    requires_api_token: bool
    allowed_write_roles: tuple[str, ...]
    description: str
    log_granularity: str = "standard"
    seal_strength: str = "standard"
    provenance_strength: str = "standard"
    requires_live_sdk: bool = False
    allows_lab_port: bool = True
    requires_hil_gate: bool = False
    research_sandbox_enabled: bool = False
    allowed_guidance_source_tiers: tuple[str, ...] = ("live", "replay", "simulated")
    allowed_force_source_tiers: tuple[str, ...] = ("live", "replay", "simulated")

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "allows_write_commands": self.allows_write_commands,
            "requires_strict_control_authority": self.requires_strict_control_authority,
            "requires_session_evidence_seal": self.requires_session_evidence_seal,
            "review_only": self.review_only,
            "requires_api_token": self.requires_api_token,
            "allowed_write_roles": list(self.allowed_write_roles),
            "description": self.description,
            "log_granularity": self.log_granularity,
            "seal_strength": self.seal_strength,
            "provenance_strength": self.provenance_strength,
            "requires_live_sdk": self.requires_live_sdk,
            "allows_lab_port": self.allows_lab_port,
            "requires_hil_gate": self.requires_hil_gate,
            "research_sandbox_enabled": self.research_sandbox_enabled,
            "allowed_guidance_source_tiers": list(self.allowed_guidance_source_tiers),
            "allowed_force_source_tiers": list(self.allowed_force_source_tiers),
        }


class DeploymentProfileService:
    def __init__(self, env: dict[str, str] | None = None) -> None:
        self._env = env if env is not None else dict(os.environ)

    @staticmethod
    def normalize_profile_name(name: str) -> str:
        """Normalize profile names to the canonical deployment matrix.

        Args:
            name: Raw profile token from environment variables, scripts, or
                acceptance artifacts.

        Returns:
            Canonical profile name when the token is recognized. Legacy aliases
            are mapped as follows: ``mock -> dev``, ``hil -> research``, and
            ``prod -> clinical``. Unknown values are returned as lowercase text
            so callers can decide whether to reject or ignore them.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Empty input returns an empty string.
        """
        token = str(name or "").strip().lower()
        return _PROFILE_ALIASES.get(token, token)

    def resolve(self, config: RuntimeConfig | None = None) -> DeploymentProfile:
        requested = self.normalize_profile_name(self._env.get("SPINE_DEPLOYMENT_PROFILE") or self._env.get("SPINE_PROFILE") or "")
        if requested not in _PROFILE_ORDER:
            requested = self._infer_profile(config)
        if requested == "clinical":
            return DeploymentProfile(
                "clinical",
                True,
                True,
                True,
                False,
                True,
                ("operator", "service"),
                "Clinical execution profile with strict control ownership, token-gated writes and sealed session evidence.",
                log_granularity="audit",
                seal_strength="strict",
                provenance_strength="strict",
                requires_live_sdk=True,
                allows_lab_port=False,
                requires_hil_gate=True,
                research_sandbox_enabled=False,
                allowed_guidance_source_tiers=("live",),
                allowed_force_source_tiers=("live",),
            )
        if requested == "research":
            return DeploymentProfile(
                "research",
                True,
                True,
                True,
                False,
                False,
                ("operator", "researcher", "service"),
                "Research execution profile with writable runtime, strict control authority and evidence capture enabled.",
                log_granularity="verbose",
                seal_strength="strong",
                provenance_strength="strong",
                requires_live_sdk=True,
                allows_lab_port=True,
                requires_hil_gate=True,
                research_sandbox_enabled=True,
                allowed_guidance_source_tiers=("live",),
                allowed_force_source_tiers=("live",),
            )
        if requested == "lab":
            return DeploymentProfile(
                "lab",
                True,
                True,
                True,
                False,
                False,
                ("operator", "qa", "service"),
                "Lab bring-up profile for controlled hardware rehearsal, mock/live boundary validation and diagnostic evidence capture.",
                log_granularity="verbose",
                seal_strength="strong",
                provenance_strength="strong",
                requires_live_sdk=False,
                allows_lab_port=True,
                requires_hil_gate=False,
                research_sandbox_enabled=True,
                allowed_guidance_source_tiers=("live", "replay"),
                allowed_force_source_tiers=("live", "replay", "simulated"),
            )
        if requested == "review":
            return DeploymentProfile(
                "review",
                False,
                False,
                True,
                True,
                False,
                tuple(),
                "Read-only review profile for replay, QA and exported evidence inspection.",
                log_granularity="audit",
                seal_strength="strict",
                provenance_strength="strict",
                requires_live_sdk=False,
                allows_lab_port=True,
                requires_hil_gate=False,
                research_sandbox_enabled=False,
                allowed_guidance_source_tiers=("live", "replay", "simulated"),
                allowed_force_source_tiers=("live", "replay", "simulated"),
            )
        return DeploymentProfile(
            "dev",
            True,
            False,
            False,
            False,
            False,
            ("operator", "researcher", "qa", "service"),
            "Development profile optimized for local iteration and mock/runtime debugging.",
            log_granularity="debug",
            seal_strength="relaxed",
            provenance_strength="standard",
            requires_live_sdk=False,
            allows_lab_port=True,
            requires_hil_gate=False,
            research_sandbox_enabled=True,
            allowed_guidance_source_tiers=("live", "replay", "simulated"),
            allowed_force_source_tiers=("live", "replay", "simulated"),
        )

    def build_snapshot(self, config: RuntimeConfig | None = None) -> dict[str, Any]:
        profile = self.resolve(config)
        return {
            **profile.to_dict(),
            "profile_matrix": list(_PROFILE_ORDER),
            "env_overrides": {
                "SPINE_DEPLOYMENT_PROFILE": self._env.get("SPINE_DEPLOYMENT_PROFILE", ""),
                "SPINE_READ_ONLY_MODE": self._env.get("SPINE_READ_ONLY_MODE", ""),
                "SPINE_STRICT_CONTROL_AUTHORITY": self._env.get("SPINE_STRICT_CONTROL_AUTHORITY", ""),
                "SPINE_API_TOKEN": "set" if self._env.get("SPINE_API_TOKEN") else "",
            },
        }

    def _infer_profile(self, config: RuntimeConfig | None) -> str:
        """Infer a deployment profile from explicit environment intent only.

        Args:
            config: Optional runtime configuration. It is intentionally *not*
                used to auto-escalate into research/clinical profiles because
                safety-critical deployment mode must be an operator or launcher
                decision, not an incidental consequence of runtime defaults.

        Returns:
            Resolved fallback profile name.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            - ``SPINE_READ_ONLY_MODE`` forces ``review``.
            - ``SPINE_LAB_MODE`` forces ``lab``.
            - ``SPINE_STRICT_CONTROL_AUTHORITY`` forces ``clinical``.
            - Absent explicit deployment intent, the system stays in ``dev`` so
              local development does not silently inherit research-grade gates.
        """
        if str(self._env.get("SPINE_READ_ONLY_MODE", "0")).lower() in {"1", "true", "yes", "on"}:
            return "review"
        if str(self._env.get("SPINE_LAB_MODE", "0")).lower() in {"1", "true", "yes", "on"}:
            return "lab"
        if str(self._env.get("SPINE_STRICT_CONTROL_AUTHORITY", "0")).lower() in {"1", "true", "yes", "on"}:
            return "clinical"
        if str(self._env.get("SPINE_RESEARCH_MODE", "0")).lower() in {"1", "true", "yes", "on"}:
            return "research"
        return "dev"
