#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import signal
import socket
import subprocess
import sys
import time
from pathlib import Path
from typing import Mapping

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.runtime_mode_policy import resolve_runtime_mode

_CANONICAL_DEPLOYMENT_PROFILES = ("dev", "lab", "research", "clinical", "review")
_LEGACY_PROFILE_ALIASES = {
    "mock": "dev",
    "hil": "research",
    "prod": "clinical",
}
_BUILD_PROFILE_BY_DEPLOYMENT = {
    "dev": "mock",
    "lab": "hil",
    "research": "hil",
    "clinical": "prod",
    "review": "mock",
}


def _bool_env(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return str(value).strip().lower() not in {"0", "false", "off", "no", ""}


def _env_str(*names: str, default: str) -> str:
    for name in names:
        raw = os.getenv(name)
        if raw is not None and str(raw).strip():
            return str(raw).strip()
    return default


def _normalize_deployment_profile(raw: str | None) -> str:
    normalized = str(raw or "").strip().lower()
    if not normalized:
        return "dev"
    return _LEGACY_PROFILE_ALIASES.get(normalized, normalized)


def _validate_deployment_profile(profile: str) -> str:
    if profile not in _CANONICAL_DEPLOYMENT_PROFILES:
        valid = ", ".join(_CANONICAL_DEPLOYMENT_PROFILES + tuple(_LEGACY_PROFILE_ALIASES))
        raise SystemExit(f"Unsupported --profile={profile!r}. Expected one of: {valid}")
    return profile


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Unified operator-facing launcher for Spine mainline surfaces")
    parser.add_argument("--surface", choices=("desktop", "headless"), default=os.getenv("SPINE_MAINLINE_SURFACE", "desktop"))
    parser.add_argument(
        "--profile",
        default=_env_str("SPINE_DEPLOYMENT_PROFILE", "SPINE_PROFILE", default="dev"),
        help="deployment profile (dev/lab/research/clinical/review); legacy aliases mock/hil/prod are still accepted",
    )
    parser.add_argument("--backend", choices=("mock", "core", "api", "auto"), default=os.getenv("SPINE_MAINLINE_BACKEND", "auto"))
    parser.add_argument("--build-dir", default=os.getenv("SPINE_CORE_BUILD_DIR", "/tmp/spine_core_build_runtime"))
    parser.add_argument("--cmake-build-type", default=os.getenv("CMAKE_BUILD_TYPE", "Release"))
    parser.add_argument("--workspace", default=str(ROOT / "data"))
    parser.add_argument("--api-base-url", default=os.getenv("SPINE_API_BASE_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--host", default=os.getenv("SPINE_HEADLESS_HOST", "0.0.0.0"))
    parser.add_argument("--port", default=os.getenv("SPINE_HEADLESS_PORT", "8000"))
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--skip-doctor", action="store_true")
    parser.add_argument("--doctor-strict", action="store_true", default=_bool_env("SPINE_DOCTOR_STRICT", False))
    parser.add_argument("--core-command-port", type=int, default=int(os.getenv("SPINE_CORE_COMMAND_PORT", "5656")))
    parser.add_argument("--core-telemetry-port", type=int, default=int(os.getenv("SPINE_CORE_TELEMETRY_PORT", "5657")))
    parser.add_argument("--core-ready-timeout-sec", type=float, default=float(os.getenv("SPINE_CORE_READY_TIMEOUT_SEC", "8.0")))
    parser.add_argument("--core-ready-poll-sec", type=float, default=float(os.getenv("SPINE_CORE_READY_POLL_SEC", "0.1")))
    args = parser.parse_args()
    args.profile = _validate_deployment_profile(_normalize_deployment_profile(args.profile))
    return args


def _resolve_backend(*, profile_name: str, surface: str, backend: str, env: Mapping[str, str]) -> str:
    explicit_backend = None if backend == "auto" else backend
    decision = resolve_runtime_mode(
        explicit_mode=explicit_backend,
        surface=surface,
        env=env,
        allow_environment_override=False,
    )
    if decision.profile_name != profile_name:
        raise RuntimeError(
            f"launcher profile drift: expected deployment profile '{profile_name}', runtime policy resolved '{decision.profile_name}'"
        )
    return decision.mode


def _resolve_core_build_flags(*, deployment_profile: str, backend: str) -> tuple[str, str, str]:
    build_profile = _BUILD_PROFILE_BY_DEPLOYMENT[deployment_profile]
    requires_live_sdk = deployment_profile in {"research", "clinical"}
    wants_contract_transport = backend == "core"
    sdk_default = requires_live_sdk or deployment_profile == "lab" or wants_contract_transport
    model_default = requires_live_sdk
    with_sdk = "ON" if _bool_env("ROBOT_CORE_WITH_XCORE_SDK", sdk_default) else "OFF"
    with_model = "ON" if _bool_env("ROBOT_CORE_WITH_XMATE_MODEL", model_default) else "OFF"
    if with_sdk == "OFF":
        with_model = "OFF"
    return build_profile, with_sdk, with_model


def build_env(args: argparse.Namespace) -> dict[str, str]:
    env = dict(os.environ)
    env["SPINE_DEPLOYMENT_PROFILE"] = args.profile
    env["SPINE_PROFILE"] = args.profile
    env.pop("SPINE_LAB_MODE", None)
    env.pop("SPINE_RESEARCH_MODE", None)
    env.pop("SPINE_READ_ONLY_MODE", None)
    env.pop("SPINE_UI_BACKEND", None)
    env.pop("SPINE_HEADLESS_BACKEND", None)

    profile = DeploymentProfileService({"SPINE_DEPLOYMENT_PROFILE": args.profile}).resolve(None)
    if args.profile == "lab":
        env["SPINE_LAB_MODE"] = "1"
    elif args.profile == "research":
        env["SPINE_RESEARCH_MODE"] = "1"
    elif args.profile == "review":
        env["SPINE_READ_ONLY_MODE"] = "1"

    resolved_backend = _resolve_backend(profile_name=args.profile, surface=args.surface, backend=args.backend, env=env)
    env["SPINE_MAINLINE_BACKEND"] = resolved_backend
    if args.surface == "desktop":
        env["SPINE_UI_BACKEND"] = resolved_backend
    else:
        env["SPINE_HEADLESS_BACKEND"] = resolved_backend

    env["SPINE_STRICT_CONTROL_AUTHORITY"] = "1" if profile.requires_strict_control_authority else "0"
    build_profile, with_sdk, with_model = _resolve_core_build_flags(deployment_profile=args.profile, backend=resolved_backend)
    env["ROBOT_CORE_PROFILE"] = build_profile
    env.setdefault("SPINE_RUNTIME_BUILD_PROFILE", build_profile)
    env["ROBOT_CORE_WITH_XCORE_SDK"] = with_sdk
    env["ROBOT_CORE_WITH_XMATE_MODEL"] = with_model
    return env


def run_checked(cmd: list[str], *, env: Mapping[str, str]) -> None:
    subprocess.run(cmd, cwd=ROOT, env=dict(env), check=True)


def maybe_run_doctor(args: argparse.Namespace, env: Mapping[str, str]) -> None:
    if args.skip_doctor:
        return
    cmd = [sys.executable, str(ROOT / "scripts" / "doctor_runtime.py"), "--surface", args.surface]
    if args.doctor_strict or args.profile in {"research", "clinical"}:
        cmd.append("--strict")
    run_checked(cmd, env=env)


def maybe_build_core(args: argparse.Namespace, env: Mapping[str, str]) -> Path:
    build_dir = Path(args.build_dir)
    if str(env.get("SPINE_MAINLINE_BACKEND", "")) != "core":
        return build_dir / "spine_robot_core"
    if args.skip_build:
        return build_dir / "spine_robot_core"
    cmake_args = [
        "cmake", "-S", str(ROOT / "cpp_robot_core"), "-B", str(build_dir),
        f"-DCMAKE_BUILD_TYPE={args.cmake_build_type}",
        f"-DROBOT_CORE_PROFILE={env.get('ROBOT_CORE_PROFILE', 'mock')}",
        f"-DROBOT_CORE_WITH_XCORE_SDK={env.get('ROBOT_CORE_WITH_XCORE_SDK', 'OFF')}",
        f"-DROBOT_CORE_WITH_XMATE_MODEL={env.get('ROBOT_CORE_WITH_XMATE_MODEL', 'OFF')}",
    ]
    sdk_root = os.getenv("XCORE_SDK_ROOT") or os.getenv("ROKAE_SDK_ROOT")
    if sdk_root:
        cmake_args.append(f"-DXCORE_SDK_ROOT={sdk_root}")
    run_checked(cmake_args, env=env)
    run_checked(["cmake", "--build", str(build_dir), f"-j{os.getenv('CMAKE_BUILD_PARALLEL_LEVEL', '1')}"], env=env)
    return build_dir / "spine_robot_core"


def launch_core_binary(core_bin: Path, env: Mapping[str, str]) -> subprocess.Popen[str] | None:
    if str(env.get("SPINE_MAINLINE_BACKEND", "")) != "core":
        return None
    sdk_root = os.getenv("XCORE_SDK_ROOT") or os.getenv("ROKAE_SDK_ROOT")
    child_env = dict(env)
    if sdk_root:
        sdk_lib_dir = Path(sdk_root) / "lib" / "Linux" / "cpp" / "x86_64"
        child_env["LD_LIBRARY_PATH"] = f"{sdk_lib_dir}:{child_env.get('LD_LIBRARY_PATH', '')}".rstrip(":")
    return subprocess.Popen([str(core_bin)], cwd=ROOT, env=child_env, text=True)


def _port_accepting(host: str, port: int, timeout_sec: float) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_sec)
        try:
            sock.connect((host, port))
            return True
        except OSError:
            return False


def wait_for_core_ready(core_proc: subprocess.Popen[str] | None, args: argparse.Namespace) -> None:
    if core_proc is None:
        return
    deadline = time.monotonic() + max(0.1, float(args.core_ready_timeout_sec))
    poll = max(0.05, float(args.core_ready_poll_sec))
    command_ready = False
    telemetry_ready = False
    while time.monotonic() < deadline:
        if core_proc.poll() is not None:
            raise RuntimeError(f"core process exited early with code {core_proc.returncode}")
        command_ready = _port_accepting("127.0.0.1", int(args.core_command_port), poll)
        telemetry_ready = _port_accepting("127.0.0.1", int(args.core_telemetry_port), poll)
        if command_ready and telemetry_ready:
            return
        time.sleep(poll)
    raise RuntimeError(
        "core readiness probe timed out before command/telemetry ports became available: "
        f"command_ready={command_ready} telemetry_ready={telemetry_ready}"
    )


def run_surface(args: argparse.Namespace, env: Mapping[str, str]) -> int:
    if args.surface == "desktop":
        cmd = [sys.executable, str(ROOT / "run.py"), "--backend", str(env.get("SPINE_UI_BACKEND", "mock")), "--workspace", args.workspace, "--api-base-url", args.api_base_url]
    else:
        cmd = [sys.executable, "-m", "uvicorn", "spine_ultrasound_ui.api_server:app", "--host", args.host, "--port", str(args.port)]
    return subprocess.call(cmd, cwd=ROOT, env=dict(env))


def main() -> int:
    args = parse_args()
    env = build_env(args)
    maybe_run_doctor(args, env)
    core_bin = maybe_build_core(args, env)
    core_proc = launch_core_binary(core_bin, env)
    try:
        wait_for_core_ready(core_proc, args)
        return run_surface(args, env)
    finally:
        if core_proc is not None:
            core_proc.send_signal(signal.SIGTERM)
            try:
                core_proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                core_proc.kill()
                core_proc.wait(timeout=5)


if __name__ == "__main__":
    raise SystemExit(main())
