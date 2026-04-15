#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

KEY_TARGETS = [
    'spine_robot_core_runtime',
    'spine_robot_core',
    'test_protocol_bridge',
    'test_rt_motion_service_truth',
    'test_recovery_manager',
]

KEY_SOURCES = [
    'cpp_robot_core/src/command_registry.cpp',
    'cpp_robot_core/src/core_runtime.cpp',
    'cpp_robot_core/src/runtime_state_store.cpp',
    'cpp_robot_core/src/sdk_robot_facade.cpp',
    'cpp_robot_core/src/rt_motion_service.cpp',
    'cpp_robot_core/src/core_runtime_session_execution.cpp',
    'cpp_robot_core/src/model_authority.cpp',
]


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=str(cwd), text=True, capture_output=True)


def choose_generator() -> list[str]:
    if shutil.which('ninja'):
        return ['-G', 'Ninja']
    return []


def configure(repo_root: Path, build_dir: Path, profile: str, with_sdk: bool, with_model: bool) -> subprocess.CompletedProcess[str]:
    cmd = [
        'cmake',
        '-S', 'cpp_robot_core',
        '-B', str(build_dir),
        '-DCMAKE_EXPORT_COMPILE_COMMANDS=ON',
        f"-DROBOT_CORE_PROFILE={profile}",
        f"-DROBOT_CORE_WITH_XCORE_SDK={'ON' if with_sdk else 'OFF'}",
        f"-DROBOT_CORE_WITH_XMATE_MODEL={'ON' if with_model else 'OFF'}",
    ]
    cmd.extend(choose_generator())
    return run(cmd, repo_root)


def syntax_only(repo_root: Path, build_dir: Path) -> dict[str, str]:
    compile_db_path = build_dir / 'compile_commands.json'
    if not compile_db_path.exists():
        return {'status': 'missing_compile_commands'}
    compile_db = json.loads(compile_db_path.read_text(encoding='utf-8'))
    by_file = {Path(entry['file']).resolve(): entry for entry in compile_db}
    results: dict[str, str] = {}
    for rel_source in KEY_SOURCES:
        source_path = (repo_root / rel_source).resolve()
        entry = by_file.get(source_path)
        if entry is None:
            results[rel_source] = 'missing'
            continue
        command = entry.get('command')
        directory = Path(entry.get('directory', build_dir))
        if not command:
            results[rel_source] = 'missing_command'
            continue
        syntax_cmd = command + ' -fsyntax-only'
        proc = subprocess.run(syntax_cmd, cwd=str(directory), shell=True, text=True, capture_output=True)
        results[rel_source] = 'ok' if proc.returncode == 0 else proc.stderr[-500:]
    return results


def build_targets(repo_root: Path, build_dir: Path, timeout_sec: int) -> dict[str, str]:
    results: dict[str, str] = {}
    for target in KEY_TARGETS:
        cmd = ['cmake', '--build', str(build_dir), '--target', target, '-j1']
        try:
            proc = subprocess.run(cmd, cwd=str(repo_root), text=True, capture_output=True, timeout=max(1, timeout_sec))
        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout.decode(errors='ignore') if isinstance(exc.stdout, bytes) else (exc.stdout or '')
            stderr = exc.stderr.decode(errors='ignore') if isinstance(exc.stderr, bytes) else (exc.stderr or '')
            combined = (stdout + '\n' + stderr).strip()
            results[target] = combined[-1000:] if combined else f'timed_out_after_{timeout_sec}s'
            break
        combined = ((proc.stdout or '') + '\n' + (proc.stderr or '')).strip()
        results[target] = 'ok' if proc.returncode == 0 else (combined[-1000:] if combined else f'build_failed_exit_{proc.returncode}')
        if proc.returncode != 0:
            break
    return results


def _portable_path(raw: str, *, base_dir: Path) -> str:
    """Return a package-portable path string when possible."""
    if not raw:
        return ''
    original = Path(raw)
    candidate = original if original.is_absolute() else (Path.cwd() / original)
    try:
        return os.path.relpath(candidate.resolve(strict=False), base_dir.resolve(strict=False))
    except ValueError:
        return str(original)


def main() -> int:
    parser = argparse.ArgumentParser(description='Produce reproducible C++ build evidence with build+syntax fallback.')
    parser.add_argument('--profile', default='hil', choices=['hil', 'mock', 'prod'])
    parser.add_argument('--with-sdk', action='store_true')
    parser.add_argument('--with-model', action='store_true')
    parser.add_argument('--report', required=True)
    parser.add_argument('--target-timeout-sec', type=int, default=45, help='per-target wall-clock timeout before syntax-only fallback is allowed')
    args = parser.parse_args()

    repo_root = Path(__file__).resolve().parents[1]
    report_path = Path(args.report)
    report_base_dir = report_path.parent
    build_dir = Path(tempfile.mkdtemp(prefix='cpp_build_evidence_', dir='/tmp'))
    report: dict[str, object] = {
        'schema_version': 'cpp.build_evidence.v2',
        'path_basis': 'relative_to_report_dir_or_symbolic',
        'profile': args.profile,
        'with_sdk': args.with_sdk,
        'with_model': args.with_model,
        'build_dir': '<ephemeral_tmpdir_removed>',
        'build_dir_retained': False,
        'build_dir_kind': 'ephemeral_tmpdir',
        'build_dir_parent': '/tmp',
        'claim_boundary': 'repository/sandbox only; never implies live-controller validation',
        'target_timeout_sec': args.target_timeout_sec,
    }
    try:
        configure_proc = configure(repo_root, build_dir, args.profile, args.with_sdk, args.with_model)
        report['configure_returncode'] = configure_proc.returncode
        report['generator'] = 'Ninja' if shutil.which('ninja') else 'default'
        if configure_proc.returncode != 0:
            report['configure_error'] = (configure_proc.stderr or configure_proc.stdout)[-1000:]
            report['configure_ok'] = False
            report['target_results'] = {}
            report['syntax_only_results'] = {}
            report['target_build_complete'] = False
            report['syntax_only_fallback_ok'] = False
            report['evidence_mode'] = 'configure_failed'
        else:
            report['configure_ok'] = True
            report['target_results'] = build_targets(repo_root, build_dir, args.target_timeout_sec)
            report['syntax_only_results'] = syntax_only(repo_root, build_dir)
            report['target_build_complete'] = bool(report['target_results']) and all(v == 'ok' for v in report['target_results'].values())
            report['syntax_only_fallback_ok'] = bool(report['syntax_only_results']) and all(v == 'ok' for v in report['syntax_only_results'].values())
            if report['target_build_complete']:
                report['evidence_mode'] = 'full_target_build'
            elif report['syntax_only_fallback_ok']:
                report['evidence_mode'] = 'syntax_only_fallback'
            else:
                report['evidence_mode'] = 'build_failed'
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    finally:
        shutil.rmtree(build_dir, ignore_errors=True)

    target_results = report.get('target_results', {})
    syntax_results = report.get('syntax_only_results', {})
    target_ok = isinstance(target_results, dict) and target_results and all(v == 'ok' for v in target_results.values())
    syntax_ok = isinstance(syntax_results, dict) and syntax_results and all(v == 'ok' for v in syntax_results.values())
    report['result_ok'] = bool(report.get('configure_returncode') == 0 and (target_ok or syntax_ok))
    report_path.write_text(json.dumps(report, indent=2), encoding='utf-8')
    return 0 if report['result_ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
