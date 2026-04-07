from __future__ import annotations

import pytest

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.runtime_mode_policy import resolve_runtime_mode


def test_deployment_profile_defaults_to_dev_without_explicit_runtime_intent() -> None:
    profile = DeploymentProfileService(env={}).resolve(RuntimeConfig())
    assert profile.name == 'dev'


def test_runtime_mode_policy_defaults_dev_desktop_to_mock() -> None:
    decision = resolve_runtime_mode(explicit_mode=None, surface='desktop', env={})
    assert decision.profile_name == 'dev'
    assert decision.mode == 'mock'
    assert decision.resolution_source == 'profile_default'


def test_runtime_mode_policy_blocks_mock_in_research_headless() -> None:
    with pytest.raises(ValueError, match='only allows backend modes: core'):
        resolve_runtime_mode(
            explicit_mode='mock',
            surface='headless',
            env={'SPINE_DEPLOYMENT_PROFILE': 'research'},
        )


def test_runtime_mode_policy_allows_api_desktop_review() -> None:
    decision = resolve_runtime_mode(
        explicit_mode=None,
        surface='desktop',
        env={'SPINE_READ_ONLY_MODE': '1'},
    )
    assert decision.profile_name == 'review'
    assert decision.mode == 'api'


def test_headless_runtime_mode_does_not_fallback_to_ui_backend_env() -> None:
    decision = resolve_runtime_mode(
        explicit_mode=None,
        surface='headless',
        env={'SPINE_DEPLOYMENT_PROFILE': 'dev', 'SPINE_UI_BACKEND': 'api'},
    )
    assert decision.mode == 'mock'
    assert decision.resolution_source == 'profile_default'
