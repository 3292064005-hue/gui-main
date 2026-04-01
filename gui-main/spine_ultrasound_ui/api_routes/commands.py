from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Body, Header, HTTPException
from loguru import logger

from spine_ultrasound_ui.services.api_command_guard import ApiCommandHeaders
from spine_ultrasound_ui.services.backend_errors import BackendOperationError, InvalidPayloadError, normalize_backend_exception


def build_command_router(adapter_getter: Callable[[], Any], guard_getter: Callable[[], Any]) -> APIRouter:
    router = APIRouter()

    def _route_status(exc: BackendOperationError) -> int:
        # Preserve the historical HTTP contract: adapter-side transport faults are
        # surfaced as 502 at the API boundary even when the internal typed error
        # retains 503/504 semantics for diagnostics and retry policy.
        return 502 if exc.error_type in {"transport_error", "transport_timeout", "dependency_failure"} else exc.http_status


    @router.post("/api/v1/commands/{command}")
    async def post_command(
        command: str,
        payload: Any = Body(default=None),
        x_spine_role: str | None = Header(default=None),
        x_spine_actor: str | None = Header(default=None),
        x_spine_workspace: str | None = Header(default=None),
        x_spine_lease_id: str | None = Header(default=None),
        x_spine_intent: str | None = Header(default=None),
        x_spine_session_id: str | None = Header(default=None),
        x_spine_api_token: str | None = Header(default=None),
    ):
        adapter = adapter_getter()
        guard = guard_getter()
        try:
            payload_dict = guard.normalize_payload(
                adapter=adapter,
                command=command,
                payload=payload,
                headers=ApiCommandHeaders(
                    role=x_spine_role,
                    actor=x_spine_actor,
                    workspace=x_spine_workspace,
                    lease_id=x_spine_lease_id,
                    intent=x_spine_intent,
                    session_id=x_spine_session_id,
                    api_token=x_spine_api_token,
                ),
            )
            return adapter.command(command, payload_dict)
        except (ValueError, TypeError) as exc:
            normalized = normalize_backend_exception(InvalidPayloadError(str(exc)), command=command, context="headless-command")
            raise HTTPException(status_code=_route_status(normalized), detail=normalized.message) from exc
        except BackendOperationError as exc:
            raise HTTPException(status_code=_route_status(exc), detail=exc.message) from exc
        except HTTPException:
            raise
        except Exception as exc:
            normalized = normalize_backend_exception(exc, command=command, context="headless-command")
            logger.warning(f"Headless command failure for {command}: {normalized.error_type}: {normalized.message}")
            raise HTTPException(status_code=_route_status(normalized), detail=normalized.message) from exc

    return router
