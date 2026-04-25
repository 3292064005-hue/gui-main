from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService


_FORCE_LIVE_PROVIDERS = {"rokae_force_sensor", "xcore_force_sensor", "live_force_sensor", "hardware_force_sensor"}
_CAMERA_LIVE_MODES = {"live", "opencv_camera", "webcam"}
_CAMERA_REPLAY_MODES = {"filesystem", "replay"}
_CAMERA_SIM_MODES = {"synthetic"}


@dataclass(frozen=True)
class RuntimeSourcePolicySnapshot:
    deployment_profile: str
    force_source_tier: str
    camera_source_tier: str
    guidance_source_type: str
    shell_write_tier: str
    execution_write_ready: bool
    session_lock_ready: bool
    preview_ready: bool
    blockers: tuple[str, ...]
    warnings: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "deployment_profile": self.deployment_profile,
            "force_source_tier": self.force_source_tier,
            "camera_source_tier": self.camera_source_tier,
            "guidance_source_type": self.guidance_source_type,
            "shell_write_tier": self.shell_write_tier,
            "execution_write_ready": self.execution_write_ready,
            "session_lock_ready": self.session_lock_ready,
            "preview_ready": self.preview_ready,
            "blockers": list(self.blockers),
            "warnings": list(self.warnings),
        }


class RuntimeSourcePolicyService:
    """Resolve deployment-profile source boundaries for preview, lock, and execution.

    The service hard-separates development/simulation sources from research and
    clinical execution surfaces. Callers should use this service rather than
    duplicating profile checks in UI, workflow, or readiness code.
    """

    def __init__(self, env: dict[str, str] | None = None) -> None:
        self._env = env if env is not None else dict(os.environ)
        self._profiles = DeploymentProfileService(self._env)

    @staticmethod
    def classify_force_source(provider: str) -> str:
        normalized = str(provider or "").strip().lower()
        if not normalized:
            return "unknown"
        if normalized in {"mock", "mock_force_sensor", "simulated_force_sensor"}:
            return "simulated"
        if normalized in _FORCE_LIVE_PROVIDERS or "rokae" in normalized or "xcore" in normalized:
            return "live"
        if "replay" in normalized or "recorded" in normalized:
            return "replay"
        return "unknown"

    @staticmethod
    def classify_camera_source(mode: str) -> str:
        normalized = str(mode or "").strip().lower()
        if normalized in _CAMERA_LIVE_MODES:
            return "live"
        if normalized in _CAMERA_REPLAY_MODES:
            return "replay"
        if normalized in _CAMERA_SIM_MODES:
            return "simulated"
        return "unknown"

    @staticmethod
    def guidance_source_tier(source_type: str) -> str:
        normalized = str(source_type or "").strip().lower()
        if normalized in {"camera_only", "hybrid", "camera_backed", "live_camera"}:
            return "live"
        if normalized in {"filesystem", "replay", "recorded"}:
            return "replay"
        if normalized in {"fallback_simulated", "synthetic", "ultrasound_only"}:
            return "simulated"
        return "unknown"

    def build_snapshot(
        self,
        *,
        config: RuntimeConfig,
        guidance_source_type: str = "",
        provider_mode: str = "",
    ) -> RuntimeSourcePolicySnapshot:
        profile = self._profiles.resolve(config)
        force_tier = self.classify_force_source(getattr(config, 'force_sensor_provider', ''))
        camera_mode = provider_mode or getattr(config, 'camera_guidance_input_mode', '')
        camera_tier = self.classify_camera_source(camera_mode)
        guidance_tier = self.guidance_source_tier(guidance_source_type) if guidance_source_type else camera_tier
        shell_write_tier = 'contract_shell_forbidden'

        blockers: list[str] = []
        warnings: list[str] = []
        preview_ready = True
        session_lock_ready = True
        execution_write_ready = not profile.review_only

        if guidance_tier not in set(profile.allowed_guidance_source_tiers):
            if profile.name == 'dev':
                warnings.append(f'dev profile is using unsupported guidance source tier: {guidance_tier}')
            elif profile.name == 'review':
                warnings.append(f'review profile is reading unsupported guidance source tier: {guidance_tier}')
            else:
                preview_ready = False if profile.name in {'research', 'clinical'} else preview_ready
                session_lock_ready = False
                if profile.allows_write_commands:
                    execution_write_ready = False
                blockers.append(
                    f'{profile.name} profile requires guidance source tiers {list(profile.allowed_guidance_source_tiers)}; got {guidance_tier}'
                )
        elif profile.name == 'dev' and guidance_tier == 'simulated':
            warnings.append('dev profile is using synthetic guidance inputs')

        if force_tier not in set(profile.allowed_force_source_tiers):
            if profile.name == 'dev':
                warnings.append(f'dev profile is using unsupported force source tier: {force_tier}')
            elif profile.name == 'review':
                warnings.append(f'review profile is reading unsupported force source tier: {force_tier}')
            elif profile.name == 'lab' and force_tier == 'simulated':
                warnings.append('lab profile is still using simulated force inputs')
            else:
                session_lock_ready = False
                if profile.allows_write_commands:
                    execution_write_ready = False
                blockers.append(
                    f'{profile.name} profile requires force source tiers {list(profile.allowed_force_source_tiers)}; got {force_tier}'
                )
        elif profile.name == 'dev' and force_tier == 'simulated':
            warnings.append('dev profile is using simulated force inputs')


        return RuntimeSourcePolicySnapshot(
            deployment_profile=profile.name,
            force_source_tier=force_tier,
            camera_source_tier=camera_tier,
            guidance_source_type=str(guidance_source_type or camera_mode),
            shell_write_tier=shell_write_tier,
            execution_write_ready=execution_write_ready,
            session_lock_ready=session_lock_ready,
            preview_ready=preview_ready,
            blockers=tuple(blockers),
            warnings=tuple(warnings),
        )

    def validate_guidance_preview(self, *, config: RuntimeConfig, source_type: str, provider_mode: str = '') -> None:
        snapshot = self.build_snapshot(config=config, guidance_source_type=source_type, provider_mode=provider_mode)
        if not snapshot.preview_ready:
            raise RuntimeError('; '.join(snapshot.blockers) or 'guidance preview blocked by deployment source policy')

    def validate_session_lock(
        self,
        *,
        config: RuntimeConfig,
        patient_registration: dict[str, Any],
        localization_readiness: dict[str, Any],
        source_frame_set: dict[str, Any],
    ) -> None:
        source_type = str(
            patient_registration.get('source_type')
            or localization_readiness.get('source_type')
            or source_frame_set.get('source_type')
            or ''
        )
        provider_mode = str(source_frame_set.get('provider_mode') or getattr(config, 'camera_guidance_input_mode', ''))
        snapshot = self.build_snapshot(config=config, guidance_source_type=source_type, provider_mode=provider_mode)
        if not snapshot.session_lock_ready:
            raise RuntimeError('; '.join(snapshot.blockers) or 'session lock blocked by deployment source policy')

    def validate_execution_write(self, *, config: RuntimeConfig, guidance_source_type: str = '', provider_mode: str = '') -> None:
        snapshot = self.build_snapshot(config=config, guidance_source_type=guidance_source_type, provider_mode=provider_mode)
        if not snapshot.execution_write_ready:
            raise RuntimeError('; '.join(snapshot.blockers) or 'execution write blocked by deployment source policy')
