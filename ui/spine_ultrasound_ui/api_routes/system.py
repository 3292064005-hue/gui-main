from __future__ import annotations

from typing import Any, Callable

from fastapi import APIRouter, Body, HTTPException

from spine_ultrasound_ui.contracts import schema_catalog


def build_system_router(adapter_getter: Callable[[], Any], deployment_profile_getter: Callable[[], Any]) -> APIRouter:
    router = APIRouter()


    def _raise_read_only_api(endpoint: str) -> None:
        raise HTTPException(status_code=403, detail=f"HTTP API is read-only evidence surface; {endpoint} must be initiated from the desktop operator console")

    @router.get("/api/v1/status")
    async def get_system_status():
        return adapter_getter().status()

    @router.get("/api/v1/health")
    async def get_health():
        return adapter_getter().health()

    @router.get("/api/v1/telemetry/snapshot")
    async def get_telemetry_snapshot(topics: str | None = None):
        topic_filter = {topic.strip() for topic in (topics or "").split(",") if topic.strip()} or None
        return adapter_getter().snapshot(topic_filter)

    @router.get("/api/v1/schema")
    async def get_protocol_schema():
        payload = adapter_getter().schema()
        payload["contract_schemas"] = list(schema_catalog().keys())
        return payload

    @router.get("/api/v1/profile")
    async def get_deployment_profile():
        adapter = adapter_getter()
        runtime_config = {}
        if hasattr(adapter, "runtime_config"):
            runtime_config = dict(getattr(adapter, "runtime_config")().get("runtime_config", {}))
        return {
            "deployment_profile": deployment_profile_getter().build_snapshot(None),
            "runtime_config_present": bool(runtime_config),
        }

    @router.get("/api/v1/backend/link-state")
    async def get_backend_link_state():
        adapter = adapter_getter()
        return {
            "status": adapter.status(),
            "health": adapter.health(),
            "topics": adapter.topic_catalog() if hasattr(adapter, "topic_catalog") else {"topics": []},
        }

    @router.get("/api/v1/control-plane")
    async def get_control_plane():
        adapter = adapter_getter()
        if hasattr(adapter, "control_plane_status"):
            return adapter.control_plane_status()
        return {
            "status": adapter.status(),
            "health": adapter.health(),
            "schema": adapter.schema(),
            "runtime_config": adapter.runtime_config() if hasattr(adapter, "runtime_config") else {"runtime_config": {}},
            "topics": adapter.topic_catalog() if hasattr(adapter, "topic_catalog") else {"topics": []},
            "recent_commands": {"recent_commands": []},
            "control_authority": adapter.control_authority_status() if hasattr(adapter, "control_authority_status") else {},
        }

    @router.get("/api/v1/control-authority")
    async def get_control_authority():
        adapter = adapter_getter()
        if hasattr(adapter, "resolve_control_authority"):
            payload = adapter.resolve_control_authority()
            if payload:
                return payload
            return {
                "summary_state": "degraded",
                "summary_label": "control authority unavailable",
                "detail": "adapter canonical authority surface returned no runtime-owned control authority",
            }
        if hasattr(adapter, "control_authority_status"):
            return adapter.control_authority_status()
        return {
            "summary_state": "ready",
            "summary_label": "control authority unavailable",
            "detail": "adapter does not expose control authority",
        }

    @router.get("/api/v1/authoritative-runtime-envelope")
    async def get_authoritative_runtime_envelope():
        adapter = adapter_getter()
        if hasattr(adapter, "resolve_authoritative_runtime_envelope"):
            payload = adapter.resolve_authoritative_runtime_envelope()
            if payload:
                return payload
            return {
                "summary_state": "degraded",
                "summary_label": "authoritative runtime envelope unavailable",
                "detail": "adapter canonical authority surface returned no runtime-published authoritative envelope",
            }
        if hasattr(adapter, "control_plane_status"):
            control_plane = adapter.control_plane_status()
            if isinstance(control_plane, dict):
                return dict(control_plane.get("authoritative_runtime_envelope", {}))
        return {
            "summary_state": "degraded",
            "summary_label": "authoritative runtime envelope unavailable",
            "detail": "adapter does not expose an authoritative runtime envelope",
        }

    @router.get("/api/v1/final-verdict")
    async def get_final_verdict():
        adapter = adapter_getter()
        if hasattr(adapter, "query_final_verdict_snapshot"):
            payload = adapter.query_final_verdict_snapshot()
            if payload:
                return payload
            return {
                "summary_state": "degraded",
                "summary_label": "final verdict unavailable",
                "detail": "adapter canonical final-verdict surface returned no runtime-owned verdict",
            }
        if hasattr(adapter, "resolve_final_verdict"):
            payload = adapter.resolve_final_verdict(None, None, read_only=True)
            if payload:
                return payload
            return {
                "summary_state": "degraded",
                "summary_label": "final verdict unavailable",
                "detail": "adapter canonical final-verdict surface returned no runtime-owned verdict",
            }
        return {
            "summary_state": "degraded",
            "summary_label": "final verdict unavailable",
            "detail": "adapter does not expose final verdict queries",
        }

    @router.post("/api/v1/control-lease/acquire")
    async def post_control_lease_acquire(payload: Any = Body(default=None)):
        if payload is not None and not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be a JSON object")
        _raise_read_only_api("control-lease acquire")

    @router.post("/api/v1/control-lease/renew")
    async def post_control_lease_renew(payload: Any = Body(default=None)):
        if payload is not None and not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be a JSON object")
        _raise_read_only_api("control-lease renew")

    @router.post("/api/v1/control-lease/release")
    async def post_control_lease_release(payload: Any = Body(default=None)):
        if payload is not None and not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be a JSON object")
        _raise_read_only_api("control-lease release")

    @router.get("/api/v1/commands/recent")
    async def get_recent_commands():
        adapter = adapter_getter()
        if hasattr(adapter, "recent_commands"):
            return adapter.recent_commands()
        return {"recent_commands": []}

    @router.get("/api/v1/runtime-config")
    async def get_runtime_config():
        adapter = adapter_getter()
        if hasattr(adapter, "runtime_config"):
            return adapter.runtime_config()
        return {"runtime_config": {}}

    @router.post("/api/v1/runtime-config")
    async def post_runtime_config(payload: Any = Body(default=None)):
        if payload is not None and not isinstance(payload, dict):
            raise HTTPException(status_code=400, detail="payload must be a JSON object")
        _raise_read_only_api("runtime-config update")

    @router.get("/api/v1/topics")
    async def get_topic_catalog():
        adapter = adapter_getter()
        if hasattr(adapter, "topic_catalog"):
            return adapter.topic_catalog()
        return {"topics": []}

    @router.get("/api/v1/roles")
    async def get_role_catalog():
        adapter = adapter_getter()
        if hasattr(adapter, "role_catalog"):
            return adapter.role_catalog()
        return {"roles": {}}

    @router.get("/api/v1/command-policies")
    async def get_command_policy_catalog():
        adapter = adapter_getter()
        if hasattr(adapter, "command_policy_catalog"):
            return adapter.command_policy_catalog()
        return {"policies": []}

    @router.get("/api/v1/schema/artifacts")
    async def get_artifact_schemas():
        return schema_catalog()

    return router
