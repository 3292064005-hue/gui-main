from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class SessionIntegrityService:
    REQUIRED_ARTIFACTS = {
        "scan_plan",
        "device_readiness",
        "xmate_profile",
        "patient_registration",
        "scan_protocol",
        "command_journal",
        "annotations",
    }

    def build(self, session_dir: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / "meta" / "manifest.json")
        registry = dict(manifest.get("artifact_registry", {}))
        artifact_rows: list[dict[str, Any]] = []
        missing: list[str] = []
        checksum_mismatch: list[str] = []
        for artifact_id, descriptor in sorted(registry.items()):
            rel_path = str(descriptor.get("path", ""))
            absolute = session_dir / rel_path if rel_path else session_dir
            exists = absolute.exists()
            checksum_expected = str(descriptor.get("checksum", ""))
            checksum_actual = self._checksum(absolute) if exists and absolute.is_file() else ""
            checksum_ok = not checksum_expected or checksum_expected == checksum_actual
            if not exists:
                missing.append(artifact_id)
            elif not checksum_ok:
                checksum_mismatch.append(artifact_id)
            artifact_rows.append(
                {
                    "artifact_id": artifact_id,
                    "path": rel_path,
                    "exists": exists,
                    "ready": bool(descriptor.get("ready", False)),
                    "checksum_expected": checksum_expected,
                    "checksum_actual": checksum_actual,
                    "checksum_ok": checksum_ok,
                    "size_bytes": int(descriptor.get("size_bytes", 0) or 0),
                    "source_stage": str(descriptor.get("source_stage", "")),
                }
            )
        for artifact_id in sorted(self.REQUIRED_ARTIFACTS):
            if artifact_id not in registry:
                missing.append(artifact_id)
        unique_missing = sorted(set(missing))
        warnings = []
        if unique_missing:
            warnings.append("missing_artifacts")
        if checksum_mismatch:
            warnings.append("checksum_mismatch")
        manifest_session_id = str(manifest.get("session_id", session_dir.name))
        scan_plan_path = session_dir / str(manifest.get("artifacts", {}).get("scan_plan", "meta/scan_plan.json"))
        scan_plan = self._read_json(scan_plan_path)
        manifest_plan_hash = str(manifest.get("scan_plan_hash", ""))
        actual_plan_hash = self._dict_hash(scan_plan) if scan_plan else ""
        plan_hash_ok = (not manifest_plan_hash) or (manifest_plan_hash == actual_plan_hash)
        if not plan_hash_ok:
            warnings.append("scan_plan_hash_mismatch")
        return {
            "session_id": manifest_session_id,
            "session_dir": str(session_dir),
            "artifacts": artifact_rows,
            "summary": {
                "artifact_count": len(artifact_rows),
                "missing_count": len(unique_missing),
                "checksum_mismatch_count": len(checksum_mismatch),
                "ready_count": sum(1 for row in artifact_rows if row["ready"]),
                "integrity_ok": not unique_missing and not checksum_mismatch and plan_hash_ok,
            },
            "manifest_consistency": {
                "manifest_session_id": manifest_session_id,
                "directory_session_id": session_dir.name,
                "session_id_match": manifest_session_id == session_dir.name,
                "scan_plan_hash_expected": manifest_plan_hash,
                "scan_plan_hash_actual": actual_plan_hash,
                "scan_plan_hash_ok": plan_hash_ok,
            },
            "missing_artifacts": unique_missing,
            "checksum_mismatch_artifacts": sorted(checksum_mismatch),
            "warnings": warnings,
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _checksum(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _dict_hash(payload: dict[str, Any]) -> str:
        return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
