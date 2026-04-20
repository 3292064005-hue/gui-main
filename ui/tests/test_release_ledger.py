from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys


def test_write_release_ledger_uses_portable_relative_paths(tmp_path: Path) -> None:
    ledger = tmp_path / 'proof' / 'release_ledger.json'
    build_dir = tmp_path / 'build'
    verification = tmp_path / 'proof' / 'verification_execution_report.json'
    readiness = tmp_path / 'proof' / 'runtime_readiness_manifest.json'
    build_evidence = tmp_path / 'proof' / 'build_evidence_report.json'
    acceptance = tmp_path / 'proof' / 'acceptance_summary.json'
    live_bundle = tmp_path / 'proof' / 'live_bundle.zip'
    installed = build_dir / 'hil' / 'spine_robot_core'

    verification.parent.mkdir(parents=True, exist_ok=True)
    verification.write_text(json.dumps({
        'claim_guardrails': {
            'safe_summary': 'repository/sandbox only; never implies live-controller validation',
            'next_required_evidence': ['enabled runtime build proof', 'live bundle'],
        },
        'proof_scope': {
            'repository_proof': True,
            'profile_gate_proof': False,
            'profile_phases': ['python', 'mock'],
        },
        'real_environment': {
            'bundle_validation': {
                'valid': False,
                'reason': 'missing live bundle',
            },
        },
        'reported_tiers': {'python': 'repository'},
    }, indent=2), encoding='utf-8')
    readiness.write_text(json.dumps({
        'summary_state': 'degraded',
        'verification': {
            'verification_boundary': 'environment_blocked',
            'evidence_tier': 'repository',
            'live_runtime_ready': False,
            'live_runtime_verified': False,
        },
    }, indent=2), encoding='utf-8')
    build_evidence.write_text(json.dumps({
        'evidence_mode': 'syntax_only_fallback',
        'claim_boundary': 'repository/sandbox only; never implies live-controller validation',
    }, indent=2), encoding='utf-8')
    acceptance.write_text(json.dumps({
        'acceptance_scope': {
            'validated_profiles': ['mock'],
            'unvalidated_requested_profiles': ['hil'],
        },
        'verification_snapshot': {
            'claim_boundary': 'repository/sandbox only; never implies live-controller validation',
            'verification_boundary': 'environment_blocked',
            'evidence_tier': 'repository',
            'build_evidence_mode': 'syntax_only_fallback',
            'reported_tiers': {'python': 'repository'},
        },
    }, indent=2), encoding='utf-8')
    live_bundle.write_bytes(b'PK\x05\x06' + b'\x00' * 18)

    result = subprocess.run(
        [
            sys.executable,
            'scripts/write_release_ledger.py',
            '--output', str(ledger),
            '--build-dir', str(build_dir),
            '--verification-report', str(verification),
            '--readiness-manifest', str(readiness),
            '--build-evidence-report', str(build_evidence),
            '--acceptance-summary', str(acceptance),
            '--live-evidence-bundle', str(live_bundle),
            '--with-sdk',
            '--profile', 'mock',
            '--profile', 'hil',
            '--installed-binary', str(installed),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(ledger.read_text(encoding='utf-8'))
    assert payload['schema_version'] == 'release.ledger.v1'
    assert payload['path_basis'] == 'relative_to_ledger_dir'
    assert payload['build_dir'] == '../build'
    assert payload['verification_report'] == 'verification_execution_report.json'
    assert payload['readiness_manifest'] == 'runtime_readiness_manifest.json'
    assert payload['build_evidence_report'] == 'build_evidence_report.json'
    assert payload['acceptance_summary'] == 'acceptance_summary.json'
    assert payload['live_evidence_bundle'] == 'live_bundle.zip'
    assert payload['requested_bindings']['with_sdk'] is True
    assert payload['requested_bindings']['with_model'] is False
    assert payload['requested_profiles'] == ['mock', 'hil']
    assert payload['installed_binaries'] == ['../build/hil/spine_robot_core']
    assert payload['verification_boundary'] == 'environment_blocked'
    assert payload['build_evidence_mode'] == 'syntax_only_fallback'
    assert payload['proof_scope']['validated_profiles'] == ['mock']
    assert payload['proof_scope']['unvalidated_requested_profiles'] == ['hil']
    assert payload['runtime_verification']['live_evidence_bundle_validated'] is False
    assert payload['guardrails']['next_required_evidence'] == ['enabled runtime build proof', 'live bundle']



def test_write_release_ledger_falls_back_to_verification_report_when_readiness_manifest_is_omitted(tmp_path: Path) -> None:
    ledger = tmp_path / 'proof' / 'release_ledger.json'
    build_dir = tmp_path / 'build'
    verification = tmp_path / 'proof' / 'verification_execution_report.json'
    build_evidence = tmp_path / 'proof' / 'build_evidence_report.json'
    acceptance = tmp_path / 'proof' / 'acceptance_summary.json'

    verification.parent.mkdir(parents=True, exist_ok=True)
    verification.write_text(json.dumps({
        'claim_guardrails': {'safe_summary': 'claim-safe'},
        'proof_scope': {'repository_proof': True, 'profile_gate_proof': True, 'profile_phases': ['mock']},
        'runtime_readiness': {
            'source': 'embedded_live_bundle',
            'summary_state': 'ready',
            'verification_boundary': 'live_runtime_unverified',
            'evidence_tier': 'live_bundle',
            'live_runtime_ready': True,
            'live_runtime_verified': False,
        },
        'real_environment': {'bundle_validation': {'valid': True, 'reason': 'ok'}},
    }, indent=2), encoding='utf-8')
    build_evidence.write_text(json.dumps({'evidence_mode': 'live_bundle_index', 'claim_boundary': 'claim-safe'}, indent=2), encoding='utf-8')
    acceptance.write_text(json.dumps({
        'acceptance_scope': {'validated_profiles': ['mock'], 'unvalidated_requested_profiles': []},
        'verification_snapshot': {
            'claim_boundary': 'claim-safe',
            'verification_boundary': 'live_runtime_unverified',
            'evidence_tier': 'live_bundle',
            'build_evidence_mode': 'live_bundle_index',
            'reported_tiers': {'python': 'repository'},
        },
    }, indent=2), encoding='utf-8')

    result = subprocess.run(
        [
            sys.executable,
            'scripts/write_release_ledger.py',
            '--output', str(ledger),
            '--build-dir', str(build_dir),
            '--verification-report', str(verification),
            '--build-evidence-report', str(build_evidence),
            '--acceptance-summary', str(acceptance),
            '--profile', 'mock',
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(ledger.read_text(encoding='utf-8'))
    assert payload['readiness_manifest'] == ''
    assert payload['runtime_verification']['summary_state'] == 'ready'
    assert payload['runtime_verification']['source'] == 'verification_report'
    assert payload['verification_boundary'] == 'live_runtime_unverified'
    assert payload['evidence_tier'] == 'live_bundle'



def test_write_release_ledger_fails_closed_when_required_reports_are_missing(tmp_path: Path) -> None:
    ledger = tmp_path / 'proof' / 'release_ledger.json'
    build_dir = tmp_path / 'build'

    result = subprocess.run(
        [
            sys.executable,
            'scripts/write_release_ledger.py',
            '--output', str(ledger),
            '--build-dir', str(build_dir),
            '--verification-report', str(tmp_path / 'missing_verification_execution_report.json'),
            '--build-evidence-report', str(tmp_path / 'missing_build_evidence_report.json'),
            '--acceptance-summary', str(tmp_path / 'missing_acceptance_summary.json'),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert '[FAIL] verification report file does not exist:' in result.stderr
    assert not ledger.exists()
