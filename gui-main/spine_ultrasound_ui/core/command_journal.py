from __future__ import annotations

from typing import Any


def summarize_command_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    summary: dict[str, Any] = {}
    for key, value in payload.items():
        if key == "scan_plan" and isinstance(value, dict):
            segments = value.get("segments", [])
            waypoint_count = 0
            for segment in segments:
                if isinstance(segment, dict):
                    waypoint_count += len(segment.get("waypoints", []))
            summary[key] = {
                "plan_id": value.get("plan_id", ""),
                "session_id": value.get("session_id", ""),
                "segment_count": len(segments),
                "waypoint_count": waypoint_count,
            }
            continue
        if key == "config_snapshot" and isinstance(value, dict):
            summary[key] = {
                "pressure_target": value.get("pressure_target"),
                "tool_name": value.get("tool_name"),
                "tcp_name": value.get("tcp_name"),
                "load_kg": value.get("load_kg"),
                "force_sensor_provider": value.get("force_sensor_provider"),
            }
            continue
        if key == "device_roster" and isinstance(value, dict):
            summary[key] = {
                name: {
                    "connected": bool(device.get("connected", False)),
                    "health": str(device.get("health", "unknown")),
                }
                for name, device in value.items()
                if isinstance(device, dict)
            }
            continue
        if isinstance(value, (str, int, float, bool)) or value is None:
            summary[key] = value
            continue
        if isinstance(value, list):
            summary[key] = {"items": len(value)}
            continue
        if isinstance(value, dict):
            summary[key] = {"keys": sorted(value.keys())}
            continue
        summary[key] = str(value)
    return summary
