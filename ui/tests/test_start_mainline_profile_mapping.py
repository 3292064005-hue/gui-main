from __future__ import annotations

from argparse import Namespace

from scripts.start_mainline import build_env


def _args(*, profile: str, backend: str = "auto", surface: str = "desktop") -> Namespace:
    return Namespace(
        profile=profile, backend=backend, surface=surface, build_dir="/tmp/build", cmake_build_type="Release", workspace="/tmp/ws", api_base_url="http://127.0.0.1:8000", host="0.0.0.0", port="8000", skip_build=False, skip_doctor=False, doctor_strict=False, core_command_port=5656, core_telemetry_port=5657, core_ready_timeout_sec=8.0, core_ready_poll_sec=0.1
    )


def test_mock_profile_maps_to_dev_without_strict_authority(monkeypatch):
    monkeypatch.delenv("SPINE_DEPLOYMENT_PROFILE", raising=False)
    monkeypatch.delenv("SPINE_STRICT_CONTROL_AUTHORITY", raising=False)
    env = build_env(_args(profile="mock"))
    assert env["SPINE_DEPLOYMENT_PROFILE"] == "dev"
    assert env["SPINE_MAINLINE_BACKEND"] == "mock"
    assert "SPINE_STRICT_CONTROL_AUTHORITY" not in env or env["SPINE_STRICT_CONTROL_AUTHORITY"] != "1"


def test_hil_profile_maps_to_lab_and_enables_core_authority(monkeypatch):
    monkeypatch.delenv("SPINE_DEPLOYMENT_PROFILE", raising=False)
    monkeypatch.delenv("SPINE_STRICT_CONTROL_AUTHORITY", raising=False)
    monkeypatch.delenv("SPINE_LAB_MODE", raising=False)
    env = build_env(_args(profile="hil"))
    assert env["SPINE_DEPLOYMENT_PROFILE"] == "lab"
    assert env["SPINE_MAINLINE_BACKEND"] == "core"
    assert env["SPINE_LAB_MODE"] == "1"
    assert env["SPINE_STRICT_CONTROL_AUTHORITY"] == "1"


def test_prod_profile_maps_to_clinical(monkeypatch):
    monkeypatch.delenv("SPINE_DEPLOYMENT_PROFILE", raising=False)
    monkeypatch.delenv("SPINE_STRICT_CONTROL_AUTHORITY", raising=False)
    env = build_env(_args(profile="prod"))
    assert env["SPINE_DEPLOYMENT_PROFILE"] == "clinical"
    assert env["SPINE_MAINLINE_BACKEND"] == "core"
    assert env["SPINE_STRICT_CONTROL_AUTHORITY"] == "1"
