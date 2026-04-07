from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urlparse, urlunparse


@dataclass
class BackendLinkMetrics:
    commands_sent: int = 0
    commands_failed: int = 0
    last_command: str = ""
    last_error: str = ""
    telemetry_connected: bool = False
    camera_connected: bool = False
    ultrasound_connected: bool = False
    rest_reachable: bool = False
    using_websocket_telemetry: bool = False
    using_websocket_media: bool = False
    reconnect_count: int = 0
    last_command_latency_ms: int | None = None
    last_status_poll_ns: int = 0


class BackendLinkService:
    def normalize_http_base(self, value: str) -> str:
        raw = (value or "").strip()
        if not raw:
            raw = "http://127.0.0.1:8000"
        if "://" not in raw:
            raw = f"http://{raw}"
        parsed = urlparse(raw)
        scheme = parsed.scheme or "http"
        netloc = parsed.netloc or parsed.path
        path = parsed.path if parsed.netloc else ""
        normalized_path = path.rstrip("/")
        return urlunparse((scheme, netloc, normalized_path, "", "", ""))

    def infer_ws_base(self, http_base: str) -> str:
        normalized = self.normalize_http_base(http_base)
        parsed = urlparse(normalized)
        ws_scheme = "wss" if parsed.scheme == "https" else "ws"
        return urlunparse((ws_scheme, parsed.netloc, parsed.path.rstrip("/"), "", "", ""))

    def build_snapshot(
        self,
        *,
        mode: str,
        http_base: str,
        ws_base: str,
        status: dict[str, Any] | None = None,
        health: dict[str, Any] | None = None,
        metrics: BackendLinkMetrics | None = None,
        extra_errors: list[str] | None = None,
        control_plane: dict[str, Any] | None = None,
        local_runtime_config: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        status = dict(status or {})
        health = dict(health or {})
        metrics = metrics or BackendLinkMetrics()
        control_plane = dict(control_plane or {})
        local_runtime_config = dict(local_runtime_config or {})
        errors = [str(item) for item in (extra_errors or []) if str(item).strip()]
        if metrics.last_error:
            errors.append(metrics.last_error)
        telemetry_age = health.get("latest_telemetry_age_ms")
        adapter_running = bool(health.get("adapter_running", False))
        telemetry_stale = bool(health.get("telemetry_stale", False)) if telemetry_age is not None else True
        command_failures = int(metrics.commands_failed)
        commands_sent = int(metrics.commands_sent)
        command_success_rate = 100 if commands_sent <= 0 else int(round(((commands_sent - command_failures) / commands_sent) * 100))

        blockers: list[dict[str, str]] = []
        warnings: list[dict[str, str]] = []

        if not metrics.rest_reachable:
            blockers.append({"name": "REST 网关不可达", "detail": f"当前无法访问 {http_base}"})
        if adapter_running is False and metrics.rest_reachable:
            blockers.append({"name": "后端适配器未运行", "detail": "Headless adapter 未进入运行态。"})
        if not metrics.telemetry_connected:
            blockers.append({"name": "遥测通道未连通", "detail": "前端尚未建立实时遥测链路。"})
        elif telemetry_stale:
            warnings.append({"name": "遥测数据陈旧", "detail": f"最新遥测已 {telemetry_age} ms 未更新。"})
        if command_success_rate < 100 and commands_sent > 0:
            warnings.append({"name": "命令成功率下降", "detail": f"当前命令成功率 {command_success_rate}%（{command_failures}/{commands_sent} 失败）。"})
        if metrics.using_websocket_media and (not metrics.camera_connected or not metrics.ultrasound_connected):
            warnings.append({"name": "媒体流部分未连通", "detail": "camera/ultrasound WebSocket 仍有未连接流。"})
        for item in control_plane.get("blockers", []):
            if isinstance(item, dict):
                blockers.append({"name": str(item.get("name", "控制面阻塞")), "detail": str(item.get("detail", ""))})
        for item in control_plane.get("warnings", []):
            if isinstance(item, dict):
                warnings.append({"name": str(item.get("name", "控制面告警")), "detail": str(item.get("detail", ""))})
        if errors:
            warnings.append({"name": "链路异常记录", "detail": errors[-1]})

        if blockers:
            summary_state = "blocked"
            summary_label = "前后端链路阻塞"
        elif warnings:
            summary_state = "degraded"
            summary_label = "前后端链路降级"
        else:
            summary_state = "ready"
            summary_label = "前后端链路在线"

        detail_parts = [
            f"REST={'UP' if metrics.rest_reachable else 'DOWN'}",
            f"adapter={'RUN' if adapter_running else 'STOP'}",
            f"telemetry={'WS' if metrics.using_websocket_telemetry else 'POLL'}:{'ON' if metrics.telemetry_connected else 'OFF'}",
            f"camera={'ON' if metrics.camera_connected else 'OFF'}",
            f"ultrasound={'ON' if metrics.ultrasound_connected else 'OFF'}",
            f"cmd_ok={command_success_rate}%",
        ]
        if telemetry_age is not None:
            detail_parts.append(f"telemetry_age={telemetry_age}ms")
        if control_plane:
            detail_parts.append(f"control={control_plane.get('summary_label', '-')}")
            cfg = control_plane.get("config_sync", {})
            proto = control_plane.get("protocol_status", {})
            topics = control_plane.get("topic_coverage", {})
            if cfg:
                detail_parts.append(f"cfg={cfg.get('summary_label', '-')}")
            if proto:
                detail_parts.append(f"proto={proto.get('summary_label', '-')}")
            if topics:
                detail_parts.append(f"topics={topics.get('coverage_percent', 0)}%")

        return {
            "mode": mode,
            "summary_state": summary_state,
            "summary_label": summary_label,
            "detail": " / ".join(detail_parts),
            "http_base": self.normalize_http_base(http_base),
            "ws_base": ws_base,
            "status": status,
            "health": health,
            "commands_sent": commands_sent,
            "commands_failed": command_failures,
            "command_success_rate": command_success_rate,
            "telemetry_connected": metrics.telemetry_connected,
            "camera_connected": metrics.camera_connected,
            "ultrasound_connected": metrics.ultrasound_connected,
            "rest_reachable": metrics.rest_reachable,
            "using_websocket_telemetry": metrics.using_websocket_telemetry,
            "using_websocket_media": metrics.using_websocket_media,
            "reconnect_count": metrics.reconnect_count,
            "last_command": metrics.last_command,
            "last_command_latency_ms": metrics.last_command_latency_ms,
            "blockers": blockers,
            "warnings": warnings,
            "errors": errors[-5:],
            "command_endpoint": status.get("command_endpoint", ""),
            "telemetry_endpoint": status.get("telemetry_endpoint", ""),
            "backend_mode": status.get("backend_mode", mode),
            "execution_state": status.get("execution_state", health.get("execution_state", "BOOT")),
            "session_id": status.get("session_id", ""),
            "control_plane": control_plane,
            "local_runtime_config": local_runtime_config,
        }
