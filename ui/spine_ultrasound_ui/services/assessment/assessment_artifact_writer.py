from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.utils import ensure_dir


class AssessmentArtifactWriter:
    """Persist authoritative assessment artifacts for a session."""

    def __init__(self, exp_manager: ExperimentManager) -> None:
        self.exp_manager = exp_manager

    def write(
        self,
        session_dir: Path,
        *,
        cobb_measurement: dict[str, Any],
        assessment_summary: dict[str, Any],
        vertebra_pairs: dict[str, Any] | None = None,
        tilt_candidates: dict[str, Any] | None = None,
        uca_measurement: dict[str, Any] | None = None,
        assessment_agreement: dict[str, Any] | None = None,
        overlay_path: Path | None = None,
        prior_assisted_cobb: dict[str, Any] | None = None,
    ) -> dict[str, Path]:
        """Write assessment artifacts to deterministic session locations.

        Args:
            session_dir: Locked session directory.
            cobb_measurement: Detailed Cobb measurement payload.
            assessment_summary: Session-oriented assessment summary payload.
            vertebra_pairs: Optional vertebra pairing payload.
            tilt_candidates: Optional vertebra tilt payload.
            uca_measurement: Optional auxiliary-UCA payload.
            assessment_agreement: Optional agreement payload.
            overlay_path: Optional rendered overlay path.
            prior_assisted_cobb: Optional sidecar measurement derived from prior-assisted geometry.

        Returns:
            Mapping of canonical assessment artifact names to written paths.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` does not exist.

        Boundary behaviour:
            Optional artifacts are omitted when unavailable so older consumers can
            continue reading the core authoritative assessment files. When a
            prior-assisted measurement exists, the canonical
            ``cobb_measurement.json`` is rewritten as an authoritative
            placeholder and the contaminated measurement is emitted only via the
            dedicated sidecar.
        """
        if not session_dir.exists():
            raise FileNotFoundError(session_dir)
        canonical_measurement = self._canonical_measurement_payload(
            measurement=cobb_measurement,
            summary=assessment_summary,
            prior_assisted_cobb=prior_assisted_cobb,
        )
        output = {
            'cobb_measurement': self.exp_manager.save_json_artifact(session_dir, 'derived/assessment/cobb_measurement.json', canonical_measurement),
            'assessment_summary': self.exp_manager.save_json_artifact(session_dir, 'derived/assessment/assessment_summary.json', assessment_summary),
        }
        if vertebra_pairs is not None:
            output['vertebra_pairs'] = self.exp_manager.save_json_artifact(session_dir, 'derived/assessment/vertebra_pairs.json', vertebra_pairs)
        if tilt_candidates is not None:
            output['tilt_candidates'] = self.exp_manager.save_json_artifact(session_dir, 'derived/assessment/tilt_candidates.json', tilt_candidates)
        if uca_measurement is not None:
            output['uca_measurement'] = self.exp_manager.save_json_artifact(session_dir, 'derived/assessment/uca_measurement.json', uca_measurement)
        if assessment_agreement is not None:
            output['assessment_agreement'] = self.exp_manager.save_json_artifact(session_dir, 'derived/assessment/assessment_agreement.json', assessment_agreement)
        if prior_assisted_cobb is not None:
            output['prior_assisted_cobb'] = self.exp_manager.save_json_artifact(session_dir, 'derived/assessment/prior_assisted_cobb.json', prior_assisted_cobb)
        if overlay_path is not None and overlay_path.exists():
            target = session_dir / 'derived' / 'assessment' / 'assessment_overlay.png'
            ensure_dir(target.parent)
            target.write_bytes(overlay_path.read_bytes())
            output['assessment_overlay'] = target
        return output

    @staticmethod
    def _canonical_measurement_payload(
        *,
        measurement: dict[str, Any],
        summary: dict[str, Any],
        prior_assisted_cobb: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Return the canonical Cobb payload for disk persistence."""
        contamination_flags = {str(item) for item in list(summary.get('source_contamination_flags', [])) if str(item)}
        is_prior_assisted = bool(prior_assisted_cobb) or str(summary.get('closure_verdict', '')) == 'prior_assisted' or bool(contamination_flags)
        if not is_prior_assisted:
            return dict(measurement)
        return {
            'generated_at': str(measurement.get('generated_at', summary.get('generated_at', '')) or ''),
            'session_id': str(summary.get('session_id', measurement.get('session_id', '')) or ''),
            'experiment_id': str(summary.get('experiment_id', measurement.get('experiment_id', '')) or ''),
            'method_version': str(measurement.get('method_version', summary.get('method_version', '')) or ''),
            'coordinate_frame': str(summary.get('coordinate_frame', measurement.get('coordinate_frame', 'patient_surface')) or 'patient_surface'),
            'angle_deg': 0.0,
            'confidence': 0.0,
            'requires_manual_review': True,
            'upper_end_vertebra_candidate': {},
            'lower_end_vertebra_candidate': {},
            'upper_line': {},
            'lower_line': {},
            'evidence_refs': [],
            'fit_diagnostics': {'authoritative_available': False},
            'runtime_profile': str(summary.get('runtime_profile', measurement.get('runtime_profile', 'weighted_runtime')) or 'weighted_runtime'),
            'profile_release_state': str(summary.get('profile_release_state', measurement.get('profile_release_state', 'research_validated')) or 'research_validated'),
            'closure_mode': str(summary.get('closure_mode', measurement.get('closure_mode', 'runtime_optional')) or 'runtime_optional'),
            'measurement_source': 'authoritative_measurement_unavailable',
            'measurement_status': 'unavailable',
            'manual_review_reasons': ['authoritative_measurement_unavailable'],
            'closure_verdict': 'prior_assisted',
            'provenance_purity': 'prior_assisted',
            'source_contamination_flags': list(summary.get('source_contamination_flags', [])),
            'hard_blockers': list(summary.get('hard_blockers', [])),
            'soft_review_reasons': list(summary.get('soft_review_reasons', [])),
            'authoritative_available': False,
            'sidecar_ref': 'derived/assessment/prior_assisted_cobb.json',
        }
