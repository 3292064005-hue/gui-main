from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text


def build_quality_timeline(service, session_dir: Path) -> Path:
    manifest = service.exp_manager.load_manifest(session_dir)
    quality_entries = service._read_jsonl(session_dir / "raw" / "ui" / "quality_feedback.jsonl")
    contact_entries = service._read_jsonl(session_dir / "raw" / "core" / "contact_state.jsonl")
    progress_entries = service._read_jsonl(session_dir / "raw" / "core" / "scan_progress.jsonl")
    stale_threshold_ms = int(manifest.get("safety_thresholds", {}).get("stale_telemetry_ms", 250))
    last_ts = 0
    points = []
    for index, entry in enumerate(quality_entries):
        ts_ns = int(entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0))
        payload = dict(entry.get("data", {}))
        contact = contact_entries[min(index, len(contact_entries) - 1)]["data"] if contact_entries else {}
        progress = progress_entries[min(index, len(progress_entries) - 1)]["data"] if progress_entries else {}
        delta_ms = 0 if last_ts == 0 else max(0, int((ts_ns - last_ts) / 1_000_000))
        last_ts = ts_ns
        points.append({
            "seq": int(entry.get("seq", 0)), "ts_ns": ts_ns,
            "image_quality": float(payload.get("image_quality", 0.0)),
            "feature_confidence": float(payload.get("feature_confidence", 0.0)),
            "quality_score": float(payload.get("quality_score", 0.0)),
            "coverage_score": round(min(1.0, float(progress.get("progress_pct", progress.get("overall_progress", 0.0))) / 100.0), 4),
            "contact_confidence": float(contact.get("confidence", 0.0)),
            "pressure_current": float(contact.get("pressure_current", 0.0)),
            "need_resample": bool(payload.get("need_resample", False)),
            "stale_telemetry": delta_ms > stale_threshold_ms,
            "delta_ms": delta_ms,
            "stale_threshold_ms": stale_threshold_ms,
            "force_status": str(contact.get("recommended_action", "IDLE")),
            "segment_id": int(progress.get("active_segment", 0)),
        })
    quality_scores = [point["quality_score"] for point in points]
    payload = {"generated_at": now_text(), "session_id": manifest["session_id"], "sample_count": len(points), "points": points, "summary": {"min_quality_score": min(quality_scores) if quality_scores else 0.0, "max_quality_score": max(quality_scores) if quality_scores else 0.0, "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 4) if quality_scores else 0.0, "resample_events": sum(1 for point in points if point["need_resample"]), "coverage_ratio": round(max((point["coverage_score"] for point in points), default=0.0), 4), "stale_samples": sum(1 for point in points if point["stale_telemetry"]), "stale_threshold_ms": stale_threshold_ms}}
    return service.exp_manager.save_json_artifact(session_dir, "derived/quality/quality_timeline.json", payload)


def build_alarm_timeline(service, session_dir: Path) -> Path:
    manifest = service.exp_manager.load_manifest(session_dir)
    core_alarm_entries = service._read_jsonl(session_dir / "raw" / "core" / "alarm_event.jsonl")
    journal_entries = service._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl")
    events: list[dict[str, Any]] = []
    for entry in core_alarm_entries:
        data = dict(entry.get("data", {}))
        events.append({"severity": str(data.get("severity", "WARN")), "source": str(data.get("source", "robot_core")), "message": str(data.get("message", "")), "workflow_step": str(data.get("workflow_step", "")), "request_id": str(data.get("request_id", "")), "auto_action": str(data.get("auto_action", "")), "ts_ns": int(data.get("event_ts_ns", entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0)))})
    for entry in journal_entries:
        data = dict(entry.get("data", {})); reply = dict(data.get("reply", {}))
        if bool(reply.get("ok", True)):
            continue
        events.append({"severity": "ERROR", "source": str(data.get("source", "desktop")), "message": str(reply.get("message", "command failure")), "workflow_step": str(data.get("workflow_step", data.get("command", ""))), "request_id": str(reply.get("request_id", "")), "auto_action": str(data.get("auto_action", "")), "ts_ns": int(data.get("ts_ns", entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0)))})
    events.sort(key=lambda item: int(item.get("ts_ns", 0)))
    payload = {"generated_at": now_text(), "session_id": manifest["session_id"], "events": events, "summary": {"count": len(events), "fatal_count": sum(1 for event in events if event["severity"].upper().startswith("FATAL")), "hold_count": sum(1 for event in events if event.get("auto_action") == "hold"), "retreat_count": sum(1 for event in events if "retreat" in event.get("auto_action", ""))}}
    target = service.exp_manager.save_json_artifact(session_dir, "derived/alarms/alarm_timeline.json", payload)
    service.exp_manager.update_manifest(session_dir, alarms_summary=payload["summary"])
    return target


def build_frame_sync_index(service, session_dir: Path) -> Path:
    payload = service.sync_indexer.build(session_dir)
    return service.exp_manager.save_json_artifact(session_dir, "derived/sync/frame_sync_index.json", payload)


def build_replay_index(service, session_dir: Path) -> Path:
    manifest = service.exp_manager.load_manifest(session_dir)
    camera_entries = service._read_jsonl(session_dir / "raw" / "camera" / "index.jsonl")
    ultrasound_entries = service._read_jsonl(session_dir / "raw" / "ultrasound" / "index.jsonl")
    alarm_timeline = service._read_json(session_dir / "derived/alarms/alarm_timeline.json")
    quality_timeline = service._read_json(session_dir / "derived/quality/quality_timeline.json")
    sync_index = service._read_json(session_dir / "derived/sync/frame_sync_index.json")
    annotations = service._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
    timeline = []
    for event in alarm_timeline.get("events", []):
        timeline.append({"type": "alarm", "ts_ns": int(event.get("ts_ns", 0)), "label": f"{event.get('severity', 'WARN')} / {event.get('workflow_step', '-')}", "anchor": event.get("auto_action", "")})
    for point in quality_timeline.get("points", []):
        if float(point.get("quality_score", 1.0)) < 0.75:
            timeline.append({"type": "quality_valley", "ts_ns": int(point.get("ts_ns", 0)), "label": f"quality={float(point.get('quality_score', 0.0)):.2f}", "anchor": f"segment-{point.get('segment_id', 0)}"})
    for row in sync_index.get("rows", []):
        if row.get("annotation_refs"):
            timeline.append({"type": "sync_annotation", "ts_ns": int(row.get("ts_ns", 0)), "label": f"frame_sync annotations={len(row.get('annotation_refs', []))}", "anchor": f"frame-{row.get('frame_id', 0)}"})
    for entry in annotations:
        data = dict(entry.get("data", {}))
        timeline.append({"type": "annotation", "ts_ns": int(data.get("ts_ns", entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0))), "label": str(data.get("message", data.get("kind", "annotation"))), "anchor": str(data.get("kind", "annotation"))})
    timeline.sort(key=lambda item: int(item.get("ts_ns", 0)))
    payload = {"generated_at": now_text(), "session_id": manifest["session_id"], "channels": ["camera", "ultrasound", "robot_state", "contact_state", "pressure_sensor", "scan_progress", "alarm_event", "quality_feedback", "annotations", "frame_sync_index"], "streams": {"camera": {"index_path": "raw/camera/index.jsonl", "frame_count": len(camera_entries), "latest_frame": camera_entries[-1]["data"].get("frame_path", "") if camera_entries else ""}, "ultrasound": {"index_path": "raw/ultrasound/index.jsonl", "frame_count": len(ultrasound_entries), "latest_frame": ultrasound_entries[-1]["data"].get("frame_path", "") if ultrasound_entries else ""}, "frame_sync": {"index_path": "derived/sync/frame_sync_index.json", "frame_count": int(sync_index.get("summary", {}).get("frame_count", 0)), "usable_ratio": float(sync_index.get("summary", {}).get("usable_ratio", 0.0))}, "core_topics": [topic for topic in ["robot_state", "contact_state", "scan_progress", "alarm_event"] if (session_dir / "raw" / "core" / f"{topic}.jsonl").exists()]}, "timeline": timeline, "alarm_segments": alarm_timeline.get("events", []), "quality_segments": [{"ts_ns": int(point.get("ts_ns", 0)), "segment_id": int(point.get("segment_id", 0)), "quality_score": float(point.get("quality_score", 0.0))} for point in quality_timeline.get("points", [])], "annotation_segments": [dict(entry.get("data", {})) for entry in annotations], "frame_sync_summary": sync_index.get("summary", {}), "notable_events": timeline[:50], "artifacts": dict(manifest.get("artifacts", {}))}
    return service.exp_manager.save_json_artifact(session_dir, "replay/replay_index.json", payload)
