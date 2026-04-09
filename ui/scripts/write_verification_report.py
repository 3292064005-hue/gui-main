#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.runtime_readiness_manifest_service import RuntimeReadinessManifestService
from spine_ultrasound_ui.services.verification_execution_report_service import VerificationExecutionReportService


class ArgumentConflictError(ValueError):
    pass


class ManifestInputError(FileNotFoundError):
    pass


class ManifestFormatError(ValueError):
    pass


class BundleValidationError(ValueError):
    pass


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


def _portable_report_paths(report: dict, *, base_dir: Path) -> dict:
    """Rewrite package-local report paths to be relative to the report file."""
    runtime = dict(report.get('runtime_readiness') or {})
    runtime['manifest_path'] = _portable_path(str(runtime.get('manifest_path', '') or ''), base_dir=base_dir)
    report['runtime_readiness'] = runtime
    real_environment = dict(report.get('real_environment') or {})
    real_environment['evidence_bundle'] = _portable_path(str(real_environment.get('evidence_bundle', '') or ''), base_dir=base_dir)
    bundle_validation = dict(real_environment.get('bundle_validation') or {})
    bundle_validation['bundle_path'] = _portable_path(str(bundle_validation.get('bundle_path', '') or ''), base_dir=base_dir)
    real_environment['bundle_validation'] = bundle_validation
    report['real_environment'] = real_environment
    return report


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Write a claim-safe verification execution report')
    parser.add_argument('--phase', action='append', dest='phases', default=[], help='executed verification phase; repeat as needed')
    parser.add_argument('--with-sdk', action='store_true', help='record that the run requested live SDK bindings')
    parser.add_argument('--with-model', action='store_true', help='record that the run requested live model bindings')
    parser.add_argument('--surface', choices=('desktop', 'headless'), default='desktop', help='surface used to derive runtime readiness manifest')
    parser.add_argument('--output', required=True, help='path to write the verification report JSON')
    parser.add_argument('--readiness-manifest', default='', help='optional precomputed runtime readiness manifest path (for static/sandbox reporting only)')
    parser.add_argument('--write-readiness-manifest', default='', help='optional path to write the runtime readiness manifest JSON')
    parser.add_argument('--live-evidence-bundle', default='', help='path to archived live-controller evidence bundle (.zip only)')
    return parser.parse_args()


def _load_manifest(manifest_path: Path) -> dict:
    data = json.loads(manifest_path.read_text(encoding='utf-8'))
    if not isinstance(data, dict):
        raise ManifestFormatError(f'readiness manifest must contain a top-level JSON object: {manifest_path}')
    return data


def main() -> int:
    args = parse_args()
    if args.live_evidence_bundle and args.readiness_manifest:
        raise ArgumentConflictError('do not pass --readiness-manifest together with --live-evidence-bundle; live validation must read runtime_readiness_manifest.json from the archived bundle itself')
    if args.live_evidence_bundle and args.write_readiness_manifest:
        raise ArgumentConflictError('do not pass --write-readiness-manifest together with --live-evidence-bundle; generate the readiness manifest before packaging the archived live evidence bundle')

    config = RuntimeConfig()
    readiness_service = RuntimeReadinessManifestService(ROOT)
    readiness_manifest = readiness_service.build(config=config, surface=args.surface, env=dict(os.environ))
    readiness_path = ''

    if args.readiness_manifest:
        manifest_path = Path(args.readiness_manifest)
        if not manifest_path.exists():
            raise ManifestInputError(f'readiness manifest does not exist: {manifest_path}')
        readiness_manifest = _load_manifest(manifest_path)
        readiness_path = str(manifest_path)
    elif args.write_readiness_manifest:
        manifest_path = Path(args.write_readiness_manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(json.dumps(readiness_manifest, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
        readiness_path = str(manifest_path)

    service = VerificationExecutionReportService(ROOT)
    report = service.build(
        executed_phases=args.phases,
        sdk_binding_requested=args.with_sdk,
        model_binding_requested=args.with_model,
        readiness_manifest_path=readiness_path,
        readiness_manifest=readiness_manifest,
        live_evidence_bundle=args.live_evidence_bundle,
    )
    bundle_validation = dict(((report.get('real_environment') or {}).get('bundle_validation') or {}))
    if args.live_evidence_bundle and not bool(bundle_validation.get('valid', False)):
        raise BundleValidationError(f'invalid live evidence bundle: {bundle_validation.get("reason", "unknown reason")}')
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report = _portable_report_paths(report, base_dir=output_path.parent)
    output_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({
        'ok': True,
        'report': _portable_path(str(output_path), base_dir=output_path.parent),
        'summary': report['claim_guardrails']['safe_summary'],
        'tiers': report['reported_tiers'],
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except ArgumentConflictError as exc:
        print(f'[FAIL] {exc}', file=sys.stderr)
        raise SystemExit(2)
    except ManifestInputError as exc:
        print(f'[FAIL] {exc}', file=sys.stderr)
        raise SystemExit(3)
    except (ManifestFormatError, json.JSONDecodeError) as exc:
        print(f'[FAIL] {exc}', file=sys.stderr)
        raise SystemExit(4)
    except BundleValidationError as exc:
        print(f'[FAIL] {exc}', file=sys.stderr)
        raise SystemExit(5)
