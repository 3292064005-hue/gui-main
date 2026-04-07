from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.authoritative_artifact_reader import AuthoritativeArtifactReader
from spine_ultrasound_ui.utils import now_text


class AssessmentInputBuilder:
    """Assemble authoritative assessment inputs from reconstruction artifacts."""

    def __init__(self, *, method_version: str = 'assessment_input_index_v2', artifact_reader: AuthoritativeArtifactReader | None = None) -> None:
        self.method_version = method_version
        self.artifact_reader = artifact_reader or AuthoritativeArtifactReader()

    def build(self, session_dir: Path) -> dict[str, Any]:
        """Build a normalized assessment input payload.

        Args:
            session_dir: Locked session directory containing reconstruction and
                patient-registration evidence.

        Returns:
            Assessment input payload containing spine-curve geometry,
            lamina-center evidence, VPI references, and patient-frame context.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` does not exist.

        Boundary behaviour:
            Missing optional artifacts degrade to empty dictionaries so the
            measurement stage can flag manual review instead of aborting.
            When the reconstruction summary marks the canonical spine curve as
            prior-assisted, the builder transparently switches to the
            ``prior_assisted_curve.json`` sidecar so weighted-runtime curve
            fallback can continue without letting contaminated geometry occupy
            the canonical artifact path.
        """
        if not session_dir.exists():
            raise FileNotFoundError(session_dir)
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        curve_resolution = self.artifact_reader.read_spine_curve(session_dir)
        reconstruction_summary = dict(curve_resolution.get('summary', {}))
        return {
            'generated_at': now_text(),
            'session_id': manifest.get('session_id', session_dir.name),
            'experiment_id': manifest.get('experiment_id', ''),
            'method_version': self.method_version,
            'patient_registration': self._read_json(session_dir / 'meta' / 'patient_registration.json'),
            'spine_curve': dict(curve_resolution.get('effective_payload', {})),
            'spine_curve_source_path': str(curve_resolution.get('effective_source_path', 'derived/reconstruction/spine_curve.json')),
            'landmark_track': self._read_json(session_dir / 'derived' / 'reconstruction' / 'landmark_track.json'),
            'lamina_candidates': self._read_json(session_dir / 'derived' / 'reconstruction' / 'lamina_candidates.json'),
            'reconstruction_summary': reconstruction_summary,
            'reconstruction_evidence': self._read_json(session_dir / 'derived' / 'reconstruction' / 'reconstruction_evidence.json'),
            'vpi_path': str(session_dir / 'derived' / 'reconstruction' / 'coronal_vpi.npz'),
            'vpi_preview_path': str(session_dir / 'derived' / 'reconstruction' / 'vpi_preview.png'),
            'bone_mask_path': str(session_dir / 'derived' / 'reconstruction' / 'bone_mask.npz'),
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        """Read an optional JSON artifact without aborting the assessment path.

        Args:
            path: Artifact path to read.

        Returns:
            Parsed JSON object, or an empty dictionary when the artifact is
            missing or malformed.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Historical sessions and partially written reconstruction sidecars can
            omit or corrupt optional JSON artifacts. The assessment input stage
            degrades to an empty payload so measurement logic can surface manual
            review instead of crashing the post-process job.
        """
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return {}
