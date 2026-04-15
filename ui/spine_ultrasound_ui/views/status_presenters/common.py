from __future__ import annotations

from dataclasses import dataclass
from html import escape
from typing import Any

from spine_ultrasound_ui.services.runtime_governance_query_surface import RuntimeGovernanceQuerySurface


@dataclass(frozen=True)
class StatusViewContext:
    payload: dict[str, Any]
    window: Any
    devices: dict[str, Any]
    metrics: dict[str, Any]
    current_exp: dict[str, Any] | None
    robot: dict[str, Any]
    safety: dict[str, Any]
    recording: dict[str, Any]
    config: dict[str, Any]
    workflow: dict[str, Any]
    readiness: dict[str, Any]
    sdk_alignment: dict[str, Any]
    sdk_runtime: dict[str, Any]
    model_report: dict[str, Any]
    config_report: dict[str, Any]
    session_governance: dict[str, Any]
    backend_link: dict[str, Any]
    bridge_observability: dict[str, Any]
    control_plane: dict[str, Any]
    control_authority: dict[str, Any]
    persistence: dict[str, Any]
    system_state: str
    pose: dict[str, Any]
    rl_status: dict[str, Any]
    drag_status: dict[str, Any]
    exp_id: str
    operate_mode: str
    readiness_percent: int
    readiness_state: str
    recommended_label: str
    recommended_reason: str
    recommended_tab: str
    blockers: list[Any]
    sdk_blockers: list[Any]
    sdk_warnings: list[Any]
    model_blockers: list[Any]
    model_warnings: list[Any]
    config_blockers: list[Any]
    config_warnings: list[Any]
    session_blockers: list[Any]
    session_warnings: list[Any]
    backend_blockers: list[Any]
    backend_warnings: list[Any]
    control_blockers: list[Any]
    control_warnings: list[Any]
    bridge_blockers: list[Any]
    bridge_warnings: list[Any]


def join_lines(lines: list[str], fallback: str = "-") -> str:
    cleaned = [str(line) for line in lines if str(line).strip()]
    return "\n".join(cleaned) if cleaned else fallback


def html_summary(lines: list[tuple[str, str]]) -> str:
    return "".join(
        f"<p><span style='color:#6B7280;'>{escape(str(key))}</span><br>"
        f"<span style='color:#111827; font-weight:700;'>{escape(str(value))}</span></p>"
        for key, value in lines
    )


def set_text_edit_plain_preserve_scroll(editor: Any, content: str) -> None:
    _set_text_edit_content_preserve_scroll(editor, content, mode="plain")


def set_text_edit_html_preserve_scroll(editor: Any, content: str) -> None:
    _set_text_edit_content_preserve_scroll(editor, content, mode="html")


def _set_text_edit_content_preserve_scroll(editor: Any, content: str, *, mode: str) -> None:
    cache_key = f"_presenter_last_{mode}"
    if hasattr(editor, "property") and editor.property(cache_key) == content:
        return

    vertical = editor.verticalScrollBar() if hasattr(editor, "verticalScrollBar") else None
    horizontal = editor.horizontalScrollBar() if hasattr(editor, "horizontalScrollBar") else None
    old_v = vertical.value() if vertical is not None else 0
    old_h = horizontal.value() if horizontal is not None else 0

    if mode == "html":
        editor.setHtml(content)
    else:
        editor.setPlainText(content)

    if hasattr(editor, "setProperty"):
        editor.setProperty(cache_key, content)

    if vertical is not None:
        vertical.setValue(min(old_v, vertical.maximum()))
    if horizontal is not None:
        horizontal.setValue(min(old_h, horizontal.maximum()))


def build_status_context(window: Any, payload: dict[str, Any]) -> StatusViewContext:
    devices = payload["devices"]
    metrics = payload["metrics"]
    current_exp = payload["current_experiment"]
    robot = payload.get("robot", {})
    safety = payload.get("safety", {})
    recording = payload.get("recording", {})
    config = payload.get("config", {})
    workflow = payload.get("workflow", {})
    readiness = payload.get("readiness", {})
    sdk_alignment = payload.get("sdk_alignment", {})
    sdk_runtime = payload.get("sdk_runtime", {})
    model_report = payload.get("model_report", {})
    config_report = payload.get("config_report", {})
    session_governance = payload.get("session_governance", {})
    backend_link = payload.get("backend_link", {})
    bridge_observability = payload.get("bridge_observability", {})
    control_plane = dict(backend_link.get("control_plane", {}))
    governance_projection = RuntimeGovernanceQuerySurface().build_projection(
        backend_link=backend_link,
        control_plane_snapshot=payload.get("control_plane_snapshot", {}),
        model_report=model_report,
        sdk_runtime=sdk_runtime,
    )
    control_authority = dict(governance_projection.get("control_authority") or control_plane.get("control_authority") or payload.get("control_authority", {}))
    persistence = payload.get("persistence", {})
    system_state = payload["state"]
    pose = metrics["tcp_pose"]
    rl_status = dict(sdk_runtime.get("rl_status", robot.get("rl_status", {})))
    drag_status = dict(sdk_runtime.get("drag_status", robot.get("drag_state", {})))
    exp_id = current_exp["exp_id"] if current_exp else "-"
    operate_mode = robot.get("operate_mode", "-")
    readiness_percent = int(readiness.get("percent", 0))
    readiness_state = window._readiness_state(readiness_percent)
    recommended_label = readiness.get("recommended_label", "等待系统满足条件")
    recommended_reason = readiness.get("recommended_reason", "请先排除阻塞项。")
    recommended_tab = readiness.get("recommended_tab", "系统总览")
    blockers = readiness.get("blockers", [])
    sdk_blockers = sdk_alignment.get("blockers", [])
    sdk_warnings = sdk_alignment.get("warnings", [])
    model_blockers = model_report.get("blockers", [])
    model_warnings = model_report.get("warnings", [])
    config_blockers = config_report.get("blockers", [])
    config_warnings = config_report.get("warnings", [])
    session_blockers = session_governance.get("blockers", [])
    session_warnings = session_governance.get("warnings", [])
    backend_blockers = backend_link.get("blockers", [])
    backend_warnings = backend_link.get("warnings", [])
    control_blockers = control_plane.get("blockers", [])
    control_warnings = control_plane.get("warnings", [])
    bridge_blockers = bridge_observability.get("blockers", [])
    bridge_warnings = bridge_observability.get("warnings", [])
    return StatusViewContext(
        payload=payload,
        window=window,
        devices=devices,
        metrics=metrics,
        current_exp=current_exp,
        robot=robot,
        safety=safety,
        recording=recording,
        config=config,
        workflow=workflow,
        readiness=readiness,
        sdk_alignment=sdk_alignment,
        sdk_runtime=sdk_runtime,
        model_report=model_report,
        config_report=config_report,
        session_governance=session_governance,
        backend_link=backend_link,
        bridge_observability=bridge_observability,
        control_plane={**control_plane, "authoritative_projection": dict(governance_projection)},
        control_authority=control_authority,
        persistence=persistence,
        system_state=system_state,
        pose=pose,
        rl_status=rl_status,
        drag_status=drag_status,
        exp_id=exp_id,
        operate_mode=operate_mode,
        readiness_percent=readiness_percent,
        readiness_state=readiness_state,
        recommended_label=recommended_label,
        recommended_reason=recommended_reason,
        recommended_tab=recommended_tab,
        blockers=blockers,
        sdk_blockers=sdk_blockers,
        sdk_warnings=sdk_warnings,
        model_blockers=model_blockers,
        model_warnings=model_warnings,
        config_blockers=config_blockers,
        config_warnings=config_warnings,
        session_blockers=session_blockers,
        session_warnings=session_warnings,
        backend_blockers=backend_blockers,
        backend_warnings=backend_warnings,
        control_blockers=control_blockers,
        control_warnings=control_warnings,
        bridge_blockers=bridge_blockers,
        bridge_warnings=bridge_warnings,
    )
