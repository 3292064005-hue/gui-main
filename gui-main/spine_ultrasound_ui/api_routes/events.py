from __future__ import annotations

import asyncio
from typing import Any, Callable

from fastapi import APIRouter, WebSocket, WebSocketDisconnect


def build_events_router(adapter_getter: Callable[[], Any]) -> APIRouter:
    router = APIRouter()

    @router.get("/api/v1/events/bus-stats")
    async def get_event_bus_stats():
        return adapter_getter().event_bus_stats()

    @router.get("/api/v1/events/dead-letters")
    async def get_event_dead_letters():
        return adapter_getter().event_dead_letters()

    @router.get("/api/v1/events/delivery-audit")
    async def get_event_delivery_audit():
        return adapter_getter().event_delivery_audit()

    @router.get("/api/v1/events/replay")
    async def get_event_replay(
        topics: str | None = None,
        session_id: str | None = None,
        since_ts_ns: int | None = None,
        until_ts_ns: int | None = None,
        delivery: str | None = None,
        category: str | None = None,
        limit: int | None = None,
        cursor: str | None = None,
        page_size: int | None = None,
    ):
        topic_filter = {topic.strip() for topic in (topics or "").split(",") if topic.strip()} or None
        return adapter_getter().replay_events(
            topics=topic_filter,
            session_id=session_id,
            since_ts_ns=since_ts_ns,
            until_ts_ns=until_ts_ns,
            delivery=delivery,
            category=category,
            limit=limit,
            cursor=cursor,
            page_size=page_size,
        )

    return router


def build_ws_router(adapter_getter: Callable[[], Any]) -> APIRouter:
    router = APIRouter()

    @router.websocket("/ws/telemetry")
    async def websocket_telemetry_endpoint(websocket: WebSocket):
        adapter = adapter_getter()
        await websocket.accept()
        topic_filter = {topic.strip() for topic in websocket.query_params.get("topics", "").split(",") if topic.strip()} or None
        if hasattr(adapter, "subscribe") and hasattr(adapter, "unsubscribe"):
            subscription = adapter.subscribe(topic_filter, include_snapshot=True)
            try:
                while True:
                    item = await asyncio.to_thread(subscription.get, 1.0)
                    if item is None:
                        break
                    await websocket.send_json(item)
            except WebSocketDisconnect:
                return
            finally:
                adapter.unsubscribe(subscription)
            return
        try:
            while True:
                for item in adapter.snapshot(topic_filter):
                    await websocket.send_json(item)
                await asyncio.sleep(0.1)
        except WebSocketDisconnect:
            return

    @router.websocket("/ws/camera")
    async def websocket_camera_endpoint(websocket: WebSocket):
        adapter = adapter_getter()
        await websocket.accept()
        try:
            while True:
                await websocket.send_text(adapter.camera_frame())
                await asyncio.sleep(0.1)
        except WebSocketDisconnect:
            return

    @router.websocket("/ws/ultrasound")
    async def websocket_ultrasound_endpoint(websocket: WebSocket):
        adapter = adapter_getter()
        await websocket.accept()
        try:
            while True:
                await websocket.send_text(adapter.ultrasound_frame())
                await asyncio.sleep(0.1)
        except WebSocketDisconnect:
            return

    return router
