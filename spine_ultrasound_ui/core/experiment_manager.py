from __future__ import annotations

import json
import platform
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from spine_ultrasound_ui.models import ScanPlan, SessionManifest
from spine_ultrasound_ui.utils import ensure_dir, now_text


class ExperimentManager:
    def __init__(self, root: Path):
        self.root = ensure_dir(root)

    def make_experiment_id(self) -> str:
        year = now_text()[:4]
        idx = 1
        while True:
            exp_id = f"EXP_{year}_{idx:04d}"
            if not (self.root / exp_id).exists():
                return exp_id
            idx += 1

    def make_session_id(self, exp_id: str) -> str:
        idx = 1
        while True:
            session_id = f"{exp_id}_S{idx:03d}"
            if not (self.root / exp_id / "sessions" / session_id).exists():
                return session_id
            idx += 1

    def create(self, config_snapshot: dict, note: str = "") -> dict:
        exp_id = self.make_experiment_id()
        exp_dir = ensure_dir(self.root / exp_id)
        for p in ["meta", "sessions", "derived", "export", "replay"]:
            ensure_dir(exp_dir / p)
        metadata = {
            "experiment_id": exp_id,
            "created_at": now_text(),
            "note": note,
            "software": {"platform": platform.platform()},
            "config_snapshot": config_snapshot,
            "state": "CREATED",
        }
        (exp_dir / "meta" / "experiment.json").write_text(json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8")
        return {"exp_id": exp_id, "save_dir": str(exp_dir), "metadata": metadata}

    def save_preview_plan(self, exp_id: str, plan: ScanPlan) -> Path:
        exp_dir = self.root / exp_id
        target = exp_dir / "derived" / "preview" / "scan_plan_preview.json"
        ensure_dir(target.parent)
        target.write_text(json.dumps(plan.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def lock_session(
        self,
        exp_id: str,
        config_snapshot: Dict[str, Any],
        device_roster: Dict[str, Any],
        software_version: str,
        build_id: str,
        scan_plan: ScanPlan,
        *,
        protocol_version: int,
        force_sensor_provider: str,
        safety_thresholds: Dict[str, Any],
        device_health_snapshot: Dict[str, Any],
    ) -> dict:
        exp_dir = self.root / exp_id
        session_id = self.make_session_id(exp_id)
        session_dir = ensure_dir(exp_dir / "sessions" / session_id)
        for p in [
            "meta",
            "raw/core",
            "raw/camera/frames",
            "raw/ultrasound/frames",
            "raw/ui",
            "derived/preview",
            "derived/keyframes",
            "derived/reconstruction",
            "derived/assessment",
            "replay",
            "export",
        ]:
            ensure_dir(session_dir / p)
        final_plan = scan_plan.with_session(session_id, plan_id=f"PLAN_{session_id}")
        manifest = SessionManifest(
            experiment_id=exp_id,
            session_id=session_id,
            config_snapshot=config_snapshot,
            scan_plan_hash=final_plan.plan_hash(),
            device_roster=device_roster,
            software_version=software_version,
            build_id=build_id,
            protocol_version=protocol_version,
            force_sensor_provider=force_sensor_provider,
            safety_thresholds=safety_thresholds,
            device_health_snapshot=device_health_snapshot,
            artifacts={"scan_plan": "meta/scan_plan.json"},
        )
        self._write_manifest(session_dir, manifest)
        (session_dir / "meta" / "scan_plan.json").write_text(
            json.dumps(final_plan.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        return {
            "session_id": session_id,
            "session_dir": str(session_dir),
            "manifest": manifest.to_dict(),
            "scan_plan": final_plan.to_dict(),
        }

    def append_artifact(self, session_dir: Path, name: str, artifact_path: Path) -> dict:
        manifest = self.load_manifest(session_dir)
        artifacts = dict(manifest.get("artifacts", {}))
        artifacts[name] = str(artifact_path.relative_to(session_dir))
        manifest["artifacts"] = artifacts
        self._write_manifest(session_dir, SessionManifest(**manifest))
        return manifest

    def load_manifest(self, session_dir: Path) -> Dict[str, Any]:
        path = session_dir / "meta" / "manifest.json"
        return json.loads(path.read_text(encoding="utf-8"))

    def save_summary(self, session_dir: Path, payload: Dict[str, Any]) -> Path:
        target = session_dir / "export" / "summary.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def save_json_artifact(self, session_dir: Path, relative_path: str, payload: Dict[str, Any]) -> Path:
        target = session_dir / relative_path
        ensure_dir(target.parent)
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    def load_json_artifact(self, session_dir: Path, relative_path: str) -> Dict[str, Any]:
        target = session_dir / relative_path
        return json.loads(target.read_text(encoding="utf-8"))

    def _write_manifest(self, session_dir: Path, manifest: SessionManifest) -> None:
        path = session_dir / "meta" / "manifest.json"
        path.write_text(json.dumps(asdict(manifest), indent=2, ensure_ascii=False), encoding="utf-8")
