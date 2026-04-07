from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.utils import ensure_dir, now_text


class SessionExportService:
    """Export locked session artifacts into training-ready dataset cases.

    The service copies authoritative session artifacts into a deterministic
    patient/session dataset tree so offline annotation and model training stay
    decoupled from the runtime application.
    """

    def export_lamina_center_case(self, session_dir: Path, output_root: Path) -> dict[str, Any]:
        """Export a locked session as a lamina-center training case.

        Args:
            session_dir: Locked session directory containing authoritative
                reconstruction artifacts.
            output_root: Dataset root where the case directory will be created.

        Returns:
            Metadata describing the exported case, generated files, and labels.

        Raises:
            FileNotFoundError: Raised when the session directory does not exist.
            ValueError: Raised when the session manifest is missing required
                session identifiers.

        Boundary behaviour:
            Missing optional artifacts are represented by empty files or empty
            JSON payloads so annotation tooling receives a stable directory
            contract across historical and modern sessions.
        """
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        patient_registration = self._read_json(session_dir / 'meta' / 'patient_registration.json')
        case_dir = self._resolve_case_dir(session_dir, output_root, manifest, patient_registration)
        ensure_dir(case_dir)
        exported = {
            'meta': self._copy_json(session_dir / 'meta' / 'manifest.json', case_dir / 'meta.json', fallback={
                'session_id': manifest.get('session_id', session_dir.name),
                'experiment_id': manifest.get('experiment_id', ''),
                'generated_at': now_text(),
                'patient_id': self._patient_id(patient_registration, manifest),
                'dataset_role': 'lamina_center',
            }),
            'patient_registration': self._copy_json(session_dir / 'meta' / 'patient_registration.json', case_dir / 'patient_registration.json'),
            'reconstruction_input_index': self._copy_json(session_dir / 'derived' / 'reconstruction' / 'reconstruction_input_index.json', case_dir / 'reconstruction_input_index.json'),
            'training_bridge_model_ready_input_index': self._copy_json(session_dir / 'derived' / 'training_bridge' / 'model_ready_input_index.json', case_dir / 'training_bridge_model_ready_input_index.json'),
            'spine_curve': self._copy_json(session_dir / 'derived' / 'reconstruction' / 'spine_curve.json', case_dir / 'spine_curve.json'),
            'prior_assisted_curve': self._copy_json(session_dir / 'derived' / 'reconstruction' / 'prior_assisted_curve.json', case_dir / 'prior_assisted_curve.json'),
            'landmark_track': self._copy_json(session_dir / 'derived' / 'reconstruction' / 'landmark_track.json', case_dir / 'landmark_track.json'),
            'reconstruction_summary': self._copy_json(session_dir / 'derived' / 'reconstruction' / 'reconstruction_summary.json', case_dir / 'reconstruction_summary.json'),
            'lamina_candidates': self._copy_json(session_dir / 'derived' / 'reconstruction' / 'lamina_candidates.json', case_dir / 'lamina_candidates.json'),
            'pose_series': self._copy_json(session_dir / 'derived' / 'reconstruction' / 'pose_series.json', case_dir / 'pose_series.json'),
            'coronal_vpi': self._copy_binary(session_dir / 'derived' / 'reconstruction' / 'coronal_vpi.npz', case_dir / 'coronal_vpi.npz'),
            'vpi_preview': self._copy_binary(session_dir / 'derived' / 'reconstruction' / 'vpi_preview.png', case_dir / 'vpi_preview.png'),
        }
        self._export_frames(session_dir / 'raw' / 'ultrasound' / 'frames', case_dir / 'us_frames')
        payload = {
            'generated_at': now_text(),
            'dataset_role': 'lamina_center',
            'patient_id': self._patient_id(patient_registration, manifest),
            'session_id': manifest.get('session_id', session_dir.name),
            'experiment_id': manifest.get('experiment_id', ''),
            'case_dir': str(case_dir),
            'exported_files': {name: str(path) for name, path in exported.items()},
        }
        (case_dir / 'export_manifest.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        return payload

    def export_uca_case(self, session_dir: Path, output_root: Path) -> dict[str, Any]:
        """Export a locked session as a UCA-annotation/training case.

        Args:
            session_dir: Locked session directory containing VPI and assessment
                artifacts.
            output_root: Dataset root where the case directory will be created.

        Returns:
            Metadata describing the exported UCA case.

        Raises:
            FileNotFoundError: Raised when the session directory does not exist.
            ValueError: Raised when the session manifest lacks identifiers.

        Boundary behaviour:
            The service emits empty JSON placeholders for optional UCA artifacts
            so downstream ranking and annotation tools can process sessions that
            have not yet run auxiliary-UCA assessment. Coronal slices are
            materialized from the exported VPI bundle to keep the offline
            annotation workflow independent from runtime-only projection code.
        """
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        patient_registration = self._read_json(session_dir / 'meta' / 'patient_registration.json')
        case_dir = self._resolve_case_dir(session_dir, output_root, manifest, patient_registration)
        ensure_dir(case_dir)
        exported = {
            'meta': self._copy_json(session_dir / 'meta' / 'manifest.json', case_dir / 'meta.json', fallback={
                'session_id': manifest.get('session_id', session_dir.name),
                'experiment_id': manifest.get('experiment_id', ''),
                'generated_at': now_text(),
                'patient_id': self._patient_id(patient_registration, manifest),
                'dataset_role': 'uca',
            }),
            'patient_registration': self._copy_json(session_dir / 'meta' / 'patient_registration.json', case_dir / 'patient_registration.json'),
            'coronal_vpi': self._copy_binary(session_dir / 'derived' / 'reconstruction' / 'coronal_vpi.npz', case_dir / 'coronal_vpi.npz'),
            'vpi_preview': self._copy_binary(session_dir / 'derived' / 'reconstruction' / 'vpi_preview.png', case_dir / 'vpi_preview.png'),
            'vpi_ranked_slices': self._copy_json(session_dir / 'derived' / 'reconstruction' / 'vpi_ranked_slices.json', case_dir / 'ranked_slice_candidates.json'),
            'vpi_bone_feature_mask': self._copy_binary(session_dir / 'derived' / 'reconstruction' / 'vpi_bone_feature_mask.npz', case_dir / 'vpi_bone_feature_mask.npz'),
            'uca_measurement': self._copy_json(session_dir / 'derived' / 'assessment' / 'uca_measurement.json', case_dir / 'uca_measurement.json'),
            'prior_assisted_cobb': self._copy_json(session_dir / 'derived' / 'assessment' / 'prior_assisted_cobb.json', case_dir / 'prior_assisted_cobb.json'),
        }
        self._export_coronal_slices(case_dir / 'coronal_vpi.npz', case_dir / 'coronal_slices')
        payload = {
            'generated_at': now_text(),
            'dataset_role': 'uca',
            'patient_id': self._patient_id(patient_registration, manifest),
            'session_id': manifest.get('session_id', session_dir.name),
            'experiment_id': manifest.get('experiment_id', ''),
            'case_dir': str(case_dir),
            'exported_files': {name: str(path) for name, path in exported.items()},
            'coronal_slice_dir': str(case_dir / 'coronal_slices'),
        }
        (case_dir / 'export_manifest.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        return payload

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

    @staticmethod
    def _copy_json(source: Path, destination: Path, fallback: dict[str, Any] | None = None) -> Path:
        ensure_dir(destination.parent)
        if source.exists():
            try:
                payload = json.loads(source.read_text(encoding='utf-8'))
            except (OSError, json.JSONDecodeError):
                payload = dict(fallback or {})
        else:
            payload = dict(fallback or {})
        destination.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        return destination

    @staticmethod
    def _copy_binary(source: Path, destination: Path) -> Path:
        ensure_dir(destination.parent)
        if source.exists():
            try:
                shutil.copy2(source, destination)
                return destination
            except OSError:
                pass
        if destination.suffix == '.npz':
            np.savez_compressed(destination, empty=np.zeros((0,), dtype=np.float32))
        else:
            destination.write_bytes(b'')
        return destination

    @staticmethod
    def _export_coronal_slices(vpi_path: Path, destination_dir: Path) -> None:
        """Materialize coronal VPI columns as standalone slice files.

        Args:
            vpi_path: Path to the exported VPI ``.npz`` file.
            destination_dir: Directory receiving per-slice ``.npy`` files.

        Returns:
            None.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Missing or empty VPI payloads simply create an empty destination
            directory so downstream UCA annotation tools can still open the
            case structure without special casing missing slices.
        """
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
