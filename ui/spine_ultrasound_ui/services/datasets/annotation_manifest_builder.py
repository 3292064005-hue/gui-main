from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import ensure_dir, now_text


class AnnotationManifestBuilder:
    """Build deterministic annotation manifests and patient-level data splits."""

    def build(self, dataset_root: Path) -> dict[str, Any]:
        """Scan exported dataset cases and build an annotation manifest.

        Args:
            dataset_root: Dataset root containing patient/session subfolders.

        Returns:
            Manifest payload with cases and patient-level train/val/test splits.

        Raises:
            FileNotFoundError: Raised when the dataset root does not exist.

        Boundary behaviour:
            Invalid or incomplete case directories are skipped instead of causing
            the manifest build to fail. This keeps the export workflow usable
            during iterative curation.
        """
        if not dataset_root.exists():
            raise FileNotFoundError(dataset_root)
        cases: list[dict[str, Any]] = []
        raw_root = dataset_root / 'raw_cases'
        if raw_root.exists():
            for patient_dir in sorted(path for path in raw_root.iterdir() if path.is_dir()):
                for session_dir in sorted(path for path in patient_dir.iterdir() if path.is_dir()):
                    meta_path = session_dir / 'meta.json'
                    if not meta_path.exists():
                        continue
                    meta = json.loads(meta_path.read_text(encoding='utf-8'))
                    patient_id = str(meta.get('patient_id', patient_dir.name) or patient_dir.name)
                    session_id = str(meta.get('session_id', session_dir.name) or session_dir.name)
                    case_id = f"{patient_id}/{session_id}"
                    cases.append({
                        'case_id': case_id,
                        'patient_id': patient_id,
                        'session_id': session_id,
                        'case_dir': str(session_dir),
                        'dataset_role': str(meta.get('dataset_role', 'unknown') or 'unknown'),
                    })
        split = self.build_patient_level_split(cases)
        payload = {
            'generated_at': now_text(),
            'dataset_root': str(dataset_root),
            'case_count': len(cases),
            'cases': cases,
            'split': split,
        }
        ensure_dir(dataset_root / 'splits')
        (dataset_root / 'annotation_manifest.json').write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        (dataset_root / 'splits' / 'split_v1.json').write_text(json.dumps(split, indent=2, ensure_ascii=False), encoding='utf-8')
        return payload

    def build_patient_level_split(self, cases: list[dict[str, Any]], *, seed: int = 42) -> dict[str, list[str]]:
        """Build a deterministic patient-level split.

        Args:
            cases: Case metadata rows containing ``patient_id`` and ``case_id``.
            seed: Stable split seed incorporated into the patient hash.

        Returns:
            Mapping with ``train``, ``val``, and ``test`` case identifiers.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Empty case lists return empty splits. Patients are hashed as whole
            groups so no patient can appear in multiple splits.
        """
        grouped: dict[str, list[str]] = {}
        for case in cases:
            patient_id = str(case.get('patient_id', 'unknown_patient') or 'unknown_patient')
            grouped.setdefault(patient_id, []).append(str(case.get('case_id', '')))
        split = {'train': [], 'val': [], 'test': []}
        for patient_id in sorted(grouped):
            bucket = self._bucket_for_patient(patient_id, seed)
            split[bucket].extend(sorted(grouped[patient_id]))
        return split

    @staticmethod
    def _bucket_for_patient(patient_id: str, seed: int) -> str:
        digest = hashlib.sha256(f'{patient_id}:{seed}'.encode('utf-8')).hexdigest()
        value = int(digest[:8], 16) % 10
        if value < 7:
            return 'train'
        if value < 9:
            return 'val'
        return 'test'
