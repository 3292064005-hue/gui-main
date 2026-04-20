from __future__ import annotations

import json
from pathlib import Path
import zipfile

import pytest

from spine_ultrasound_ui.services.live_evidence_bundle_service import LiveEvidenceBundleService
from spine_ultrasound_ui.services.verification_execution_report_service import VerificationExecutionReportService


def _runtime_config() -> dict:
    return {
        'robot_model': 'xmate3',
        'sdk_robot_class': 'xMateRobot',
        'axis_count': 6,
        'preferred_link': 'wired_direct',
        'rt_mode': 'cartesianImpedance',
        'rt_phase_contract': {
            'common': {'rt_max_pose_trim_deg': 1.5},
            'seek_contact': {'contact_force_tolerance_n': 1.0, 'seek_contact_max_travel_mm': 8.0},
            'scan_follow': {'scan_force_tolerance_n': 1.0, 'scan_tangent_speed_max_mm_s': 12.0},
            'pause_hold': {'pause_hold_position_guard_mm': 0.4},
            'controlled_retract': {'retract_timeout_ms': 1200.0},
        },
    }


def _phase_metrics() -> dict:
    return {
        'seek_contact': {'contact_establish_time_ms': 300.0, 'peak_force_overshoot_n': 0.8, 'max_seek_travel_mm': 4.0},
        'scan_follow': {'normal_force_rms_error_n': 0.8, 'tangent_speed_rms_mm_s': 8.0, 'pose_trim_rms_deg': 0.4},
        'pause_hold': {'drift_mm_30s': 0.2, 'drift_mm_60s': 0.4},
        'controlled_retract': {'release_detection_time_ms': 500.0, 'total_retract_time_ms': 800.0, 'timeout_faulted': False},
    }


def _readiness_manifest() -> dict:
    return {
        'summary_state': 'ready',
        'verification': {
            'live_runtime_ready': True,
            'live_runtime_verified': False,
            'verification_boundary': 'live_runtime_unverified',
        },
    }


def _write_bundle(tmp_path: Path, *, include_readiness: bool = True) -> Path:
    bundle = tmp_path / 'live_bundle.zip'
    with zipfile.ZipFile(bundle, 'w', compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr('runtime_config.json', json.dumps(_runtime_config()))
        zf.writestr('rt_phase_metrics.json', json.dumps(_phase_metrics()))
        if include_readiness:
            zf.writestr('runtime_readiness_manifest.json', json.dumps(_readiness_manifest()))
    return bundle


def test_verification_execution_report_defaults_to_static_only_without_readiness_evidence(tmp_path: Path) -> None:
    report = VerificationExecutionReportService(tmp_path).build(
        executed_phases=['python', 'prod'],
        sdk_binding_requested=False,
        model_binding_requested=False,
    )
    assert report['schema_version'] == 'verification.execution_report.v1'
    assert report['proof_scope']['repository_proof'] is True
    assert report['proof_scope']['profile_gate_proof'] is False
    assert report['proof_scope']['sandbox_validation_possible'] is False
    assert report['proof_scope']['live_controller_validation'] is False
    assert report['reported_tiers']['已静态确认'] is True
    assert report['reported_tiers']['已沙箱验证'] is False
    assert report['reported_tiers']['未真实环境验证'] is True
    assert 'only when readiness evidence exists' in report['claim_guardrails']['safe_summary']


def test_verification_execution_report_closes_sandbox_tier_with_readiness_evidence(tmp_path: Path) -> None:
    readiness = {
        'summary_state': 'ready',
        'verification': {
            'sandbox_validation_possible': True,
            'evidence_tier': 'static_and_sandbox',
            'verification_boundary': 'live_runtime_unverified',
            'live_runtime_ready': True,
            'live_runtime_verified': False,
        },
    }
    report = VerificationExecutionReportService(tmp_path).build(
        executed_phases=['python', 'prod'],
        sdk_binding_requested=False,
        model_binding_requested=False,
        readiness_manifest=readiness,
    )
    assert report['proof_scope']['repository_proof'] is True
    assert report['proof_scope']['profile_gate_proof'] is True
    assert report['proof_scope']['sandbox_validation_possible'] is True
    assert report['reported_tiers']['已静态确认'] is True
    assert report['reported_tiers']['已沙箱验证'] is True
    assert report['reported_tiers']['未真实环境验证'] is True


def test_verification_execution_report_rejects_missing_bundle_even_with_live_flags(tmp_path: Path) -> None:
    report = VerificationExecutionReportService(tmp_path).build(
        executed_phases=['hil'],
        sdk_binding_requested=True,
        model_binding_requested=True,
        live_evidence_bundle='artifacts/hil_bundle.zip',
        readiness_manifest=_readiness_manifest(),
    )
    assert report['proof_scope']['live_controller_validation'] is False
    assert report['real_environment']['validated'] is False
    assert report['reported_tiers']['未真实环境验证'] is True
    assert 'does not exist' in report['real_environment']['reason']


@pytest.mark.parametrize('with_bindings', [False, True])
def test_verification_execution_report_only_closes_live_validation_with_real_bundle(tmp_path: Path, with_bindings: bool) -> None:
    bundle = _write_bundle(tmp_path)
    report = VerificationExecutionReportService(Path.cwd()).build(
        executed_phases=['hil'],
        sdk_binding_requested=with_bindings,
        model_binding_requested=with_bindings,
        live_evidence_bundle=str(bundle),
    )
    assert report['proof_scope']['live_controller_validation'] is with_bindings
    assert report['real_environment']['validated'] is with_bindings
    assert report['reported_tiers']['未真实环境验证'] is (not with_bindings)


def test_live_evidence_bundle_service_rejects_directory_even_if_external_readiness_exists(tmp_path: Path) -> None:
    bundle_dir = tmp_path / 'bundle_dir'
    bundle_dir.mkdir()
    (bundle_dir / 'runtime_config.json').write_text(json.dumps(_runtime_config()), encoding='utf-8')
    (bundle_dir / 'rt_phase_metrics.json').write_text(json.dumps(_phase_metrics()), encoding='utf-8')
    inspection = LiveEvidenceBundleService(Path.cwd()).inspect(
        str(bundle_dir),
        readiness_manifest=_readiness_manifest(),
        sdk_binding_requested=True,
        model_binding_requested=True,
    )
    assert inspection.valid is False
    assert inspection.bundle_kind == 'rejected'
    assert 'external readiness manifest is forbidden' in inspection.reason


def test_live_evidence_bundle_service_rejects_external_readiness_for_archived_bundle(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path)
    inspection = LiveEvidenceBundleService(Path.cwd()).inspect(
        str(bundle),
        readiness_manifest=_readiness_manifest(),
        sdk_binding_requested=True,
        model_binding_requested=True,
    )
    assert inspection.valid is False
    assert 'external readiness manifest is forbidden' in inspection.reason


def test_verification_execution_report_rejects_bundle_missing_internal_readiness_manifest(tmp_path: Path) -> None:
    bundle = _write_bundle(tmp_path, include_readiness=False)
    report = VerificationExecutionReportService(Path.cwd()).build(
        executed_phases=['hil'],
        sdk_binding_requested=True,
        model_binding_requested=True,
        live_evidence_bundle=str(bundle),
    )
    assert report['real_environment']['validated'] is False
    assert report['reported_tiers']['未真实环境验证'] is True
    assert 'runtime_readiness_manifest.json' in report['real_environment']['reason']


def test_write_verification_report_script_writes_report_and_readiness_manifest(tmp_path: Path) -> None:
    import subprocess
    import sys

    output = tmp_path / 'verification_report.json'
    readiness = tmp_path / 'runtime_readiness_manifest.json'
    script_path = Path('scripts/write_verification_report.py')
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            '--phase', 'python',
            '--phase', 'prod',
            '--output', str(output),
            '--write-readiness-manifest', str(readiness),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding='utf-8'))
    assert payload['executed_phases'] == ['python', 'prod']
    assert payload['runtime_readiness']['manifest_path'] == 'runtime_readiness_manifest.json'
    assert readiness.exists()


def test_write_verification_report_script_rejects_invalid_live_bundle(tmp_path: Path) -> None:
    import subprocess
    import sys

    output = tmp_path / 'verification_report.json'
    script_path = Path('scripts/write_verification_report.py')
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            '--phase', 'hil',
            '--with-sdk',
            '--with-model',
            '--live-evidence-bundle', str(tmp_path / 'missing.zip'),
            '--output', str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert 'invalid live evidence bundle' in result.stderr or 'invalid live evidence bundle' in result.stdout


def test_write_verification_report_script_rejects_external_readiness_with_live_bundle(tmp_path: Path) -> None:
    import subprocess
    import sys

    output = tmp_path / 'verification_report.json'
    readiness = tmp_path / 'runtime_readiness_manifest.json'
    readiness.write_text(json.dumps(_readiness_manifest()), encoding='utf-8')
    bundle = _write_bundle(tmp_path)
    script_path = Path('scripts/write_verification_report.py')
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            '--phase', 'hil',
            '--with-sdk',
            '--with-model',
            '--live-evidence-bundle', str(bundle),
            '--readiness-manifest', str(readiness),
            '--output', str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert 'do not pass --readiness-manifest together with --live-evidence-bundle' in result.stderr or 'do not pass --readiness-manifest together with --live-evidence-bundle' in result.stdout


def test_write_verification_report_script_reports_argument_conflict_without_traceback(tmp_path: Path) -> None:
    import subprocess
    import sys

    output = tmp_path / 'verification_report.json'
    readiness = tmp_path / 'runtime_readiness_manifest.json'
    readiness.write_text(json.dumps(_readiness_manifest()), encoding='utf-8')
    bundle = _write_bundle(tmp_path)
    script_path = Path('scripts/write_verification_report.py')
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            '--phase', 'hil',
            '--with-sdk',
            '--with-model',
            '--live-evidence-bundle', str(bundle),
            '--readiness-manifest', str(readiness),
            '--output', str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert '[FAIL] do not pass --readiness-manifest together with --live-evidence-bundle' in result.stderr
    assert 'Traceback' not in result.stderr



def test_write_verification_report_script_returns_distinct_exit_code_for_missing_manifest(tmp_path: Path) -> None:
    import subprocess
    import sys

    output = tmp_path / 'verification_report.json'
    missing_manifest = tmp_path / 'missing_runtime_readiness_manifest.json'
    script_path = Path('scripts/write_verification_report.py')
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            '--phase', 'python',
            '--readiness-manifest', str(missing_manifest),
            '--output', str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 3
    assert '[FAIL] readiness manifest does not exist' in result.stderr
    assert 'Traceback' not in result.stderr


def test_write_verification_report_script_returns_bundle_error_code_without_traceback(tmp_path: Path) -> None:
    import subprocess
    import sys

    output = tmp_path / 'verification_report.json'
    script_path = Path('scripts/write_verification_report.py')
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            '--phase', 'hil',
            '--with-sdk',
            '--with-model',
            '--live-evidence-bundle', str(tmp_path / 'missing_live_bundle.zip'),
            '--output', str(output),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 5
    assert '[FAIL] invalid live evidence bundle:' in result.stderr
    assert 'Traceback' not in result.stderr



def test_acceptance_summary_script_writes_machine_readable_summary(tmp_path: Path) -> None:
    import subprocess
    import sys

    summary = tmp_path / 'acceptance_summary.json'
    verification = tmp_path / 'verification_execution_report.json'
    readiness = tmp_path / 'runtime_readiness_manifest.json'
    build_evidence = tmp_path / 'build_evidence_report.json'
    verification.write_text(json.dumps({'proof_scope': {'repository_proof': True, 'profile_gate_proof': False}, 'executed_phases': ['python']}), encoding='utf-8')
    readiness.write_text(json.dumps({'summary_state': 'degraded', 'verification': {'verification_boundary': 'environment_blocked'}}), encoding='utf-8')
    build_evidence.write_text(json.dumps({'evidence_mode': 'syntax_only_fallback'}), encoding='utf-8')
    script_path = Path('scripts/write_acceptance_summary.py')
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            '--output', str(summary),
            '--build-dir', str(tmp_path / 'build'),
            '--verification-report', str(verification),
            '--readiness-manifest', str(readiness),
            '--build-evidence-report', str(build_evidence),
            '--profile', 'mock',
            '--profile', 'hil',
            '--installed-binary', str(tmp_path / 'mock/spine_robot_core'),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(summary.read_text(encoding='utf-8'))
    assert payload['schema_version'] == 'acceptance.summary.v2'
    assert payload['verification_snapshot']['reported_tiers'] == {}
    assert payload['profiles'] == []
    assert payload['requested_profiles'] == ['mock', 'hil']
    assert payload['acceptance_scope']['profile_gate_proof'] is False


def test_verification_and_acceptance_summary_chain_can_materialize_reports(tmp_path: Path) -> None:
    import subprocess
    import sys

    verification = tmp_path / 'verification_execution_report.json'
    readiness = tmp_path / 'runtime_readiness_manifest.json'
    build_evidence = tmp_path / 'build_evidence_report.json'
    acceptance = tmp_path / 'acceptance_summary.json'

    verification_script = Path('scripts/write_verification_report.py')
    verification_result = subprocess.run(
        [
            sys.executable,
            str(verification_script),
            '--phase', 'python',
            '--phase', 'mock',
            '--output', str(verification),
            '--write-readiness-manifest', str(readiness),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert verification_result.returncode == 0, verification_result.stderr

    build_evidence.write_text(json.dumps({'profile': 'mock', 'target_results': {'spine_robot_core': 'ok'}, 'evidence_mode': 'syntax_only_fallback', 'claim_boundary': 'repository/sandbox only'}, indent=2), encoding='utf-8')
    acceptance_script = Path('scripts/write_acceptance_summary.py')
    acceptance_result = subprocess.run(
        [
            sys.executable,
            str(acceptance_script),
            '--output', str(acceptance),
            '--build-dir', str(tmp_path / 'build'),
            '--verification-report', str(verification),
            '--readiness-manifest', str(readiness),
            '--build-evidence-report', str(build_evidence),
            '--profile', 'mock',
            '--installed-binary', str(tmp_path / 'mock/spine_robot_core'),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert acceptance_result.returncode == 0, acceptance_result.stderr
    payload = json.loads(acceptance.read_text(encoding='utf-8'))
    assert payload['path_basis'] == 'relative_to_summary_dir'
    assert payload['verification_report'] == 'verification_execution_report.json'
    assert payload['readiness_manifest'] == 'runtime_readiness_manifest.json'
    assert payload['build_evidence_report'] == 'build_evidence_report.json'
    assert payload['verification_snapshot']['verification_boundary'] == 'environment_blocked'
    assert payload['verification_snapshot']['build_evidence_mode'] == 'syntax_only_fallback'
    assert payload['profiles'] == ['mock']
    assert payload['requested_profiles'] == ['mock']
    assert payload['acceptance_scope']['validated_profiles'] == ['mock']



def test_final_acceptance_audit_script_declares_full_cpp_gate_contract() -> None:
    script = Path('scripts/final_acceptance_audit.sh').read_text(encoding='utf-8')
    for target in (
        'test_normal_force_estimator',
        'test_normal_axis_admittance_controller',
        'test_tangential_scan_controller',
        'test_orientation_trim_controller',
        'test_contact_control_contract',
        'test_recording_service',
        'test_rt_motion_service_truth',
    ):
        assert target in script
    assert 'count_registered_cpp_tests' in script
    assert 'EXPECTED_CPP_TEST_COUNT' in script



def test_write_acceptance_summary_uses_portable_relative_paths(tmp_path: Path) -> None:
    import subprocess
    import sys

    summary = tmp_path / 'proof' / 'acceptance_summary.json'
    build_dir = tmp_path / 'build'
    verification = tmp_path / 'proof' / 'verification_execution_report.json'
    readiness = tmp_path / 'proof' / 'runtime_readiness_manifest.json'
    evidence = tmp_path / 'proof' / 'build_evidence_report.json'
    installed = build_dir / 'mock' / 'spine_robot_core'
    verification.parent.mkdir(parents=True, exist_ok=True)
    verification.write_text(json.dumps({'proof_scope': {'repository_proof': True, 'profile_gate_proof': False}, 'executed_phases': ['python']}), encoding='utf-8')
    readiness.write_text(json.dumps({'summary_state': 'degraded', 'verification': {'verification_boundary': ''}}), encoding='utf-8')
    evidence.write_text(json.dumps({'evidence_mode': ''}), encoding='utf-8')
    script_path = Path('scripts/write_acceptance_summary.py')
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            '--output', str(summary),
            '--build-dir', str(build_dir),
            '--verification-report', str(verification),
            '--readiness-manifest', str(readiness),
            '--build-evidence-report', str(evidence),
            '--installed-binary', str(installed),
            '--profile', 'mock',
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(summary.read_text(encoding='utf-8'))
    assert payload['path_basis'] == 'relative_to_summary_dir'
    assert payload['build_dir'] == '../build'
    assert payload['verification_report'] == 'verification_execution_report.json'
    assert payload['readiness_manifest'] == 'runtime_readiness_manifest.json'
    assert payload['build_evidence_report'] == 'build_evidence_report.json'
    assert payload['verification_snapshot']['verification_boundary'] == ''
    assert payload['verification_snapshot']['build_evidence_mode'] == ''
    assert payload['installed_binaries'] == ['../build/mock/spine_robot_core']
    assert payload['verification_snapshot']['verification_boundary'] == ''
    assert payload['profiles'] == []
    assert payload['requested_profiles'] == ['mock']


def test_write_verification_report_uses_portable_relative_manifest_path(tmp_path: Path) -> None:
    import subprocess
    import sys

    output_dir = tmp_path / 'proof'
    output = output_dir / 'verification_execution_report.json'
    readiness = output_dir / 'runtime_readiness_manifest.json'
    script_path = Path('scripts/write_verification_report.py')
    result = subprocess.run(
        [
            sys.executable,
            str(script_path),
            '--phase', 'python',
            '--output', str(output),
            '--write-readiness-manifest', str(readiness),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(output.read_text(encoding='utf-8'))
    assert payload['runtime_readiness']['manifest_path'] == 'runtime_readiness_manifest.json'



def test_acceptance_summary_falls_back_to_verification_report_when_local_readiness_manifest_is_omitted(tmp_path: Path) -> None:
    import subprocess
    import sys

    summary = tmp_path / 'acceptance_summary.json'
    verification = tmp_path / 'verification_execution_report.json'
    build_evidence = tmp_path / 'build_evidence_report.json'
    verification.write_text(json.dumps({
        'proof_scope': {'repository_proof': True, 'profile_gate_proof': True, 'profile_phases': ['mock']},
        'executed_phases': ['python', 'mock'],
        'reported_tiers': {'python': 'repository'},
        'runtime_readiness': {
            'source': 'embedded_live_bundle',
            'summary_state': 'ready',
            'verification_boundary': 'live_runtime_unverified',
            'evidence_tier': 'live_bundle',
            'live_runtime_ready': True,
            'live_runtime_verified': False,
        },
        'claim_guardrails': {'safe_summary': 'claim-safe'},
    }, indent=2), encoding='utf-8')
    build_evidence.write_text(json.dumps({'evidence_mode': 'live_bundle_index', 'claim_boundary': 'claim-safe'}, indent=2), encoding='utf-8')

    result = subprocess.run(
        [
            sys.executable,
            'scripts/write_acceptance_summary.py',
            '--output', str(summary),
            '--build-dir', str(tmp_path / 'build'),
            '--verification-report', str(verification),
            '--build-evidence-report', str(build_evidence),
            '--profile', 'mock',
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stderr
    payload = json.loads(summary.read_text(encoding='utf-8'))
    assert payload['readiness_manifest'] == ''
    assert payload['verification_snapshot']['summary_state'] == 'ready'
    assert payload['verification_snapshot']['verification_boundary'] == 'live_runtime_unverified'
    assert payload['verification_snapshot']['evidence_tier'] == 'live_bundle'
    assert payload['verification_snapshot']['runtime_readiness_source'] == 'verification_report'




def test_write_acceptance_summary_fails_closed_when_required_reports_are_missing(tmp_path: Path) -> None:
    import subprocess
    import sys

    summary = tmp_path / 'acceptance_summary.json'
    result = subprocess.run(
        [
            sys.executable,
            'scripts/write_acceptance_summary.py',
            '--output', str(summary),
            '--build-dir', str(tmp_path / 'build'),
            '--verification-report', str(tmp_path / 'missing_verification_execution_report.json'),
            '--build-evidence-report', str(tmp_path / 'missing_build_evidence_report.json'),
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 2
    assert '[FAIL] verification report file does not exist:' in result.stderr
    assert not summary.exists()


def test_verification_execution_report_uses_embedded_bundle_readiness_snapshot(tmp_path: Path) -> None:
    readiness_manifest = {
        'summary_state': 'ready',
        'verification': {
            'verification_boundary': 'live_runtime_unverified',
            'evidence_tier': 'live_bundle',
            'live_runtime_ready': True,
            'live_runtime_verified': False,
        },
    }
    bundle = tmp_path / 'live_bundle.zip'
    with zipfile.ZipFile(bundle, 'w') as zf:
        zf.writestr('runtime_config.json', json.dumps(_runtime_config()))
        zf.writestr('rt_phase_metrics.json', json.dumps(_phase_metrics()))
        zf.writestr('runtime_readiness_manifest.json', json.dumps(readiness_manifest))

    report = VerificationExecutionReportService(Path.cwd()).build(
        executed_phases=['python', 'mock'],
        sdk_binding_requested=True,
        model_binding_requested=True,
        readiness_manifest_path='should_not_be_used.json',
        readiness_manifest={'summary_state': 'blocked', 'verification': {'verification_boundary': 'environment_blocked'}},
        live_evidence_bundle=str(bundle),
    )
    runtime = dict(report['runtime_readiness'])
    assert runtime['manifest_path'] == ''
    assert runtime['source'] == 'embedded_live_bundle'
    assert runtime['summary_state'] == 'ready'
    assert runtime['verification_boundary'] == 'live_runtime_unverified'
    assert runtime['evidence_tier'] == 'live_bundle'
    assert runtime['live_runtime_ready'] is True
    assert runtime['live_runtime_verified'] is False
