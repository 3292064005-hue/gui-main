from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.utils import ensure_dir, now_text


class SessionExportService:
    """Export locked sessions into provenance-aware dataset cases.

    Optional artifacts are still materialized into deterministic case
    directories, but every placeholder is explicitly declared in the export
    manifest so downstream consumers cannot misread file presence as clinical or
    research truth.
    """

    def export_lamina_center_case(self, session_dir: Path, output_root: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        patient_registration = self._read_json(session_dir / 'meta' / 'patient_registration.json')
        case_dir = self._resolve_case_dir(session_dir, output_root, manifest, patient_registration)
        ensure_dir(case_dir)
        artifact_states = {
            'meta': self._materialize_json(
                source=session_dir / 'meta' / 'manifest.json',
                destination=case_dir / 'meta.json',
                required=True,
                fallback={
                    'session_id': manifest.get('session_id', session_dir.name),
                    'experiment_id': manifest.get('experiment_id', ''),
                    'generated_at': now_text(),
                    'patient_id': self._patient_id(patient_registration, manifest),
                    'dataset_role': 'lamina_center',
                },
                producer_step='session_lock',
                consumers=['annotation_manifest', 'dataset_export'],
            ),
            'patient_registration': self._materialize_json(
                source=session_dir / 'meta' / 'patient_registration.json',
                destination=case_dir / 'patient_registration.json',
                required=True,
                producer_step='session_lock',
                consumers=['annotation_manifest', 'dataset_export'],
            ),
            'reconstruction_input_index': self._materialize_json(
                source=session_dir / 'derived' / 'reconstruction' / 'reconstruction_input_index.json',
                destination=case_dir / 'reconstruction_input_index.json',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['training'],
            ),
            'training_bridge_model_ready_input_index': self._materialize_json(
                source=session_dir / 'derived' / 'training_bridge' / 'model_ready_input_index.json',
                destination=case_dir / 'training_bridge_model_ready_input_index.json',
                required=False,
                producer_step='training_bridge',
                consumers=['training'],
            ),
            'spine_curve': self._materialize_json(
                source=session_dir / 'derived' / 'reconstruction' / 'spine_curve.json',
                destination=case_dir / 'spine_curve.json',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['assessment', 'dataset_export'],
            ),
            'prior_assisted_curve': self._materialize_json(
                source=session_dir / 'derived' / 'reconstruction' / 'prior_assisted_curve.json',
                destination=case_dir / 'prior_assisted_curve.json',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['dataset_export'],
            ),
            'landmark_track': self._materialize_json(
                source=session_dir / 'derived' / 'reconstruction' / 'landmark_track.json',
                destination=case_dir / 'landmark_track.json',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['dataset_export'],
            ),
            'reconstruction_summary': self._materialize_json(
                source=session_dir / 'derived' / 'reconstruction' / 'reconstruction_summary.json',
                destination=case_dir / 'reconstruction_summary.json',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['dataset_export', 'qa_pack'],
            ),
            'lamina_candidates': self._materialize_json(
                source=session_dir / 'derived' / 'reconstruction' / 'lamina_candidates.json',
                destination=case_dir / 'lamina_candidates.json',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['dataset_export'],
            ),
            'pose_series': self._materialize_json(
                source=session_dir / 'derived' / 'reconstruction' / 'pose_series.json',
                destination=case_dir / 'pose_series.json',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['dataset_export'],
            ),
            'coronal_vpi': self._materialize_binary(
                source=session_dir / 'derived' / 'reconstruction' / 'coronal_vpi.npz',
                destination=case_dir / 'coronal_vpi.npz',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['annotation_tools', 'dataset_export'],
            ),
            'vpi_preview': self._materialize_binary(
                source=session_dir / 'derived' / 'reconstruction' / 'vpi_preview.png',
                destination=case_dir / 'vpi_preview.png',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['annotation_tools', 'dataset_export'],
            ),
        }
        self._export_frames(session_dir / 'raw' / 'ultrasound' / 'frames', case_dir / 'us_frames')
        payload = self._build_export_payload(
            dataset_role='lamina_center',
            patient_registration=patient_registration,
            manifest=manifest,
            case_dir=case_dir,
            artifact_states=artifact_states,
        )
        self._write_export_manifest(case_dir / 'export_manifest.json', payload)
        return payload

    def export_uca_case(self, session_dir: Path, output_root: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        patient_registration = self._read_json(session_dir / 'meta' / 'patient_registration.json')
        case_dir = self._resolve_case_dir(session_dir, output_root, manifest, patient_registration)
        ensure_dir(case_dir)
        artifact_states = {
            'meta': self._materialize_json(
                source=session_dir / 'meta' / 'manifest.json',
                destination=case_dir / 'meta.json',
                required=True,
                fallback={
                    'session_id': manifest.get('session_id', session_dir.name),
                    'experiment_id': manifest.get('experiment_id', ''),
                    'generated_at': now_text(),
                    'patient_id': self._patient_id(patient_registration, manifest),
                    'dataset_role': 'uca',
                },
                producer_step='session_lock',
                consumers=['annotation_manifest', 'dataset_export'],
            ),
            'patient_registration': self._materialize_json(
                source=session_dir / 'meta' / 'patient_registration.json',
                destination=case_dir / 'patient_registration.json',
                required=True,
                producer_step='session_lock',
                consumers=['annotation_manifest', 'dataset_export'],
            ),
            'coronal_vpi': self._materialize_binary(
                source=session_dir / 'derived' / 'reconstruction' / 'coronal_vpi.npz',
                destination=case_dir / 'coronal_vpi.npz',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['annotation_tools', 'dataset_export'],
            ),
            'vpi_preview': self._materialize_binary(
                source=session_dir / 'derived' / 'reconstruction' / 'vpi_preview.png',
                destination=case_dir / 'vpi_preview.png',
                required=False,
                producer_step='reconstruction_stage',
                consumers=['annotation_tools', 'dataset_export'],
            ),
            'vpi_ranked_slices': self._materialize_json(
                source=session_dir / 'derived' / 'reconstruction' / 'vpi_ranked_slices.json',
                destination=case_dir / 'ranked_slice_candidates.json',
                required=False,
                producer_step='assessment_stage',
                consumers=['annotation_tools', 'dataset_export'],
            ),
            'vpi_bone_feature_mask': self._materialize_binary(
                source=session_dir / 'derived' / 'reconstruction' / 'vpi_bone_feature_mask.npz',
                destination=case_dir / 'vpi_bone_feature_mask.npz',
                required=False,
                producer_step='assessment_stage',
                consumers=['annotation_tools', 'dataset_export'],
            ),
            'uca_measurement': self._materialize_json(
                source=session_dir / 'derived' / 'assessment' / 'uca_measurement.json',
                destination=case_dir / 'uca_measurement.json',
                required=False,
                producer_step='assessment_stage',
                consumers=['dataset_export', 'benchmark'],
            ),
            'prior_assisted_cobb': self._materialize_json(
                source=session_dir / 'derived' / 'assessment' / 'prior_assisted_cobb.json',
                destination=case_dir / 'prior_assisted_cobb.json',
                required=False,
                producer_step='assessment_stage',
                consumers=['dataset_export', 'benchmark'],
            ),
        }
        self._export_coronal_slices(case_dir / 'coronal_vpi.npz', case_dir / 'coronal_slices')
        payload = self._build_export_payload(
            dataset_role='uca',
            patient_registration=patient_registration,
            manifest=manifest,
            case_dir=case_dir,
            artifact_states=artifact_states,
        )
        payload['coronal_slice_dir'] = str(case_dir / 'coronal_slices')
        self._write_export_manifest(case_dir / 'export_manifest.json', payload)
        return payload

    def _build_export_payload(
        self,
        *,
        dataset_role: str,
        patient_registration: dict[str, Any],
        manifest: dict[str, Any],
        case_dir: Path,
        artifact_states: dict[str, dict[str, Any]],
    ) -> dict[str, Any]:
        placeholder_artifacts = [name for name, item in artifact_states.items() if bool(item.get('placeholder_generated'))]
        integrity_state = 'placeholder_present' if placeholder_artifacts else 'fully_materialized'
        return {
            'generated_at': now_text(),
            'dataset_role': dataset_role,
            'patient_id': self._patient_id(patient_registration, manifest),
            'session_id': manifest.get('session_id', case_dir.name),
            'experiment_id': manifest.get('experiment_id', ''),
            'case_dir': str(case_dir),
            'materialized_artifacts': sorted([name for name, item in artifact_states.items() if str(item.get('state')) == 'present']),
            'placeholder_artifacts': placeholder_artifacts,
            'placeholder_artifact_count': len(placeholder_artifacts),
            'integrity_state': integrity_state,
            'claim_boundary': 'placeholder files are structural placeholders, not authoritative evidence of upstream computation',
            'artifact_states': artifact_states,
        }

    @staticmethod
    def _write_export_manifest(path: Path, payload: dict[str, Any]) -> None:
        path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')

    def _resolve_case_dir(self, session_dir: Path, output_root: Path, manifest: dict[str, Any], patient_registration: dict[str, Any]) -> Path:
        if not session_dir.exists():
            raise FileNotFoundError(session_dir)
        session_id = str(manifest.get('session_id', '') or session_dir.name)
        if not session_id:
            raise ValueError('session_id is required for dataset export')
        patient_id = self._patient_id(patient_registration, manifest)
        return ensure_dir(output_root / 'raw_cases') / patient_id / session_id

    @staticmethod
    def _patient_id(patient_registration: dict[str, Any], manifest: dict[str, Any]) -> str:
        return str(
            patient_registration.get('patient_id')
            or patient_registration.get('subject_id')
            or manifest.get('patient_id')
            or manifest.get('experiment_id')
            or 'unknown_patient'
        )

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return {}

    def _materialize_json(
        self,
        *,
        source: Path,
        destination: Path,
        required: bool,
        producer_step: str,
        consumers: list[str],
        fallback: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        ensure_dir(destination.parent)
        placeholder_generated = False
        reason = ''
        if source.exists():
            try:
                payload = json.loads(source.read_text(encoding='utf-8'))
                state = 'present'
            except (OSError, json.JSONDecodeError):
                payload = dict(fallback or {})
                state = 'generated_placeholder'
                placeholder_generated = True
                reason = 'source_json_invalid'
        else:
            payload = dict(fallback or {})
            state = 'generated_placeholder'
            placeholder_generated = True
            reason = 'source_missing'
        destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        return {
            'state': state,
            'required': bool(required),
            'source_path': str(source),
            'exported_path': str(destination),
            'source_exists': source.exists(),
            'placeholder_generated': placeholder_generated,
            'reason': reason,
            'producer_step': producer_step,
            'consumers': list(consumers),
            'evidence_status': 'present' if state == 'present' else 'placeholder',
        }

    def _materialize_binary(
        self,
        *,
        source: Path,
        destination: Path,
        required: bool,
        producer_step: str,
        consumers: list[str],
    ) -> dict[str, Any]:
        ensure_dir(destination.parent)
        placeholder_generated = False
        reason = ''
        if source.exists():
            try:
                shutil.copy2(source, destination)
                state = 'present'
            except OSError:
                state = 'generated_placeholder'
                placeholder_generated = True
                reason = 'source_copy_failed'
        else:
            state = 'generated_placeholder'
            placeholder_generated = True
            reason = 'source_missing'
        if state != 'present':
            if destination.suffix == '.npz':
                np.savez_compressed(destination, empty=np.zeros((0,), dtype=np.float32))
            else:
                destination.write_bytes(b'')
        return {
            'state': state,
            'required': bool(required),
            'source_path': str(source),
            'exported_path': str(destination),
            'source_exists': source.exists(),
            'placeholder_generated': placeholder_generated,
            'reason': reason,
            'producer_step': producer_step,
            'consumers': list(consumers),
            'evidence_status': 'present' if state == 'present' else 'placeholder',
        }

    @staticmethod
    def _export_coronal_slices(vpi_path: Path, destination_dir: Path) -> None:
        ensure_dir(destination_dir)
        if not vpi_path.exists():
            return
        try:
            with np.load(vpi_path, allow_pickle=False) as payload:
                if not payload.files:
                    return
                image = np.asarray(payload[payload.files[0]], dtype=np.float32)
        except Exception:
            return
        if image.ndim != 2 or image.size == 0:
            return
        for index in range(image.shape[1]):
            np.save(destination_dir / f'slice_{index:04d}.npy', image[:, index].astype(np.float32))

    @staticmethod
    def _export_frames(source_dir: Path, destination_dir: Path) -> None:
        ensure_dir(destination_dir)
        if not source_dir.exists():
            return
        try:
            frames = sorted(source_dir.iterdir())
        except OSError:
            return
        for frame in frames:
            if frame.is_file():
                try:
                    shutil.copy2(frame, destination_dir / frame.name)
                except OSError:
                    continue
