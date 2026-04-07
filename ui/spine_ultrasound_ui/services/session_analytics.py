from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any


class SessionAnalyticsService:
    def __init__(self, experiments_root: Path):
        self.experiments_root = experiments_root

    def compare_session(self, session_dir: Path) -> dict[str, Any]:
        current = self._session_metrics(session_dir)
        candidates = [
            self._session_metrics(candidate)
            for candidate in self._all_session_dirs()
            if candidate != session_dir and (candidate / "export" / "session_report.json").exists()
        ]
        baseline = candidates[-1] if candidates else None
        fleet = self._aggregate(candidates)
        comparison = {
            "session_id": current["session_id"],
            "baseline_session_id": baseline["session_id"] if baseline else "",
            "current": current,
            "baseline": baseline or {},
            "fleet_summary": fleet,
            "delta_vs_baseline": self._delta(current, baseline) if baseline else {},
        }
        return comparison

    def trend_summary(self, session_dir: Path, *, window: int = 5) -> dict[str, Any]:
        all_sessions = [
            self._session_metrics(candidate)
            for candidate in self._all_session_dirs()
            if (candidate / "export" / "session_report.json").exists()
        ]
        current_id = session_dir.name
        history = [item for item in all_sessions if item["session_id"] != current_id][-window:]
        current = next((item for item in all_sessions if item["session_id"] == current_id), self._session_metrics(session_dir))
        return {
            "session_id": current["session_id"],
            "history_window": window,
            "history_count": len(history),
            "history": history,
            "current": current,
            "trends": self._trend_deltas(current, history),
            "fleet_summary": self._aggregate(history),
        }

    def _all_session_dirs(self) -> list[Path]:
        paths: list[Path] = []
        if not self.experiments_root.exists():
            return paths
        for exp_dir in sorted(self.experiments_root.iterdir()):
            sessions_dir = exp_dir / "sessions"
            if not sessions_dir.exists():
                continue
            for session_dir in sorted(sessions_dir.iterdir()):
                if session_dir.is_dir():
                    paths.append(session_dir)
        return paths

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    def _session_metrics(self, session_dir: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / "meta" / "manifest.json")
        summary = self._read_json(session_dir / "export" / "summary.json")
        report = self._read_json(session_dir / "export" / "session_report.json")
        replay = self._read_json(session_dir / "replay" / "replay_index.json")
        alarms = self._read_json(session_dir / "derived" / "alarms" / "alarm_timeline.json")
        quality = self._read_json(session_dir / "derived" / "quality" / "quality_timeline.json")
        diagnostics = self._read_json(session_dir / "export" / "diagnostics_pack.json")
        sync_index = self._read_json(session_dir / "derived" / "sync" / "frame_sync_index.json")
        pressure_analysis = self._read_json(session_dir / "export" / "pressure_analysis.json")
        ultrasound_analysis = self._read_json(session_dir / "export" / "ultrasound_analysis.json")
        current = {
            "session_id": manifest.get("session_id", session_dir.name),
            "scan_duration_frames": int(replay.get("streams", {}).get("ultrasound", {}).get("frame_count", 0)),
            "alarm_count": int(alarms.get("summary", {}).get("count", 0)),
            "hold_count": int(alarms.get("summary", {}).get("hold_count", 0)),
            "retreat_count": int(alarms.get("summary", {}).get("retreat_count", 0)),
            "avg_quality_score": float(report.get("quality_summary", {}).get("avg_quality_score", 0.0)),
            "completion_ratio": float(summary.get("metrics", {}).get("scan_progress", 0.0)) / 100.0,
            "coverage_ratio": float(report.get("quality_summary", {}).get("coverage_ratio", 0.0)),
            "stale_samples": int(quality.get("summary", {}).get("stale_samples", 0)),
            "annotation_count": int(diagnostics.get("summary", {}).get("annotation_count", 0)),
            "annotation_density": round(int(diagnostics.get("summary", {}).get("annotation_count", 0)) / max(1, int(replay.get("streams", {}).get("ultrasound", {}).get("frame_count", 0))), 4),
            "usable_sync_ratio": float(sync_index.get("summary", {}).get("usable_ratio", 0.0)),
            "pressure_overpressure_count": int(pressure_analysis.get("summary", {}).get("overpressure_count", 0)),
            "pressure_stable_ratio": float(pressure_analysis.get("summary", {}).get("stable_ratio", 0.0)),
            "ultrasound_coupled_ratio": float(ultrasound_analysis.get("summary", {}).get("coupled_ratio", 0.0)),
            "force_sensor_provider": str(manifest.get("force_sensor_provider", "")),
            "software_version": str(manifest.get("software_version", "")),
            "robot_model": str(manifest.get("robot_profile", {}).get("robot_model", "")),
            "axis_count": int(manifest.get("robot_profile", {}).get("axis_count", 0) or 0),
        }
        return current

    @staticmethod
    def _aggregate(candidates: list[dict[str, Any]]) -> dict[str, Any]:
        if not candidates:
            return {"sessions": 0}
        keys = [
            "scan_duration_frames",
            "alarm_count",
            "hold_count",
            "retreat_count",
            "avg_quality_score",
            "completion_ratio",
            "coverage_ratio",
            "stale_samples",
            "annotation_count",
            "annotation_density",
            "usable_sync_ratio",
        ]
        return {
            "sessions": len(candidates),
            **{f"avg_{key}": round(mean(float(item.get(key, 0.0)) for item in candidates), 4) for key in keys},
        }

    @staticmethod
    def _delta(current: dict[str, Any], baseline: dict[str, Any] | None) -> dict[str, Any]:
        if not baseline:
            return {}
        delta: dict[str, Any] = {}
        for key, value in current.items():
            if key == "session_id" or key not in baseline:
                continue
            try:
                delta[key] = round(float(value) - float(baseline[key]), 4)
            except (TypeError, ValueError):
                continue
        return delta

    @staticmethod
    def _trend_deltas(current: dict[str, Any], history: list[dict[str, Any]]) -> dict[str, Any]:
        if not history:
            return {}
        baseline = SessionAnalyticsService._aggregate(history)
        deltas: dict[str, Any] = {}
        for key, value in current.items():
            avg_key = f"avg_{key}"
            if avg_key not in baseline:
                continue
            try:
                deltas[key] = round(float(value) - float(baseline[avg_key]), 4)
            except (TypeError, ValueError):
                continue
        return deltas
