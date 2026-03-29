from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState
from spine_ultrasound_ui.services.algorithms import PluginExecutor, PluginPlane, PluginRegistry
from spine_ultrasound_ui.services.diagnostics_pack_service import DiagnosticsPackService
from spine_ultrasound_ui.services.frame_sync_indexer import FrameSyncIndexer
from spine_ultrasound_ui.services.qa_pack_service import QAPackService
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_analytics import SessionAnalyticsService
from spine_ultrasound_ui.utils import now_text


class PostprocessService:
    def __init__(self, exp_manager: ExperimentManager):
        self.exp_manager = exp_manager
        self.plugins = PluginPlane()
        self.plugin_registry = PluginRegistry(self.plugins.all_plugins())
        self.plugin_executor = PluginExecutor()
        self.qa_pack_service = QAPackService()
        self.diagnostics_service = DiagnosticsPackService()
        self.analytics = SessionAnalyticsService(exp_manager.root)
        self.sync_indexer = FrameSyncIndexer()
        self.integrity_service = SessionIntegrityService()

    def preprocess(self, session_dir: Path | None) -> CapabilityStatus:
        if session_dir is None:
            return self._blocked("图像预处理")
        quality_target = self._build_quality_timeline(session_dir)
        alarms_target = self._build_alarm_timeline(session_dir)
        self.exp_manager.append_artifact(session_dir, "quality_timeline", quality_target)
        self.exp_manager.append_artifact(session_dir, "alarm_timeline", alarms_target)
        self.exp_manager.append_processing_step(
            session_dir,
            self.plugin_executor.run(
                self.plugin_registry.get("preprocess"),
                session_dir,
                {
                    "input_artifacts": ["raw/ui/quality_feedback.jsonl", "raw/core/alarm_event.jsonl", "raw/ui/annotations.jsonl"],
                    "output_artifacts": [
                        "derived/quality/quality_timeline.json",
                        "derived/alarms/alarm_timeline.json",
                    ],
                },
            ),
        )
        return CapabilityStatus(
            ready=True,
            state="AVAILABLE",
            implementation=ImplementationState.IMPLEMENTED.value,
            detail=f"质量时间线与告警时间线已生成：{quality_target.name} / {alarms_target.name}",
        )

    def reconstruct(self, session_dir: Path | None) -> CapabilityStatus:
        if session_dir is None:
            return self._blocked("局部重建")
        self._ensure_artifact(session_dir, "derived/quality/quality_timeline.json", self._build_quality_timeline)
        self._ensure_artifact(session_dir, "derived/alarms/alarm_timeline.json", self._build_alarm_timeline)
        sync_target = self._build_frame_sync_index(session_dir)
        replay_target = self._build_replay_index(session_dir)
        self.exp_manager.append_artifact(session_dir, "frame_sync_index", sync_target)
        self.exp_manager.append_artifact(session_dir, "replay_index", replay_target)
        self.exp_manager.append_processing_step(
            session_dir,
            self.plugin_executor.run(
                self.plugin_registry.get("reconstruction"),
                session_dir,
                {
                    "input_artifacts": [
                        "raw/camera/index.jsonl",
                        "raw/ultrasound/index.jsonl",
                        "raw/core/contact_state.jsonl",
                        "raw/core/scan_progress.jsonl",
                        "derived/quality/quality_timeline.json",
                        "derived/alarms/alarm_timeline.json",
                        "raw/ui/annotations.jsonl",
                    ],
                    "output_artifacts": [
                        "derived/sync/frame_sync_index.json",
                        "replay/replay_index.json",
                    ],
                },
            ),
        )
        return CapabilityStatus(
            ready=True,
            state="AVAILABLE",
            implementation=ImplementationState.IMPLEMENTED.value,
            detail=f"帧同步索引与回放索引已生成：{sync_target.name} / {replay_target.name}",
        )

    def assess(self, session_dir: Path | None) -> CapabilityStatus:
        if session_dir is None:
            return self._blocked("脊柱侧弯评估")
        self._ensure_artifact(session_dir, "derived/quality/quality_timeline.json", self._build_quality_timeline)
        self._ensure_artifact(session_dir, "derived/alarms/alarm_timeline.json", self._build_alarm_timeline)
        self._ensure_artifact(session_dir, "derived/sync/frame_sync_index.json", self._build_frame_sync_index)
        self._ensure_artifact(session_dir, "replay/replay_index.json", self._build_replay_index)
        report_target = self._build_session_report(session_dir)
        compare_target = self._build_session_compare(session_dir)
        trends_target = self._build_session_trends(session_dir)
        diagnostics_target = self._build_diagnostics_pack(session_dir)
        qa_target = self._build_qa_pack(session_dir)
        integrity_target = self._build_session_integrity(session_dir)
        self.exp_manager.append_artifact(session_dir, "session_report", report_target)
        self.exp_manager.append_artifact(session_dir, "session_compare", compare_target)
        self.exp_manager.append_artifact(session_dir, "session_trends", trends_target)
        self.exp_manager.append_artifact(session_dir, "diagnostics_pack", diagnostics_target)
        self.exp_manager.append_artifact(session_dir, "qa_pack", qa_target)
        self.exp_manager.append_artifact(session_dir, "session_integrity", integrity_target)
        self.exp_manager.append_processing_step(
            session_dir,
            self.plugin_executor.run(
                self.plugin_registry.get("assessment"),
                session_dir,
                {
                    "input_artifacts": [
                        "export/summary.json",
                        "derived/quality/quality_timeline.json",
                        "derived/alarms/alarm_timeline.json",
                        "derived/sync/frame_sync_index.json",
                        "replay/replay_index.json",
                        "raw/ui/command_journal.jsonl",
                        "raw/ui/annotations.jsonl",
                    ],
                    "output_artifacts": [
                        "export/session_report.json",
                        "export/session_compare.json",
                        "export/session_trends.json",
                        "export/diagnostics_pack.json",
                        "export/qa_pack.json",
                    ],
                },
            ),
        )
        self.exp_manager.update_manifest(
            session_dir,
            algorithm_registry={plugin.stage: {"plugin_id": plugin.plugin_id, "plugin_version": plugin.plugin_version} for plugin in self.plugins.all_plugins()},
        )
        return CapabilityStatus(
            ready=True,
            state="AVAILABLE",
            implementation=ImplementationState.IMPLEMENTED.value,
            detail=f"会话报告、对比分析、趋势分析、诊断包与 QA 包已生成：{report_target.name}",
        )

    def refresh_all(self, session_dir: Path | None) -> dict[str, CapabilityStatus]:
        return {
            "preprocess": self.preprocess(session_dir),
            "reconstruction": self.reconstruct(session_dir),
            "assessment": self.assess(session_dir),
        }

    def _build_session_integrity(self, session_dir: Path) -> Path:
        payload = self.integrity_service.build(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/session_integrity.json", payload)

    @staticmethod
    def _blocked(label: str) -> CapabilityStatus:
        return CapabilityStatus(
            ready=False,
            state="BLOCKED",
            implementation=ImplementationState.IMPLEMENTED.value,
            detail=f"{label}需要先完成一次有效会话。",
        )

    def _ensure_artifact(self, session_dir: Path, relative_path: str, builder) -> Path:
        target = session_dir / relative_path
        if target.exists():
            return target
        return builder(session_dir)

    def _build_quality_timeline(self, session_dir: Path) -> Path:
        manifest = self.exp_manager.load_manifest(session_dir)
        quality_entries = self._read_jsonl(session_dir / "raw" / "ui" / "quality_feedback.jsonl")
        contact_entries = self._read_jsonl(session_dir / "raw" / "core" / "contact_state.jsonl")
        progress_entries = self._read_jsonl(session_dir / "raw" / "core" / "scan_progress.jsonl")
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
            points.append(
                {
                    "seq": int(entry.get("seq", 0)),
                    "ts_ns": ts_ns,
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
                }
            )
        quality_scores = [point["quality_score"] for point in points]
        payload = {
            "generated_at": now_text(),
            "session_id": manifest["session_id"],
            "sample_count": len(points),
            "points": points,
            "summary": {
                "min_quality_score": min(quality_scores) if quality_scores else 0.0,
                "max_quality_score": max(quality_scores) if quality_scores else 0.0,
                "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 4) if quality_scores else 0.0,
                "resample_events": sum(1 for point in points if point["need_resample"]),
                "coverage_ratio": round(max((point["coverage_score"] for point in points), default=0.0), 4),
                "stale_samples": sum(1 for point in points if point["stale_telemetry"]),
                "stale_threshold_ms": stale_threshold_ms,
            },
        }
        return self.exp_manager.save_json_artifact(session_dir, "derived/quality/quality_timeline.json", payload)

    def _build_alarm_timeline(self, session_dir: Path) -> Path:
        manifest = self.exp_manager.load_manifest(session_dir)
        core_alarm_entries = self._read_jsonl(session_dir / "raw" / "core" / "alarm_event.jsonl")
        journal_entries = self._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl")
        events: list[dict[str, Any]] = []
        for entry in core_alarm_entries:
            data = dict(entry.get("data", {}))
            events.append(
                {
                    "severity": str(data.get("severity", "WARN")),
                    "source": str(data.get("source", "robot_core")),
                    "message": str(data.get("message", "")),
                    "workflow_step": str(data.get("workflow_step", "")),
                    "request_id": str(data.get("request_id", "")),
                    "auto_action": str(data.get("auto_action", "")),
                    "ts_ns": int(data.get("event_ts_ns", entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0))),
                }
            )
        for entry in journal_entries:
            data = dict(entry.get("data", {}))
            reply = dict(data.get("reply", {}))
            if bool(reply.get("ok", True)):
                continue
            events.append(
                {
                    "severity": "ERROR",
                    "source": str(data.get("source", "desktop")),
                    "message": str(reply.get("message", "command failure")),
                    "workflow_step": str(data.get("workflow_step", data.get("command", ""))),
                    "request_id": str(reply.get("request_id", "")),
                    "auto_action": str(data.get("auto_action", "")),
                    "ts_ns": int(data.get("ts_ns", entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0))),
                }
            )
        events.sort(key=lambda item: int(item.get("ts_ns", 0)))
        payload = {
            "generated_at": now_text(),
            "session_id": manifest["session_id"],
            "events": events,
            "summary": {
                "count": len(events),
                "fatal_count": sum(1 for event in events if event["severity"].upper().startswith("FATAL")),
                "hold_count": sum(1 for event in events if event.get("auto_action") == "hold"),
                "retreat_count": sum(1 for event in events if "retreat" in event.get("auto_action", "")),
            },
        }
        target = self.exp_manager.save_json_artifact(session_dir, "derived/alarms/alarm_timeline.json", payload)
        self.exp_manager.update_manifest(session_dir, alarms_summary=payload["summary"])
        return target

    def _build_frame_sync_index(self, session_dir: Path) -> Path:
        payload = self.sync_indexer.build(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "derived/sync/frame_sync_index.json", payload)

    def _build_replay_index(self, session_dir: Path) -> Path:
        manifest = self.exp_manager.load_manifest(session_dir)
        camera_entries = self._read_jsonl(session_dir / "raw" / "camera" / "index.jsonl")
        ultrasound_entries = self._read_jsonl(session_dir / "raw" / "ultrasound" / "index.jsonl")
        alarm_timeline = self._read_json(session_dir / "derived/alarms/alarm_timeline.json")
        quality_timeline = self._read_json(session_dir / "derived/quality/quality_timeline.json")
        sync_index = self._read_json(session_dir / "derived/sync/frame_sync_index.json")
        annotations = self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
        timeline = []
        for event in alarm_timeline.get("events", []):
            timeline.append(
                {
                    "type": "alarm",
                    "ts_ns": int(event.get("ts_ns", 0)),
                    "label": f"{event.get('severity', 'WARN')} / {event.get('workflow_step', '-')}",
                    "anchor": event.get("auto_action", ""),
                }
            )
        for point in quality_timeline.get("points", []):
            if float(point.get("quality_score", 1.0)) < 0.75:
                timeline.append(
                    {
                        "type": "quality_valley",
                        "ts_ns": int(point.get("ts_ns", 0)),
                        "label": f"quality={float(point.get('quality_score', 0.0)):.2f}",
                        "anchor": f"segment-{point.get('segment_id', 0)}",
                    }
                )
        for row in sync_index.get("rows", []):
            if row.get("annotation_refs"):
                timeline.append(
                    {
                        "type": "sync_annotation",
                        "ts_ns": int(row.get("ts_ns", 0)),
                        "label": f"frame_sync annotations={len(row.get('annotation_refs', []))}",
                        "anchor": f"frame-{row.get('frame_id', 0)}",
                    }
                )
        for entry in annotations:
            data = dict(entry.get("data", {}))
            timeline.append(
                {
                    "type": "annotation",
                    "ts_ns": int(data.get("ts_ns", entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0))),
                    "label": str(data.get("message", data.get("kind", "annotation"))),
                    "anchor": str(data.get("kind", "annotation")),
                }
            )
        timeline.sort(key=lambda item: int(item.get("ts_ns", 0)))
        payload = {
            "generated_at": now_text(),
            "session_id": manifest["session_id"],
            "channels": ["camera", "ultrasound", "robot_state", "contact_state", "scan_progress", "alarm_event", "quality_feedback", "annotations", "frame_sync_index"],
            "streams": {
                "camera": {
                    "index_path": "raw/camera/index.jsonl",
                    "frame_count": len(camera_entries),
                    "latest_frame": camera_entries[-1]["data"].get("frame_path", "") if camera_entries else "",
                },
                "ultrasound": {
                    "index_path": "raw/ultrasound/index.jsonl",
                    "frame_count": len(ultrasound_entries),
                    "latest_frame": ultrasound_entries[-1]["data"].get("frame_path", "") if ultrasound_entries else "",
                },
                "frame_sync": {
                    "index_path": "derived/sync/frame_sync_index.json",
                    "frame_count": int(sync_index.get("summary", {}).get("frame_count", 0)),
                    "usable_ratio": float(sync_index.get("summary", {}).get("usable_ratio", 0.0)),
                },
                "core_topics": [
                    topic
                    for topic in ["robot_state", "contact_state", "scan_progress", "alarm_event"]
                    if (session_dir / "raw" / "core" / f"{topic}.jsonl").exists()
                ],
            },
            "timeline": timeline,
            "alarm_segments": alarm_timeline.get("events", []),
            "quality_segments": [
                {
                    "ts_ns": int(point.get("ts_ns", 0)),
                    "segment_id": int(point.get("segment_id", 0)),
                    "quality_score": float(point.get("quality_score", 0.0)),
                }
                for point in quality_timeline.get("points", [])
            ],
            "annotation_segments": [dict(entry.get("data", {})) for entry in annotations],
            "frame_sync_summary": sync_index.get("summary", {}),
            "notable_events": timeline[:50],
            "artifacts": dict(manifest.get("artifacts", {})),
        }
        return self.exp_manager.save_json_artifact(session_dir, "replay/replay_index.json", payload)

    def _build_session_report(self, session_dir: Path) -> Path:
        manifest = self.exp_manager.load_manifest(session_dir)
        summary = self._read_json(session_dir / "export" / "summary.json")
        quality_timeline = self._read_json(session_dir / "derived/quality/quality_timeline.json")
        replay_index = self._read_json(session_dir / "replay/replay_index.json")
        alarms = self._read_json(session_dir / "derived/alarms/alarm_timeline.json")
        sync_index = self._read_json(session_dir / "derived/sync/frame_sync_index.json")
        journal_entries = self._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl")
        annotations = self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
        payload = {
            "generated_at": now_text(),
            "experiment_id": manifest["experiment_id"],
            "session_id": manifest["session_id"],
            "session_overview": {
                "core_state": summary.get("core_state", "UNKNOWN"),
                "software_version": manifest.get("software_version", ""),
                "build_id": manifest.get("build_id", ""),
                "force_sensor_provider": manifest.get("force_sensor_provider", ""),
                "robot_model": manifest.get("robot_profile", {}).get("robot_model", ""),
                "sdk_robot_class": manifest.get("robot_profile", {}).get("sdk_robot_class", ""),
                "axis_count": manifest.get("robot_profile", {}).get("axis_count", 0),
            },
            "workflow_trace": {
                **summary.get("workflow", {}),
                "patient_registration": manifest.get("patient_registration", {}),
                "scan_protocol": manifest.get("scan_protocol", {}),
            },
            "safety_summary": {
                **summary.get("safety", {}),
                "alarms": alarms.get("summary", {}),
                "safety_thresholds": manifest.get("safety_thresholds", {}),
                "contact_force_policy": manifest.get("robot_profile", {}).get("clinical_scan_contract", {}).get("contact_force_policy", {}),
            },
            "recording": summary.get("recording", {}),
            "quality_summary": {
                **quality_timeline.get("summary", {}),
                "annotation_count": len(annotations),
                "usable_sync_ratio": sync_index.get("summary", {}).get("usable_ratio", 0.0),
            },
            "operator_actions": {
                "command_count": len(journal_entries),
                "latest_command": journal_entries[-1].get("data", {}).get("command", "") if journal_entries else "",
                "annotation_count": len(annotations),
            },
            "devices": {
                **manifest.get("device_health_snapshot", {}),
                "device_readiness": manifest.get("device_readiness", {}),
                "robot_profile": manifest.get("robot_profile", {}),
            },
            "outputs": manifest.get("artifact_registry", {}),
            "replay": {
                "camera_frames": replay_index.get("streams", {}).get("camera", {}).get("frame_count", 0),
                "ultrasound_frames": replay_index.get("streams", {}).get("ultrasound", {}).get("frame_count", 0),
                "synced_frames": sync_index.get("summary", {}).get("frame_count", 0),
                "timeline_points": len(replay_index.get("timeline", [])),
            },
            "algorithm_versions": {plugin.stage: plugin.plugin_version for plugin in self.plugins.all_plugins()},
            "open_issues": [
                "Reconstruction algorithm body remains replaceable; this report covers clinical data products only.",
                "Cobb assessment algorithm remains plugin-ready and is not hard-bound in this session output.",
            ],
        }
        return self.exp_manager.save_json_artifact(session_dir, "export/session_report.json", payload)

    def _build_session_compare(self, session_dir: Path) -> Path:
        payload = self.analytics.compare_session(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/session_compare.json", payload)

    def _build_session_trends(self, session_dir: Path) -> Path:
        payload = self.analytics.trend_summary(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/session_trends.json", payload)

    def _build_diagnostics_pack(self, session_dir: Path) -> Path:
        payload = self.diagnostics_service.build(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/diagnostics_pack.json", payload)

    def _build_qa_pack(self, session_dir: Path) -> Path:
        payload = self.qa_pack_service.build(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/qa_pack.json", payload)

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        entries: list[dict[str, Any]] = []
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            entries.append(json.loads(line))
        return entries

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))
