#!/usr/bin/env python3
from __future__ import annotations

"""Write a machine-readable acceptance summary for the current audit run.

This script intentionally performs only lightweight validation and does not
claim that any referenced report has been produced by a real controller or HIL
run. It is the final report-linking step of the acceptance chain and must stay
parseable/executable because repository gates depend on it.
"""

import argparse
import json
import os
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for acceptance-summary emission.

    Returns:
        Parsed namespace containing output/report paths and requested binding
        flags.
    """
    parser = argparse.ArgumentParser(description='Write a machine-readable acceptance summary for the current audit run')
    parser.add_argument('--output', required=True, help='target JSON path for the acceptance summary')
    parser.add_argument('--build-dir', required=True, help='root build directory used by the acceptance run')
    parser.add_argument('--verification-report', required=True, help='verification execution report JSON path')
    parser.add_argument('--readiness-manifest', required=True, help='runtime readiness manifest JSON path')
    parser.add_argument('--build-evidence-report', required=True, help='C++ build evidence report JSON path')
    parser.add_argument('--with-sdk', action='store_true', help='record that live SDK bindings were requested')
    parser.add_argument('--with-model', action='store_true', help='record that live model bindings were requested')
    parser.add_argument('--profile', action='append', dest='profiles', default=[], help='accepted profile; repeat as needed')
    parser.add_argument('--installed-binary', action='append', dest='installed_binaries', default=[], help='installed binary produced by the run; repeat as needed')
    return parser.parse_args()


def _portable_path(raw: str, *, base_dir: Path) -> str:
    """Return a package-portable path string when possible.

    Package-contained proof members should not capture build-machine absolute
    paths. This helper rewrites such references relative to the summary file
    directory while leaving unrelated external paths unchanged.
    """
    if not raw:
        return ''
    original = Path(raw)
    candidate = original if original.is_absolute() else (Path.cwd() / original)
    try:
        return os.path.relpath(candidate.resolve(strict=False), base_dir.resolve(strict=False))
    except ValueError:
        return str(original)



def _load_json_dict(raw: str) -> dict:
    """Load an optional JSON object without turning summary emission into a hard gate.

    Args:
        raw: User-provided path string.

    Returns:
        Parsed JSON object when available and valid; otherwise an empty dict.

    Boundary behavior:
        Missing files, invalid JSON, or non-object payloads are intentionally
        treated as absent evidence because upstream generators own semantic
        validation. The acceptance summary only mirrors linked proof metadata.
    """
    if not raw:
        return {}
    try:
        candidate = Path(raw)
        payload = json.loads(candidate.read_text(encoding='utf-8'))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}



def _validated_profiles(*, verification_report: dict, requested_profiles: list[str]) -> list[str]:
    """Return only profiles that are actually closed by verification evidence.

    Args:
        verification_report: Parsed verification execution report payload.
        requested_profiles: Profiles the caller says were intended for acceptance.

    Returns:
        Profiles that are both requested and present in
        ``proof_scope.profile_phases`` when ``profile_gate_proof`` is true.

    Boundary behavior:
        When the linked verification report does not close profile-gate proof,
        this function returns an empty list even if callers passed profile names.
        This prevents acceptance summaries from overstating repository-only runs
        as if mock/HIL/prod acceptance had completed.
    """
    proof_scope = dict(verification_report.get('proof_scope') or {})
    if not bool(proof_scope.get('profile_gate_proof', False)):
        return []
    proven = [str(item).strip() for item in proof_scope.get('profile_phases', []) if str(item).strip()]
    requested = [str(item).strip() for item in requested_profiles if str(item).strip()]
    if not requested:
        return proven
    return [item for item in requested if item in proven]

def _verification_snapshot(*, verification_report: dict, readiness_manifest: dict, build_evidence_report: dict) -> dict:
    """Summarize linked verification evidence inside the acceptance payload.

    This prevents callers from needing to dereference three separate JSON files
    before they can understand the current claim boundary.
    """
    readiness_verification = dict(readiness_manifest.get('verification') or {})
    reported_tiers = dict(verification_report.get('reported_tiers') or {})
    return {
        'summary_state': str(readiness_manifest.get('summary_state', '')),
        'verification_boundary': str(readiness_verification.get('verification_boundary', '')),
        'evidence_tier': str(readiness_verification.get('evidence_tier', '')),
        'live_runtime_ready': bool(readiness_verification.get('live_runtime_ready', False)),
        'live_runtime_verified': bool(readiness_verification.get('live_runtime_verified', False)),
        'reported_tiers': reported_tiers,
        'claim_boundary': str(build_evidence_report.get('claim_boundary') or verification_report.get('claim_guardrails', {}).get('safe_summary', '')),
        'build_evidence_mode': str(build_evidence_report.get('evidence_mode', '')),
    }


def main() -> int:
    """Build and persist the acceptance summary payload.

    Returns:
        ``0`` when the summary file is written successfully.

    Boundary behavior:
        The script records package-local references relative to the summary file
        directory. Existence/semantic validation of the referenced reports
        belongs to the upstream acceptance steps that generated them.
    """
    args = parse_args()
    output = Path(args.output)
    base_dir = output.parent
    verification_report_payload = _load_json_dict(args.verification_report)
    readiness_manifest_payload = _load_json_dict(args.readiness_manifest)
    build_evidence_payload = _load_json_dict(args.build_evidence_report)
    validated_profiles = _validated_profiles(
        verification_report=verification_report_payload,
        requested_profiles=list(args.profiles),
    )
    payload = {
        'schema_version': 'acceptance.summary.v2',
        'path_basis': 'relative_to_summary_dir',
        'build_dir': _portable_path(args.build_dir, base_dir=base_dir),
        'verification_report': _portable_path(args.verification_report, base_dir=base_dir),
        'readiness_manifest': _portable_path(args.readiness_manifest, base_dir=base_dir),
        'build_evidence_report': _portable_path(args.build_evidence_report, base_dir=base_dir),
        'profiles': validated_profiles,
        'requested_profiles': list(args.profiles),
        'installed_binaries': [_portable_path(item, base_dir=base_dir) for item in args.installed_binaries],
        'requested_bindings': {
            'with_sdk': bool(args.with_sdk),
            'with_model': bool(args.with_model),
        },
        'acceptance_scope': {
            'executed_phases': list(verification_report_payload.get('executed_phases') or []),
            'repository_proof': bool((verification_report_payload.get('proof_scope') or {}).get('repository_proof', False)),
            'profile_gate_proof': bool((verification_report_payload.get('proof_scope') or {}).get('profile_gate_proof', False)),
            'validated_profiles': validated_profiles,
            'unvalidated_requested_profiles': [item for item in args.profiles if item not in validated_profiles],
            'claim_boundary': 'profiles only close when verification_report.proof_scope.profile_gate_proof is true',
        },
        'verification_snapshot': _verification_snapshot(
            verification_report=verification_report_payload,
            readiness_manifest=readiness_manifest_payload,
            build_evidence_report=build_evidence_payload,
        ),
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({'ok': True, 'summary': _portable_path(str(output), base_dir=base_dir)}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
