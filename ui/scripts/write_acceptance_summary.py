#!/usr/bin/env python3
from __future__ import annotations

"""Write a machine-readable acceptance summary for the current audit run.

This script intentionally keeps claim boundaries conservative, but it is strict
about the presence of the upstream reports it links. Final acceptance artifacts
must not materialize from missing or invalid required evidence.
"""

import argparse
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services.deployment_profile_service import DeploymentProfileService


class EvidenceLoadError(RuntimeError):
    """Raised when a required evidence file is missing or malformed."""


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
    parser.add_argument('--readiness-manifest', default='', help='optional runtime readiness manifest JSON path; omit when verification evidence comes from an archived live bundle')
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
        return os.path.relpath(candidate.resolve(strict=False), base_dir.resolve(strict=False)).replace("\\", "/")
    except ValueError:
        return str(original).replace("\\", "/")



def _load_json_dict(raw: str, *, label: str, required: bool) -> dict:
    """Load a JSON object from disk.

    Required evidence fails closed. Optional readiness evidence may be omitted
    for live-bundle flows that intentionally do not materialize a standalone
    local readiness manifest.
    """
    if not raw:
        if required:
            raise EvidenceLoadError(f'{label} path is required')
        return {}
    candidate = Path(raw)
    if not candidate.is_file():
        if required:
            raise EvidenceLoadError(f'{label} file does not exist: {raw}')
        return {}
    try:
        payload = json.loads(candidate.read_text(encoding='utf-8'))
    except json.JSONDecodeError as exc:
        raise EvidenceLoadError(f'{label} is not valid JSON: {raw} ({exc.msg})') from exc
    except OSError as exc:
        raise EvidenceLoadError(f'{label} could not be read: {raw} ({exc})') from exc
    if not isinstance(payload, dict):
        raise EvidenceLoadError(f'{label} must be a JSON object: {raw}')
    return payload



def _normalize_profiles(items: list[str]) -> list[str]:
    """Return canonical profile names while preserving first-seen order.

    Args:
        items: Raw profile tokens from scripts or upstream reports.

    Returns:
        Canonical profile names compatible with the deployment matrix.
    """
    normalized: list[str] = []
    for raw in items:
        token = DeploymentProfileService.normalize_profile_name(raw)
        if not token or token in normalized:
            continue
        normalized.append(token)
    return normalized


def _validated_profiles(*, verification_report: dict, requested_profiles: list[str]) -> list[str]:
    """Return only canonical profiles that are actually closed by verification evidence."""
    proof_scope = dict(verification_report.get('proof_scope') or {})
    if not bool(proof_scope.get('profile_gate_proof', False)):
        return []
    proven = _normalize_profiles([str(item).strip() for item in proof_scope.get('profile_phases', []) if str(item).strip()])
    requested = _normalize_profiles([str(item).strip() for item in requested_profiles if str(item).strip()])
    if not requested:
        return proven
    return [item for item in requested if item in proven]


def _verification_snapshot(*, verification_report: dict, readiness_manifest: dict, build_evidence_report: dict) -> dict:
    """Summarize linked verification evidence inside the acceptance payload."""
    readiness_verification = dict(readiness_manifest.get('verification') or {})
    verification_runtime = dict(verification_report.get('runtime_readiness') or {})
    reported_tiers = dict(verification_report.get('reported_tiers') or {})
    proof_scope = dict(verification_report.get('proof_scope') or {})
    real_environment = dict(verification_report.get('real_environment') or {})
    summary_state = str(readiness_manifest.get('summary_state', '') or verification_runtime.get('summary_state', ''))
    verification_boundary = str(readiness_verification.get('verification_boundary', '') or verification_runtime.get('verification_boundary', ''))
    evidence_tier = str(readiness_verification.get('evidence_tier', '') or verification_runtime.get('evidence_tier', ''))
    build_evidence_mode = str(build_evidence_report.get('evidence_mode', ''))
    evidence_components = {
        'repo_proof': bool(proof_scope.get('repository_proof', False)),
        'sandbox_proof': bool(proof_scope.get('profile_gate_proof', False)),
        'build_proof': bool(build_evidence_mode),
        'live_hil_proof': bool(real_environment.get('validated', False)),
    }
    return {
        'summary_state': summary_state,
        'verification_boundary': verification_boundary,
        'evidence_tier': evidence_tier,
        'live_runtime_ready': bool(readiness_verification.get('live_runtime_ready', verification_runtime.get('live_runtime_ready', False))),
        'live_runtime_verified': bool(readiness_verification.get('live_runtime_verified', verification_runtime.get('live_runtime_verified', False))),
        'runtime_readiness_source': 'linked_manifest' if readiness_manifest else 'verification_report',
        'reported_tiers': reported_tiers,
        'claim_boundary': str(build_evidence_report.get('claim_boundary') or verification_report.get('claim_guardrails', {}).get('safe_summary', '')),
        'build_evidence_mode': build_evidence_mode,
        'evidence_components': evidence_components,
        'claim_evaluator': {
            'claim_closed': bool(evidence_components['repo_proof'] and evidence_components['build_proof']),
            'requires_live_hil_for_profiles': [str(item) for item in proof_scope.get('profile_phases', []) if str(item) in {'research', 'clinical'}],
            'live_hil_closed': bool(evidence_components['live_hil_proof']),
        },
    }


def main() -> int:
    """Build and persist the acceptance summary payload."""
    args = parse_args()
    output = Path(args.output)
    base_dir = output.parent
    try:
        verification_report_payload = _load_json_dict(args.verification_report, label='verification report', required=True)
        readiness_manifest_payload = _load_json_dict(args.readiness_manifest, label='runtime readiness manifest', required=False)
        build_evidence_payload = _load_json_dict(args.build_evidence_report, label='build evidence report', required=True)
    except EvidenceLoadError as exc:
        print(f'[FAIL] {exc}', file=os.sys.stderr)
        return 2
    requested_profiles = _normalize_profiles(list(args.profiles))
    validated_profiles = _validated_profiles(
        verification_report=verification_report_payload,
        requested_profiles=requested_profiles,
    )
    payload = {
        'schema_version': 'acceptance.summary.v2',
        'path_basis': 'relative_to_summary_dir',
        'build_dir': _portable_path(args.build_dir, base_dir=base_dir),
        'verification_report': _portable_path(args.verification_report, base_dir=base_dir),
        'readiness_manifest': _portable_path(args.readiness_manifest, base_dir=base_dir),
        'build_evidence_report': _portable_path(args.build_evidence_report, base_dir=base_dir),
        'profiles': validated_profiles,
        'requested_profiles': requested_profiles,
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
            'unvalidated_requested_profiles': [item for item in requested_profiles if item not in validated_profiles],
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
