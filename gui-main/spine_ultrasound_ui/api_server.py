from __future__ import annotations

import asyncio
import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import Body, FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from spine_ultrasound_ui.contracts import schema_catalog
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
    payload = adapter.schema()
    payload["contract_schemas"] = list(schema_catalog().keys())
    return payload


@app.get("/api/v1/topics")
async def get_topic_catalog():
    if hasattr(adapter, "topic_catalog"):
        return adapter.topic_catalog()
    return {"topics": []}


@app.get("/api/v1/roles")
async def get_role_catalog():
    if hasattr(adapter, "role_catalog"):
        return adapter.role_catalog()
    return {"roles": {}}


@app.get("/api/v1/command-policies")
async def get_command_policy_catalog():
    if hasattr(adapter, "command_policy_catalog"):
        return adapter.command_policy_catalog()
    return {"policies": []}


@app.get("/api/v1/schema/artifacts")
async def get_artifact_schemas():
    return schema_catalog()


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


@app.get("/api/v1/sessions/current/quality")
async def get_current_session_quality():
    try:
        return adapter.current_quality()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/frame-sync")
async def get_current_session_frame_sync():
    try:
        return adapter.current_frame_sync()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/alarms")
async def get_current_session_alarms():
    try:
        return adapter.current_alarms()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/artifacts")
async def get_current_session_artifacts():
    try:
        return adapter.current_artifacts()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/compare")
async def get_current_session_compare():
    try:
        return adapter.current_compare()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/qa-pack")
async def get_current_session_qa_pack():
    try:
        return adapter.current_qa_pack()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc




@app.get("/api/v1/sessions/current/trends")
async def get_current_session_trends():
    try:
        return adapter.current_trends()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/diagnostics")
async def get_current_session_diagnostics():
    try:
        return adapter.current_diagnostics()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/annotations")
async def get_current_session_annotations():
    try:
        return adapter.current_annotations()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/readiness")
async def get_current_session_readiness():
    try:
        return adapter.current_readiness()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/profile")
async def get_current_session_profile():
    try:
        return adapter.current_profile()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/patient-registration")
async def get_current_session_patient_registration():
    try:
        return adapter.current_patient_registration()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/scan-protocol")
async def get_current_session_scan_protocol():
    try:
        return adapter.current_scan_protocol()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc



@app.get("/api/v1/sessions/current/command-trace")
async def get_current_session_command_trace():
    try:
        return adapter.current_command_trace()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/assessment")
async def get_current_session_assessment():
    try:
        return adapter.current_assessment()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/contact")
async def get_current_session_contact():
    try:
        return adapter.current_contact()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/recovery")
async def get_current_session_recovery():
    try:
        return adapter.current_recovery()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/integrity")
async def get_current_session_integrity():
    try:
        return adapter.current_integrity()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/lineage")
async def get_current_session_lineage():
    try:
        return adapter.current_lineage()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/resume-state")
async def get_current_session_resume_state():
    try:
        return adapter.current_resume_state()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/recovery-report")
async def get_current_session_recovery_report():
    try:
        return adapter.current_recovery_report()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/operator-incidents")
async def get_current_session_operator_incidents():
    try:
        return adapter.current_operator_incidents()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/incidents")
async def get_current_session_incidents():
    try:
        return adapter.current_incidents()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/resume-decision")
async def get_current_session_resume_decision():
    try:
        return adapter.current_resume_decision()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/event-log-index")
async def get_current_session_event_log_index():
    try:
        return adapter.current_event_log_index()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/recovery-timeline")
async def get_current_session_recovery_timeline():
    try:
        return adapter.current_recovery_timeline()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/resume-attempts")
async def get_current_session_resume_attempts():
    try:
        return adapter.current_resume_attempts()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/resume-outcomes")
async def get_current_session_resume_outcomes():
    try:
        return adapter.current_resume_outcomes()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/command-policy")
async def get_current_session_command_policy():
    return adapter.current_command_policy()




@app.get("/api/v1/sessions/current/command-policy-snapshot")
async def get_current_command_policy_snapshot():
    try:
        return adapter.current_command_policy_snapshot()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/contract-kernel-diff")
async def get_current_contract_kernel_diff():
    try:
        return adapter.current_contract_kernel_diff()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
@app.get("/api/v1/sessions/current/contract-consistency")
async def get_current_session_contract_consistency():
    try:
        return adapter.current_contract_consistency()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/event-delivery-summary")
async def get_current_session_event_delivery_summary():
    try:
        return adapter.current_event_delivery_summary()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/release-evidence")
async def get_current_session_release_evidence():
    try:
        return adapter.current_release_evidence()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc




@app.get("/api/v1/sessions/current/selected-execution-rationale")
async def get_current_selected_execution_rationale():
    try:
        return adapter.current_selected_execution_rationale()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/sessions/current/release-gate")
async def get_current_release_gate_decision():
    try:
        return adapter.current_release_gate_decision()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/v1/events/bus-stats")
async def get_event_bus_stats():
    return adapter.event_bus_stats()


@app.get("/api/v1/events/dead-letters")
async def get_event_dead_letters():
    return adapter.event_dead_letters()


@app.get("/api/v1/events/delivery-audit")
async def get_event_delivery_audit():
    return adapter.event_delivery_audit()


@app.get("/api/v1/events/replay")
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
    topic_filter = {topic.strip() for topic in (topics or '').split(',') if topic.strip()} or None
    return adapter.replay_events(
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


@app.post("/api/v1/commands/{command}")
async def post_command(
    command: str,
    payload: Any = Body(default=None),
    x_spine_role: str | None = Header(default=None),
):
    role = (x_spine_role or "operator").strip().lower()
    if getattr(adapter, "read_only_mode", False):
        raise HTTPException(status_code=403, detail="adapter is running in read-only review mode")
    role_catalog = getattr(adapter, "role_matrix", None)
    if role_catalog is not None and not role_catalog.can_issue_command(role, command):
        raise HTTPException(status_code=403, detail=f"role '{role}' is not allowed to issue write commands")
    if role_catalog is None and role != "operator":
        raise HTTPException(status_code=403, detail=f"role '{role}' is not allowed to issue write commands")
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
