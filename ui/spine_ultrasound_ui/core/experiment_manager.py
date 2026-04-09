from __future__ import annotations

import hashlib
import json
import mimetypes
import platform
from dataclasses import asdict
from pathlib import Path
from typing import Any, Dict

from spine_ultrasound_ui.models import ArtifactDescriptor, ProcessingStepRecord, ScanPlan, SessionManifest
from spine_ultrasound_ui.utils import ensure_dir, now_text
from spine_ultrasound_ui.core.artifact_path_policy import infer_dependencies, infer_source_stage
from spine_ultrasound_ui.core.artifact_schema_registry import schema_for_artifact
from spine_ultrasound_ui.contracts.schema_validator import validate_payload_against_schema


ENFORCED_CANONICAL_JSON_ARTIFACTS = {
    "device_readiness",
    "xmate_profile",
    "patient_registration",
    "localization_readiness",
    "calibration_bundle",
    "localization_freeze",
    "manual_adjustment",
    "source_frame_set",
    "localization_replay_index",
    "registration_candidate",
    "back_roi",
    "midline_polyline",
    "landmarks",
    "body_surface",
    "guidance_targets",
    "scan_protocol",
}

MANIFEST_CANONICAL_PAYLOAD_TO_ARTIFACT = {
    "device_readiness": "device_readiness",
    "robot_profile": "xmate_profile",
    "patient_registration": "patient_registration",
    "localization_readiness": "localization_readiness",
    "calibration_bundle": "calibration_bundle",
    "localization_freeze": "localization_freeze",
    "manual_adjustment": "manual_adjustment",
    "source_frame_set": "source_frame_set",
    "scan_protocol": "scan_protocol",
}

MANIFEST_CANONICAL_HASH_TO_PAYLOAD = {
    "robot_profile_hash": ("robot_profile", ()),
    "patient_registration_hash": ("patient_registration", ("registration_hash",)),
    "localization_readiness_hash": ("localization_readiness", ("readiness_hash",)),
    "calibration_bundle_hash": ("calibration_bundle", ("bundle_hash",)),
    "localization_freeze_hash": ("localization_freeze", ("freeze_hash",)),
    "manual_adjustment_hash": ("manual_adjustment", ("hash",)),
    "source_frame_set_hash": ("source_frame_set", ("source_frame_set_hash",)),
}

PROTECTED_MANIFEST_CANONICAL_FIELDS = set(MANIFEST_CANONICAL_PAYLOAD_TO_ARTIFACT) | set(MANIFEST_CANONICAL_HASH_TO_PAYLOAD)


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
        protocol_version: int = 1,
        planner_version: str = "deterministic_planner_v2",
        registration_version: str = "camera_backed_registration_v2",
        core_protocol_version: int = 1,
        frontend_build_id: str = "",
        environment_snapshot: Dict[str, Any] | None = None,
        force_control_hash: str = "",
        robot_profile_hash: str = "",
        patient_registration_hash: str = "",
        localization_readiness_hash: str = "",
        calibration_bundle_hash: str = "",
        localization_freeze_hash: str = "",
        manual_adjustment_hash: str = "",
        source_frame_set_hash: str = "",
        guidance_version: str = "camera_guidance_v1",
        guidance_mode: str = "guidance_only",
        guidance_source_type: str = "",
        force_sensor_provider: str = "mock_force_sensor",
        safety_thresholds: Dict[str, Any] | None = None,
        device_health_snapshot: Dict[str, Any] | None = None,
        robot_profile: Dict[str, Any] | None = None,
        patient_registration: Dict[str, Any] | None = None,
        localization_readiness: Dict[str, Any] | None = None,
        calibration_bundle: Dict[str, Any] | None = None,
        localization_freeze: Dict[str, Any] | None = None,
        manual_adjustment: Dict[str, Any] | None = None,
        source_frame_set: Dict[str, Any] | None = None,
        scan_protocol: Dict[str, Any] | None = None,
        control_authority: Dict[str, Any] | None = None,
        guidance_algorithm_registry: Dict[str, Any] | None = None,
        guidance_processing_steps: list[Dict[str, Any]] | None = None,
    ) -> dict:
        exp_dir = self.root / exp_id
        session_id = self.make_session_id(exp_id)
        session_dir = ensure_dir(exp_dir / "sessions" / session_id)
        for p in [
            "meta",
            "raw/core",
            "raw/camera/frames",
            "raw/ultrasound/frames",
            "raw/pressure",
            "raw/ui",
            "derived/preview",
            "derived/keyframes",
            "derived/reconstruction",
            "derived/assessment",
            "derived/ultrasound",
            "derived/pressure",
            "derived/quality",
            "derived/alarms",
            "replay",
            "export",
        ]:
            ensure_dir(session_dir / p)
        final_plan = scan_plan.with_session(session_id, plan_id=f"PLAN_{session_id}")
        readiness_payload = {"ready_to_lock": True}
        manifest = SessionManifest(
            experiment_id=exp_id,
            session_id=session_id,
            created_at=now_text(),
            config_snapshot=config_snapshot,
            scan_plan_hash=final_plan.plan_hash(),
            device_roster=device_roster,
            software_version=software_version,
            build_id=build_id,
            planner_version=planner_version,
            registration_version=registration_version,
            core_protocol_version=core_protocol_version,
            frontend_build_id=frontend_build_id,
            environment_snapshot=environment_snapshot or {},
            force_control_hash=force_control_hash,
            robot_profile_hash=robot_profile_hash,
            patient_registration_hash=patient_registration_hash,
            localization_readiness_hash=localization_readiness_hash,
            calibration_bundle_hash=calibration_bundle_hash,
            localization_freeze_hash=localization_freeze_hash,
            manual_adjustment_hash=manual_adjustment_hash,
            source_frame_set_hash=source_frame_set_hash,
            guidance_version=guidance_version,
            guidance_mode=guidance_mode,
            guidance_source_type=guidance_source_type,
            protocol_version=protocol_version,
            force_sensor_provider=force_sensor_provider,
            safety_thresholds=safety_thresholds or {},
            device_health_snapshot=device_health_snapshot or {},
            device_readiness=readiness_payload,
            robot_profile=robot_profile or {},
            patient_registration=patient_registration or {},
            localization_readiness=localization_readiness or {},
            calibration_bundle=calibration_bundle or {},
            localization_freeze=localization_freeze or {},
            manual_adjustment=manual_adjustment or {},
            source_frame_set=source_frame_set or {},
            scan_protocol=scan_protocol or {},
            guidance_algorithm_registry=guidance_algorithm_registry or {},
            guidance_processing_steps=list(guidance_processing_steps or []),
            artifacts={"scan_plan": "meta/scan_plan.json"},
            artifact_registry={
                "scan_plan": ArtifactDescriptor(
                    artifact_type="scan_plan",
                    path="meta/scan_plan.json",
                    producer="experiment_manager",
                    artifact_id="scan_plan",
                    created_at=now_text(),
                    summary="Frozen locked scan plan",
                    source_stage="workflow_lock",
                ).to_dict()
            },
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
        """Register an on-disk artifact after enforcing its declared schema.

        Args:
            session_dir: Locked session directory.
            name: Canonical artifact type.
            artifact_path: Absolute path to the JSON artifact inside the session.

        Returns:
            Updated manifest payload.

        Raises:
            RuntimeError: Raised when the artifact payload violates its declared
                schema contract.
        """
        self._validate_artifact_file(name=name, artifact_path=artifact_path)
        descriptor = self._build_artifact_descriptor(session_dir, name, artifact_path)
        return self.register_artifact(session_dir, name, descriptor)

    def register_artifact(self, session_dir: Path, name: str, descriptor: ArtifactDescriptor | Dict[str, Any]) -> dict:
        """Register an artifact descriptor after enforcing canonical schema boundaries.

        Args:
            session_dir: Locked session directory owning the artifact.
            name: Canonical artifact type.
            descriptor: Artifact descriptor payload or model.

        Returns:
            Updated manifest payload.

        Raises:
            RuntimeError: Raised when the descriptor points at a canonical JSON
                artifact that is missing on disk or violates its declared schema.
            KeyError: Raised when the descriptor does not provide a ``path``.
        """
        manifest = self.load_manifest(session_dir)
        artifacts = dict(manifest.get("artifacts", {}))
        artifact_registry = dict(manifest.get("artifact_registry", {}))
        payload = descriptor.to_dict() if isinstance(descriptor, ArtifactDescriptor) else dict(descriptor)
        payload.setdefault("artifact_id", name)
        payload.setdefault("schema", schema_for_artifact(name))
        self._validate_artifact_registration(session_dir=session_dir, name=name, payload=payload)
        artifacts[name] = payload["path"]
        artifact_registry[name] = payload
        manifest["artifacts"] = artifacts
        manifest["artifact_registry"] = artifact_registry
        self._write_manifest(session_dir, SessionManifest(**manifest))
        return manifest

    def append_processing_step(self, session_dir: Path, step: ProcessingStepRecord | Dict[str, Any]) -> dict:
        manifest = self.load_manifest(session_dir)
        steps = list(manifest.get("processing_steps", []))
        steps.append(step.to_dict() if isinstance(step, ProcessingStepRecord) else dict(step))
        manifest["processing_steps"] = steps
        self._write_manifest(session_dir, SessionManifest(**manifest))
        return manifest

    def update_manifest(self, session_dir: Path, **updates: Any) -> dict:
        """Update non-canonical manifest metadata.

        This generic update path is intentionally restricted to ordinary manifest
        metadata. Canonical artifact snapshots, their hash fields, and artifact
        registry data must flow through dedicated helpers so the repository keeps
        a single schema-enforced boundary for authoritative artifacts.

        Args:
            session_dir: Locked session directory owning the manifest.
            **updates: Top-level manifest fields to update.

        Returns:
            Updated manifest payload.

        Raises:
            RuntimeError: Raised when callers attempt to mutate artifact registry
                fields or embedded canonical snapshot/hash fields through the
                generic manifest update path.
        """
        forbidden = {
            key
            for key in (set(("artifacts", "artifact_registry")) | PROTECTED_MANIFEST_CANONICAL_FIELDS)
            if key in updates
        }
        if forbidden:
            names = ', '.join(sorted(forbidden))
            raise RuntimeError(
                'update_manifest cannot modify '
                f'{names}; use append_artifact/register_artifact for artifact registry changes '
                'and sync_canonical_manifest_fields for canonical manifest snapshots'
            )
        manifest = self.load_manifest(session_dir)
        manifest.update(updates)
        self._write_manifest(session_dir, SessionManifest(**manifest))
        return manifest

    def sync_canonical_manifest_fields(self, session_dir: Path, **updates: Any) -> dict:
        """Synchronize embedded canonical manifest snapshots with registered artifacts.

        Args:
            session_dir: Locked session directory owning the manifest.
            **updates: Canonical manifest payload fields and their companion hash
                fields. Hash-only updates are forbidden because the manifest hash
                must always be derived from the synchronized payload.

        Returns:
            Updated manifest payload.

        Raises:
            RuntimeError: Raised when callers provide unsupported fields, when a
                canonical artifact is missing, when payloads diverge from the
                registered on-disk artifact, when supplied hash fields do not
                match the payload, or when callers attempt to update a hash field
                without the corresponding payload.
        """
        unsupported = set(updates) - PROTECTED_MANIFEST_CANONICAL_FIELDS
        if unsupported:
            names = ', '.join(sorted(unsupported))
            raise RuntimeError(
                f'sync_canonical_manifest_fields only accepts canonical manifest snapshot/hash fields, got: {names}'
            )
        hash_only_fields = [
            hash_field
            for hash_field, (payload_field, _) in MANIFEST_CANONICAL_HASH_TO_PAYLOAD.items()
            if hash_field in updates and payload_field not in updates
        ]
        if hash_only_fields:
            names = ', '.join(sorted(hash_only_fields))
            raise RuntimeError(
                'sync_canonical_manifest_fields requires the matching canonical payload when updating '
                f'{names}'
            )
        manifest = self.load_manifest(session_dir)
        normalized_updates = dict(updates)
        for field_name, artifact_name in MANIFEST_CANONICAL_PAYLOAD_TO_ARTIFACT.items():
            if field_name not in normalized_updates:
                continue
            payload = normalized_updates[field_name]
            if not isinstance(payload, dict):
                raise RuntimeError(f'{field_name} must be a JSON object for canonical manifest synchronization')
            self._validate_manifest_canonical_payload(
                session_dir=session_dir,
                manifest=manifest,
                field_name=field_name,
                artifact_name=artifact_name,
                payload=payload,
            )
            for hash_field, (payload_field, preferred_keys) in MANIFEST_CANONICAL_HASH_TO_PAYLOAD.items():
                if payload_field != field_name:
                    continue
                expected_hash = self._canonical_payload_hash(payload, preferred_keys=preferred_keys)
                provided_hash = normalized_updates.get(hash_field)
                if provided_hash not in (None, "", expected_hash):
                    raise RuntimeError(
                        f'{hash_field} does not match the canonical payload for {field_name}'
                    )
                normalized_updates[hash_field] = expected_hash
        manifest.update(normalized_updates)
        self._write_manifest(session_dir, SessionManifest(**manifest))
        return manifest

    def load_manifest(self, session_dir: Path) -> Dict[str, Any]:
        path = session_dir / "meta" / "manifest.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        normalized = SessionManifest(**raw).to_dict()
        if normalized != raw:
            path.write_text(json.dumps(normalized, indent=2, ensure_ascii=False), encoding="utf-8")
        return normalized

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


    def _validate_manifest_canonical_payload(
        self,
        *,
        session_dir: Path,
        manifest: Dict[str, Any],
        field_name: str,
        artifact_name: str,
        payload: Dict[str, Any],
    ) -> None:
        """Validate embedded canonical manifest payloads against registered artifacts.

        Args:
            session_dir: Locked session directory owning the manifest.
            manifest: Current normalized manifest payload.
            field_name: Manifest field receiving the canonical payload.
            artifact_name: Canonical artifact type backing the manifest field.
            payload: Candidate manifest payload.

        Raises:
            RuntimeError: Raised when the canonical artifact is missing, when the
                payload violates its schema, or when it diverges from the
                registered artifact file on disk.
        """
        schema_name = schema_for_artifact(artifact_name)
        if schema_name:
            validate_payload_against_schema(schema_name=schema_name, payload=payload)
        relative_path = str(manifest.get('artifacts', {}).get(artifact_name, '') or '').strip()
        if not relative_path:
            raise RuntimeError(
                f'canonical manifest field {field_name} requires registered artifact {artifact_name}'
            )
        artifact_path = session_dir / relative_path
        if not artifact_path.exists() or not artifact_path.is_file():
            raise RuntimeError(
                f'canonical manifest field {field_name} is missing artifact file {artifact_path}'
            )
        try:
            artifact_payload = json.loads(artifact_path.read_text(encoding='utf-8'))
        except Exception as exc:
            raise RuntimeError(
                f'canonical manifest field {field_name} cannot read artifact file {artifact_path}: {exc}'
            ) from exc
        if artifact_payload != payload:
            raise RuntimeError(
                f'canonical manifest field {field_name} diverges from registered artifact {artifact_name}'
            )

    @staticmethod
    def _canonical_payload_hash(payload: Dict[str, Any], *, preferred_keys: tuple[str, ...]) -> str:
        """Compute the canonical hash for manifest-embedded payloads.

        Args:
            payload: Canonical JSON payload.
            preferred_keys: Optional payload keys whose non-empty value should be
                used directly before falling back to normalized JSON hashing.

        Returns:
            Stable hash string or an empty string for empty payloads.
        """
        for key in preferred_keys:
            value = str(payload.get(key, '') or '').strip()
            if value:
                return value
        if not payload:
            return ''
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')
        return hashlib.sha256(blob).hexdigest()

    def _validate_artifact_registration(self, *, session_dir: Path, name: str, payload: Dict[str, Any]) -> None:
        """Validate registration payloads that target canonical JSON artifacts.

        Args:
            session_dir: Locked session directory owning the artifact.
            name: Canonical artifact type.
            payload: Artifact descriptor payload destined for the manifest.

        Raises:
            KeyError: Raised when the descriptor omits ``path``.
            RuntimeError: Raised when the referenced artifact file is missing or
                violates the enforced canonical schema contract.
        """
        if name not in ENFORCED_CANONICAL_JSON_ARTIFACTS:
            return
        relative_path = str(payload.get("path", "") or "").strip()
        if not relative_path:
            raise KeyError(f"artifact descriptor for {name} is missing path")
        artifact_path = Path(relative_path)
        if not artifact_path.is_absolute():
            artifact_path = session_dir / artifact_path
        if not artifact_path.exists() or not artifact_path.is_file():
            raise RuntimeError(f"artifact registration failed for {name}: missing artifact file {artifact_path}")
        self._validate_artifact_file(name=name, artifact_path=artifact_path)

    def _validate_artifact_file(self, *, name: str, artifact_path: Path) -> None:
        """Validate a JSON artifact against its registered canonical schema.

        Args:
            name: Canonical artifact type.
            artifact_path: On-disk JSON artifact path.

        Raises:
            RuntimeError: Raised when the artifact payload is not valid for the
                registered schema.
        """
        if name not in ENFORCED_CANONICAL_JSON_ARTIFACTS:
            return
        schema_name = schema_for_artifact(name)
        if not schema_name:
            return
        try:
            payload = json.loads(artifact_path.read_text(encoding="utf-8"))
            validate_payload_against_schema(schema_name=schema_name, payload=payload)
        except Exception as exc:
            try:
                artifact_path.unlink(missing_ok=True)
            except OSError:
                pass
            raise RuntimeError(f'artifact schema validation failed for {name}: {exc}') from exc

    def _build_artifact_descriptor(self, session_dir: Path, name: str, artifact_path: Path) -> ArtifactDescriptor:
        mime_type = mimetypes.guess_type(str(artifact_path))[0] or "application/octet-stream"
        rel_path = str(artifact_path.relative_to(session_dir))
        return ArtifactDescriptor(
            artifact_type=name,
            path=rel_path,
            mime_type=mime_type,
            producer="experiment_manager",
            schema=schema_for_artifact(name),
            artifact_id=name,
            size_bytes=artifact_path.stat().st_size if artifact_path.exists() else 0,
            checksum=self._checksum_for_path(artifact_path),
            created_at=now_text(),
            summary=name.replace("_", " "),
            source_stage=infer_source_stage(name),
            dependencies=infer_dependencies(name),
        )

    def _write_manifest(self, session_dir: Path, manifest: SessionManifest) -> None:
        path = session_dir / "meta" / "manifest.json"
        path.write_text(json.dumps(asdict(manifest), indent=2, ensure_ascii=False), encoding="utf-8")

    @staticmethod
    def _checksum_for_path(path: Path) -> str:
        if not path.exists() or not path.is_file():
            return ""
        digest = hashlib.sha256()
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(65536), b""):
                digest.update(chunk)
        return digest.hexdigest()

