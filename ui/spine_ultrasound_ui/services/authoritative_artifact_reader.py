from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class AuthoritativeArtifactReader:
    """Resolve canonical-vs-sidecar authoritative artifacts for session consumers.

    The reader centralizes the prior-assisted placeholder policy so session,
    report, benchmark, and API consumers do not each re-implement their own
    interpretation of canonical reconstruction/assessment artifacts.
    """

    def read_spine_curve(self, session_dir: Path) -> dict[str, Any]:
        return self._resolve_json_artifact(
            session_dir=session_dir,
            canonical_relative_path='derived/reconstruction/spine_curve.json',
            summary_relative_path='derived/reconstruction/reconstruction_summary.json',
            sidecar_relative_path='derived/reconstruction/prior_assisted_curve.json',
        )

    def read_cobb_measurement(self, session_dir: Path) -> dict[str, Any]:
        return self._resolve_json_artifact(
            session_dir=session_dir,
            canonical_relative_path='derived/assessment/cobb_measurement.json',
            summary_relative_path='derived/assessment/assessment_summary.json',
            sidecar_relative_path='derived/assessment/prior_assisted_cobb.json',
        )

    def _resolve_json_artifact(
        self,
        *,
        session_dir: Path,
        canonical_relative_path: str,
        summary_relative_path: str,
        sidecar_relative_path: str,
    ) -> dict[str, Any]:
        """Resolve an effective authoritative payload from canonical and sidecar JSON.

        Args:
            session_dir: Session root.
            canonical_relative_path: Canonical artifact relative path.
            summary_relative_path: Summary artifact that declares closure verdict.
            sidecar_relative_path: Prior-assisted sidecar relative path.

        Returns:
            Resolution payload containing canonical, sidecar, summary, and the
            effective authoritative payload/source metadata.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` does not exist.

        Boundary behaviour:
            - Malformed JSON degrades to an empty dictionary.
            - Sidecars are only selected when the summary explicitly declares a
              ``prior_assisted`` closure verdict *and* the sidecar is valid.
            - When a prior-assisted sidecar is declared but malformed, callers
              keep the canonical source path instead of silently flipping to an
              unreadable sidecar path.
        """
        if not session_dir.exists():
            raise FileNotFoundError(session_dir)
        canonical_path = session_dir.joinpath(*canonical_relative_path.split('/'))
        summary_path = session_dir.joinpath(*summary_relative_path.split('/'))
        sidecar_path = session_dir.joinpath(*sidecar_relative_path.split('/'))
        summary_payload = self._read_json(summary_path)
        canonical_payload = self._read_json(canonical_path)
        sidecar_payload = self._read_json(sidecar_path)
        closure_verdict = str(summary_payload.get('closure_verdict', '') or '')
        source_contamination_flags = [str(item) for item in list(summary_payload.get('source_contamination_flags', [])) if str(item)]
        use_sidecar = closure_verdict == 'prior_assisted' and bool(sidecar_payload)
        effective_payload = dict(sidecar_payload if use_sidecar else canonical_payload)
        effective_source_path = sidecar_relative_path if use_sidecar else canonical_relative_path
        effective_status = 'authoritative'
        if closure_verdict == 'blocked':
            effective_status = 'blocked'
        elif closure_verdict == 'degraded_measured':
            effective_status = 'degraded'
        elif closure_verdict == 'prior_assisted' or source_contamination_flags:
            effective_status = 'prior_assisted'
        elif not effective_payload:
            effective_status = 'degraded'
        authority_metadata = self._build_authority_metadata(
            effective_status=effective_status,
            closure_verdict=closure_verdict,
            effective_source_path=effective_source_path,
            used_sidecar=use_sidecar,
            source_contamination_flags=source_contamination_flags,
        )
        return {
            'canonical': canonical_payload,
            'canonical_path': canonical_relative_path,
            'sidecar': sidecar_payload,
            'sidecar_path': sidecar_relative_path,
            'summary': summary_payload,
            'summary_path': summary_relative_path,
            'closure_verdict': closure_verdict,
            'source_contamination_flags': source_contamination_flags,
            'effective_payload': effective_payload,
            'effective_source_path': effective_source_path,
            'effective_status': effective_status,
            'used_sidecar': use_sidecar,
            'authority_metadata': authority_metadata,
        }

    @staticmethod
    def _build_authority_metadata(
        *,
        effective_status: str,
        closure_verdict: str,
        effective_source_path: str,
        used_sidecar: bool,
        source_contamination_flags: list[str],
    ) -> dict[str, Any]:
        """Build stable authority metadata for session products.

        Args:
            effective_status: Resolved effective artifact status.
            closure_verdict: Summary-declared closure verdict.
            effective_source_path: Relative source path selected for the payload.
            used_sidecar: Whether the selected payload came from a sidecar artifact.
            source_contamination_flags: Declared contamination flags.

        Returns:
            Additive-only authority metadata describing source class, fallback
            reason, and review suitability.
        """
        status = str(effective_status or 'degraded')
        source_class = {
            'authoritative': 'authoritative',
            'prior_assisted': 'prior_assisted',
            'degraded': 'degraded',
            'blocked': 'blocked',
        }.get(status, 'derived')
        authority_level = {
            'authoritative': 'runtime_authoritative',
            'prior_assisted': 'derived_prior_assisted',
            'degraded': 'derived_degraded',
            'blocked': 'derived_blocked',
        }.get(status, 'derived_unknown')
        fallback_reason = ''
        if status != 'authoritative':
            fallback_reason = closure_verdict or ('source_contamination' if source_contamination_flags else 'missing_authoritative_artifact')
        review_suitability = status in {'authoritative', 'prior_assisted', 'degraded'}
        return {
            'source_class': source_class,
            'authority_level': authority_level,
            'fallback_reason': fallback_reason,
            'effective_source_path': effective_source_path,
            'sidecar_selected': bool(used_sidecar),
            'source_contamination_flags': list(source_contamination_flags),
            'review_suitability': review_suitability,
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return {}
