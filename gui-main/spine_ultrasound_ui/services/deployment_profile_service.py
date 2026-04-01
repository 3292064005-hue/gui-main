from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig

_PROFILE_ORDER = ("dev", "lab", "research", "clinical", "review")


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
        }


class DeploymentProfileService:
    def __init__(self, env: dict[str, str] | None = None) -> None:
        self._env = env if env is not None else dict(os.environ)

    def resolve(self, config: RuntimeConfig | None = None) -> DeploymentProfile:
        requested = str(self._env.get("SPINE_DEPLOYMENT_PROFILE") or self._env.get("SPINE_PROFILE") or "").strip().lower()
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
        if str(self._env.get("SPINE_READ_ONLY_MODE", "0")).lower() in {"1", "true", "yes", "on"}:
            return "review"
        if str(self._env.get("SPINE_LAB_MODE", "0")).lower() in {"1", "true", "yes", "on"}:
            return "lab"
        if str(self._env.get("SPINE_STRICT_CONTROL_AUTHORITY", "0")).lower() in {"1", "true", "yes", "on"}:
            return "clinical"
        if config is not None and getattr(config, "requires_single_control_source", False):
            return "research"
        return "dev"
