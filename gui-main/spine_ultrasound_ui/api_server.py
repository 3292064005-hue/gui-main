from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Body, FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from spine_ultrasound_ui.services.headless_adapter import HeadlessAdapter


adapter = HeadlessAdapter(
    mode=os.getenv("SPINE_HEADLESS_BACKEND", os.getenv("SPINE_UI_BACKEND", "mock")),
    command_host=os.getenv("ROBOT_CORE_HOST", "127.0.0.1"),
    command_port=int(os.getenv("ROBOT_CORE_COMMAND_PORT", "5656")),
    telemetry_host=os.getenv("ROBOT_CORE_HOST", "127.0.0.1"),
    telemetry_port=int(os.getenv("ROBOT_CORE_TELEMETRY_PORT", "5657")),
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing headless adapter...")
    adapter.start()
    yield
    logger.info("Tearing down headless adapter...")
    adapter.stop()


app = FastAPI(title="Spine Ultrasound Headless Adapter", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/status")
async def get_system_status():
    return adapter.status()


@app.get("/api/v1/health")
async def get_health():
    return adapter.health()


@app.get("/api/v1/telemetry/snapshot")
async def get_telemetry_snapshot(topics: str | None = None):
    topic_filter = {topic.strip() for topic in (topics or "").split(",") if topic.strip()} or None
    return adapter.snapshot(topic_filter)


@app.get("/api/v1/schema")
async def get_protocol_schema():
    return adapter.schema()


@app.get("/api/v1/sessions/current")
async def get_current_session():
    try:
        return adapter.current_session()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/report")
async def get_current_session_report():
    try:
        return adapter.current_report()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/replay")
async def get_current_session_replay():
    try:
        return adapter.current_replay()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.post("/api/v1/commands/{command}")
async def post_command(command: str, payload: Any = Body(default=None)):
    if payload is not None and not isinstance(payload, dict):
        raise HTTPException(status_code=400, detail="payload must be a JSON object")
    try:
        return adapter.command(command, payload or {})
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        logger.warning(f"Headless command failure for {command}: {exc}")
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@app.websocket("/ws/telemetry")
async def websocket_telemetry_endpoint(websocket: WebSocket):
    await websocket.accept()
    topic_filter = {topic.strip() for topic in websocket.query_params.get("topics", "").split(",") if topic.strip()} or None
    try:
        while True:
            for item in adapter.snapshot(topic_filter):
                await websocket.send_json(item)
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/camera")
async def websocket_camera_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(adapter.camera_frame())
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return


@app.websocket("/ws/ultrasound")
async def websocket_ultrasound_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            await websocket.send_text(adapter.ultrasound_frame())
            await asyncio.sleep(0.1)
    except WebSocketDisconnect:
        return
