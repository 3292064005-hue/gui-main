from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_verify_cpp_build_evidence_emits_truthful_fallback_report(tmp_path: Path) -> None:
    report = tmp_path / 'build_evidence_report.json'
    result = subprocess.run(
        [
            sys.executable,
            'scripts/verify_cpp_build_evidence.py',
            '--profile', 'mock',
            '--target-timeout-sec', '1',
            '--report', str(report),
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr or result.stdout
    payload = json.loads(report.read_text(encoding='utf-8'))
    assert payload['schema_version'] == 'cpp.build_evidence.v2'
    assert payload['path_basis'] == 'relative_to_report_dir_or_symbolic'
    assert payload['build_dir'] == '<ephemeral_tmpdir_removed>'
    assert payload['build_dir_retained'] is False
    assert payload['configure_ok'] is True
    assert payload['result_ok'] is True
    assert payload['target_timeout_sec'] == 1
    assert payload['claim_boundary'] == 'repository/sandbox only; never implies live-controller validation'
    assert payload['evidence_mode'] in {'syntax_only_fallback', 'full_target_build'}
    if payload['evidence_mode'] == 'syntax_only_fallback':
        assert payload['target_build_complete'] is False
        assert payload['syntax_only_fallback_ok'] is True
    assert all(value == 'ok' for value in payload['syntax_only_results'].values())
