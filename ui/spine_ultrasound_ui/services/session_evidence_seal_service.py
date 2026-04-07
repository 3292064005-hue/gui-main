from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text


class SessionEvidenceSealService:
    """Materialize a deterministic, hash-addressed seal for a locked session."""

    IMMUTABLE_MANIFEST_FIELDS = (
        "experiment_id",
        "session_id",
        "scan_plan_hash",
        "protocol_version",
        "core_protocol_version",
        "software_version",
        "build_id",
        "force_sensor_provider",
        "planner_version",
        "registration_version",
    )

    def build(self, session_dir: Path, manifest: dict[str, Any] | None = None) -> dict[str, Any]:
        session_dir = Path(session_dir)
        resolved_manifest = dict(manifest or self._read_json(session_dir / "meta" / "manifest.json"))
        sanitized_manifest = dict(resolved_manifest)
        sanitized_artifacts = dict(sanitized_manifest.get("artifacts", {}))
        sanitized_registry = dict(sanitized_manifest.get("artifact_registry", {}))
        sanitized_artifacts.pop("session_evidence_seal", None)
        sanitized_registry.pop("session_evidence_seal", None)
        sanitized_manifest["artifacts"] = sanitized_artifacts
        sanitized_manifest["artifact_registry"] = sanitized_registry
        registry = dict(sanitized_registry)
        immutable_manifest = {key: sanitized_manifest.get(key) for key in self.IMMUTABLE_MANIFEST_FIELDS}
        registry_digest = self._hash_json(registry)
        immutable_digest = self._hash_json(immutable_manifest)
        manifest_digest = self._hash_json(sanitized_manifest)
        command_journal_path = session_dir / "raw" / "ui" / "command_journal.jsonl"
        command_journal_digest = self._hash_file(command_journal_path)
        listed_files: list[dict[str, Any]] = []
        for artifact_id, descriptor in sorted(registry.items()):
            path_value = str(dict(descriptor).get("path", ""))
            target = session_dir / path_value if path_value else None
            listed_files.append({
                "artifact_id": artifact_id,
                "path": path_value,
                "exists": bool(target and target.exists()),
                "checksum": str(dict(descriptor).get("checksum", "")) or (self._hash_file(target) if target else ""),
                "size_bytes": int(dict(descriptor).get("size_bytes", 0) or 0),
            })
        generated_at = now_text()
        seal_payload = {
            "schema": "session/session_evidence_seal_v1",
            "schema_version": 1,
            "generated_at": generated_at,
            "timestamp": generated_at,
            "producer": "session_evidence_seal_service",
            "freeze_point": "session_intelligence_refresh",
            "lineage": {"manifest_digest": manifest_digest, "immutable_manifest_digest": immutable_digest},
            "session_id": str(resolved_manifest.get("session_id", session_dir.name)),
            "immutable_manifest_fields": immutable_manifest,
            "immutable_manifest_digest": immutable_digest,
            "manifest_digest": manifest_digest,
            "artifact_registry_digest": registry_digest,
            "artifact_count": len(listed_files),
            "artifacts": listed_files,
            "command_journal_digest": command_journal_digest,
        }
        seal_payload["seal_digest"] = self._hash_json(seal_payload)
        return seal_payload

    def write(self, session_dir: Path, manifest: dict[str, Any] | None = None) -> Path:
        payload = self.build(session_dir, manifest=manifest)
        target = Path(session_dir) / "meta" / "session_evidence_seal.json"
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return target

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        return json.loads(path.read_text(encoding="utf-8"))

    @staticmethod
    def _hash_file(path: Path | None) -> str:
        if path is None or not path.exists() or not path.is_file():
            return ""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    @staticmethod
    def _hash_json(payload: Any) -> str:
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()
