from __future__ import annotations

import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Callable

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from spine_ultrasound_ui.api_routes import (
    build_command_router,
    build_events_router,
    build_session_router,
    build_system_router,
    build_ws_router,
)
from spine_ultrasound_ui.services.api_command_guard import ApiCommandGuardService
from spine_ultrasound_ui.services.api_runtime_container import ApiRuntimeContainer
from spine_ultrasound_ui.services.backend_errors import normalize_backend_exception
from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService
from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter
from spine_ultrasound_ui.services.runtime_mode_policy import resolve_runtime_mode


@dataclass
class ApiServerSettings:
    backend_mode: str
    command_host: str
    command_port: int
    telemetry_host: str
    telemetry_port: int
    allowed_origins: list[str]
    deployment_profile: str
    backend_resolution_source: str
    allowed_backend_modes: tuple[str, ...]

    @classmethod
    def from_env(cls, env: dict[str, str] | None = None) -> "ApiServerSettings":
        """Build settings from environment variables with defensive parsing.

        Invalid port values fall back to the documented defaults instead of
        crashing module import.
        """
        source = env if env is not None else os.environ
        origins_raw = source.get(
            "SPINE_ALLOWED_ORIGINS",
            "http://localhost:5173,http://127.0.0.1:5173,http://localhost:4173,http://127.0.0.1:4173",
        )
        allowed_origins = [item.strip() for item in origins_raw.split(",") if item.strip()]

        def _parse_port(name: str, default: int) -> int:
            raw_value = str(source.get(name, str(default))).strip()
            try:
                value = int(raw_value)
            except (TypeError, ValueError):
                return default
            return value if 0 < value <= 65535 else default

        decision = resolve_runtime_mode(
            explicit_mode=source.get("SPINE_HEADLESS_BACKEND"),
            surface="headless",
            env=source,
        )
        return cls(
            backend_mode=decision.mode,
            command_host=source.get("ROBOT_CORE_HOST", "127.0.0.1"),
            command_port=_parse_port("ROBOT_CORE_COMMAND_PORT", 5656),
            telemetry_host=source.get("ROBOT_CORE_HOST", "127.0.0.1"),
            telemetry_port=_parse_port("ROBOT_CORE_TELEMETRY_PORT", 5657),
            allowed_origins=allowed_origins or ["http://localhost:5173"],
            deployment_profile=decision.profile_name,
            backend_resolution_source=decision.resolution_source,
            allowed_backend_modes=decision.allowed_modes,
        )


DEFAULT_API_SERVER_SETTINGS = ApiServerSettings.from_env()


def _runtime_container_from_app(app: FastAPI) -> ApiRuntimeContainer:
    container = getattr(app.state, "runtime_container", None)
    if container is None:  # pragma: no cover - indicates create_app misuse
        raise RuntimeError("FastAPI app is missing runtime_container state")
    return container


def create_app(
    *,
    settings: ApiServerSettings | None = None,
    runtime_container: ApiRuntimeContainer | None = None,
    adapter_getter: Callable[[], HeadlessAdapter] | None = None,
    profile_service_getter: Callable[[], DeploymentProfileService] | None = None,
    command_guard_getter: Callable[[], ApiCommandGuardService] | None = None,
    allowed_origins: list[str] | None = None,
    title: str = "Spine Ultrasound Headless Adapter",
) -> FastAPI:
    """Create a FastAPI application with an explicit runtime composition root.

    Args:
        settings: Optional server settings override.
        runtime_container: Optional prebuilt runtime container.
        adapter_getter: Optional adapter resolver override.
        profile_service_getter: Optional deployment-profile resolver override.
        command_guard_getter: Optional command-guard resolver override.
        allowed_origins: Explicit CORS origins.
        title: Application title.

    Returns:
        Configured FastAPI application.

    Boundary behavior:
        The application stores its runtime dependencies on ``app.state``.
        There is no module-level singleton fallback; every instance must resolve
        dependencies from its own composition root.
    """
    resolved_settings = settings or DEFAULT_API_SERVER_SETTINGS
    resolved_container = runtime_container or ApiRuntimeContainer.build(settings=resolved_settings)
    origins = list(allowed_origins or resolved_settings.allowed_origins)

    fastapi_app = FastAPI(title=title)
    fastapi_app.state.runtime_container = resolved_container
    fastapi_app.state.api_server_settings = resolved_settings

    def _app_adapter() -> HeadlessAdapter:
        if adapter_getter is not None:
            return adapter_getter()
        return _runtime_container_from_app(fastapi_app).runtime_adapter

    def _app_profile_service() -> DeploymentProfileService:
        if profile_service_getter is not None:
            return profile_service_getter()
        return _runtime_container_from_app(fastapi_app).deployment_profile_service

    def _app_command_guard() -> ApiCommandGuardService:
        if command_guard_getter is not None:
            return command_guard_getter()
        return _runtime_container_from_app(fastapi_app).command_guard_service

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        runtime_adapter = _app_adapter()
        logger.info("Initializing headless adapter...")
        runtime_adapter.start()
        try:
            yield
        finally:
            logger.info("Tearing down headless adapter...")
            try:
                runtime_adapter.stop()
            except Exception as exc:  # pragma: no cover - defensive shutdown path
                normalized = normalize_backend_exception(exc, context="shutdown")
                logger.error(f"Headless adapter stop failed: {normalized.error_type}: {normalized.message}")
            close = getattr(runtime_adapter, "close", None)
            if callable(close):
                try:
                    close()
                except Exception as exc:  # pragma: no cover - defensive shutdown path
                    normalized = normalize_backend_exception(exc, context="shutdown")
                    logger.error(f"Headless adapter close failed: {normalized.error_type}: {normalized.message}")

    fastapi_app.router.lifespan_context = lifespan
    fastapi_app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["*"],
    )
    fastapi_app.include_router(build_system_router(_app_adapter, _app_profile_service))
    fastapi_app.include_router(build_session_router(_app_adapter))
    fastapi_app.include_router(build_events_router(_app_adapter))
    fastapi_app.include_router(build_command_router(_app_adapter, _app_command_guard))
    fastapi_app.include_router(build_ws_router(_app_adapter))
    return fastapi_app


app = create_app()
