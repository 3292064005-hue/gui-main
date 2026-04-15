from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.session_products_authority_surface import SessionProductsAuthoritySurface
from spine_ultrasound_ui.utils import now_text


class AssessmentBenchmarkService:
    """Evaluate authoritative assessment outputs against offline references.

    The benchmark contract is intentionally simple: each session may provide a
    JSON file containing either ``angle_deg`` or ``cobb_angle_deg``. The
    service aggregates absolute-error and manual-review statistics across the
    supplied cases so release gating can fail fast when measurement quality
    regresses.
    """

    def __init__(self, artifact_reader: SessionProductsAuthoritySurface | None = None) -> None:
        self._artifact_reader = artifact_reader or SessionProductsAuthoritySurface()

    def evaluate_many(self, case_specs: list[dict[str, Any]]) -> dict[str, Any]:
        """Evaluate multiple benchmark cases.

        Args:
            case_specs: Sequence of dictionaries with ``session_dir`` and
                optional ``ground_truth_path`` fields.

        Returns:
            Aggregate benchmark payload with per-case details.

        Raises:
            FileNotFoundError: Raised when a declared session or ground-truth
                file does not exist.
        """
        cases = [self.evaluate_case(**spec) for spec in case_specs]
        measured_cases = [case for case in cases if case.get('ground_truth_available', False)]
        absolute_errors = [float(case.get('absolute_error_deg', 0.0) or 0.0) for case in measured_cases]
        manual_review_cases = sum(1 for case in cases if bool(case.get('requires_manual_review', False)))
        return {
            'generated_at': now_text(),
            'case_count': len(cases),
            'ground_truth_case_count': len(measured_cases),
            'mean_absolute_error_deg': round(sum(absolute_errors) / len(absolute_errors), 4) if absolute_errors else 0.0,
            'max_absolute_error_deg': round(max(absolute_errors), 4) if absolute_errors else 0.0,
            'manual_review_rate': round(manual_review_cases / max(1, len(cases)), 4),
            'cases': cases,
        }

    def evaluate_case(self, *, session_dir: str | Path, ground_truth_path: str | Path | None = None) -> dict[str, Any]:
        """Evaluate a single session against optional ground truth.

        Args:
            session_dir: Session directory containing authoritative assessment
                artifacts.
            ground_truth_path: Optional explicit ground-truth JSON path.

        Returns:
            Case-level benchmark payload.

        Raises:
            FileNotFoundError: Raised when the session directory or explicit
                ground-truth path does not exist.

        Boundary behaviour:
            Prior-assisted sessions resolve their measurement from the dedicated
            sidecar when available so benchmarking cannot silently consume the
            canonical placeholder artifact.
        """
        session_root = Path(session_dir)
        if not session_root.exists():
            raise FileNotFoundError(session_root)
        measurement_resolution = self._artifact_reader.read_cobb_measurement(session_root)
        assessment_summary = dict(measurement_resolution.get('summary', {}))
        measurement = dict(measurement_resolution.get('canonical', {}))
        measurement_payload = dict(measurement_resolution.get('effective_payload', {}))
        resolved_ground_truth = Path(ground_truth_path) if ground_truth_path else session_root / 'derived' / 'assessment' / 'ground_truth_cobb.json'
        if ground_truth_path and not resolved_ground_truth.exists():
            raise FileNotFoundError(resolved_ground_truth)
        ground_truth = self._read_json(resolved_ground_truth) if resolved_ground_truth.exists() else {}
        measured_angle = float(
            assessment_summary.get('cobb_angle_deg', measurement_payload.get('angle_deg', measurement.get('angle_deg', 0.0))) or 0.0
        )
        target_angle = float(ground_truth.get('cobb_angle_deg', ground_truth.get('angle_deg', 0.0)) or 0.0)
        ground_truth_available = bool(ground_truth)
        absolute_error = abs(measured_angle - target_angle) if ground_truth_available else 0.0
        return {
            'session_dir': str(session_root),
            'session_id': str(assessment_summary.get('session_id', session_root.name) or session_root.name),
            'measurement_source': str(assessment_summary.get('measurement_source', measurement_payload.get('measurement_source', '')) or ''),
            'requires_manual_review': bool(assessment_summary.get('requires_manual_review', measurement_payload.get('requires_manual_review', False))),
            'manual_review_reasons': list(assessment_summary.get('manual_review_reasons', measurement_payload.get('manual_review_reasons', []))),
            'closure_verdict': str(assessment_summary.get('closure_verdict', measurement_payload.get('closure_verdict', '')) or ''),
            'measured_angle_deg': round(measured_angle, 4),
            'ground_truth_available': ground_truth_available,
            'ground_truth_angle_deg': round(target_angle, 4) if ground_truth_available else None,
            'absolute_error_deg': round(absolute_error, 4),
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding='utf-8'))
