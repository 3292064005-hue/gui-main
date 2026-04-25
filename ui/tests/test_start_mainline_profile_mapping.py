from __future__ import annotations

from argparse import Namespace

from scripts.start_mainline import build_env, _normalize_deployment_profile


def _args(*, profile: str, backend: str = "auto", surface: str = "desktop") -> Namespace:
    return Namespace(
        profile=profile,
        backend=backend,
        surface=surface,
        build_dir="/tmp/build",
        cmake_build_type="Release",
        workspace="/tmp/ws",
        api_base_url="http://127.0.0.1:8000",
        host="0.0.0.0",
        port="8000",
        skip_build=False,
        skip_doctor=False,
        doctor_strict=False,
        core_command_port=5656,
        core_telemetry_port=5657,
        core_ready_timeout_sec=8.0,
        core_ready_poll_sec=0.1,
    )


def test_dev_profile_maps_to_mock_build_without_strict_authority(monkeypatch):
    monkeypatch.delenv("SPINE_DEPLOYMENT_PROFILE", raising=False)
    monkeypatch.delenv("SPINE_STRICT_CONTROL_AUTHORITY", raising=False)
    env = build_env(_args(profile="dev"))
    assert env["SPINE_DEPLOYMENT_PROFILE"] == "dev"
    assert env["SPINE_MAINLINE_BACKEND"] == "mock"
    assert env["ROBOT_CORE_PROFILE"] == "mock"
    assert env["SPINE_STRICT_CONTROL_AUTHORITY"] == "0"


def test_legacy_mock_alias_maps_to_dev() -> None:
    assert _normalize_deployment_profile("mock") == "dev"


def test_research_profile_maps_to_hil_build_and_enables_core_authority(monkeypatch):
    monkeypatch.delenv("SPINE_DEPLOYMENT_PROFILE", raising=False)
    monkeypatch.delenv("SPINE_STRICT_CONTROL_AUTHORITY", raising=False)
    monkeypatch.delenv("SPINE_RESEARCH_MODE", raising=False)
    env = build_env(_args(profile="research"))
    assert env["SPINE_DEPLOYMENT_PROFILE"] == "research"
    assert env["SPINE_MAINLINE_BACKEND"] == "core"
    assert env["SPINE_RESEARCH_MODE"] == "1"
    assert env["SPINE_STRICT_CONTROL_AUTHORITY"] == "1"
    assert env["ROBOT_CORE_PROFILE"] == "hil"
    assert env["ROBOT_CORE_WITH_XCORE_SDK"] == "ON"


def test_clinical_profile_maps_to_prod_build(monkeypatch):
    monkeypatch.delenv("SPINE_DEPLOYMENT_PROFILE", raising=False)
    monkeypatch.delenv("SPINE_STRICT_CONTROL_AUTHORITY", raising=False)
    env = build_env(_args(profile="clinical"))
    assert env["SPINE_DEPLOYMENT_PROFILE"] == "clinical"
    assert env["SPINE_MAINLINE_BACKEND"] == "core"
    assert env["SPINE_STRICT_CONTROL_AUTHORITY"] == "1"
    assert env["ROBOT_CORE_PROFILE"] == "prod"




def test_robot_core_profile_env_does_not_select_deployment_profile(monkeypatch):
    monkeypatch.setenv("ROBOT_CORE_PROFILE", "prod")
    monkeypatch.delenv("SPINE_DEPLOYMENT_PROFILE", raising=False)
    monkeypatch.delenv("SPINE_PROFILE", raising=False)
    from scripts.start_mainline import parse_args
    monkeypatch.setattr("sys.argv", ["start_mainline.py"])
    args = parse_args()
    assert args.profile == "dev"


def test_review_profile_sets_read_only_and_mock_build(monkeypatch):
    monkeypatch.delenv("SPINE_READ_ONLY_MODE", raising=False)
    env = build_env(_args(profile="review", surface="headless"))
    assert env["SPINE_DEPLOYMENT_PROFILE"] == "review"
    assert env["SPINE_READ_ONLY_MODE"] == "1"
    assert env["ROBOT_CORE_PROFILE"] == "mock"


def test_launcher_auto_backend_ignores_legacy_desktop_backend_env(monkeypatch):
    monkeypatch.setenv('SPINE_UI_BACKEND', 'api')
    env = build_env(_args(profile='research', backend='auto', surface='desktop'))
    assert env['SPINE_MAINLINE_BACKEND'] == 'core'
    assert env['SPINE_UI_BACKEND'] == 'core'
    assert 'SPINE_HEADLESS_BACKEND' not in env


def test_launcher_auto_backend_ignores_legacy_headless_backend_env(monkeypatch):
    monkeypatch.setenv('SPINE_HEADLESS_BACKEND', 'mock')
    env = build_env(_args(profile='clinical', backend='auto', surface='headless'))
    assert env['SPINE_MAINLINE_BACKEND'] == 'core'
    assert env['SPINE_HEADLESS_BACKEND'] == 'core'
    assert 'SPINE_UI_BACKEND' not in env
