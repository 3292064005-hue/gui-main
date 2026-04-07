from __future__ import annotations

from spine_ultrasound_ui.api_server import ApiServerSettings


def test_api_server_settings_ignore_ui_backend_for_headless_resolution() -> None:
    settings = ApiServerSettings.from_env({
        'SPINE_DEPLOYMENT_PROFILE': 'dev',
        'SPINE_UI_BACKEND': 'api',
    })
    assert settings.backend_mode == 'mock'
    assert settings.backend_resolution_source == 'profile_default'
