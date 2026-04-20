#!/usr/bin/env python3
from __future__ import annotations

"""Emit a single machine-readable release ledger for the acceptance run."""

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from spine_ultrasound_ui.services.release_ledger_service import ReleaseLedgerEvidenceError, ReleaseLedgerService


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Write a claim-safe release ledger')
    parser.add_argument('--output', required=True, help='target JSON path for the release ledger')
    parser.add_argument('--build-dir', required=True, help='root build directory used by the acceptance run')
    parser.add_argument('--verification-report', required=True, help='verification execution report JSON path')
    parser.add_argument('--readiness-manifest', default='', help='optional runtime readiness manifest JSON path; omit when verification evidence comes from an archived live bundle')
    parser.add_argument('--build-evidence-report', required=True, help='C++ build evidence report JSON path')
    parser.add_argument('--acceptance-summary', required=True, help='acceptance summary JSON path')
    parser.add_argument('--live-evidence-bundle', default='', help='optional archived live evidence bundle path')
    parser.add_argument('--with-sdk', action='store_true', help='record that live SDK bindings were requested')
    parser.add_argument('--with-model', action='store_true', help='record that live model bindings were requested')
    parser.add_argument('--profile', action='append', dest='profiles', default=[], help='requested profile; repeat as needed')
    parser.add_argument('--installed-binary', action='append', dest='installed_binaries', default=[], help='installed binary produced by the run; repeat as needed')
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output_path = Path(args.output)
    service = ReleaseLedgerService(output_path=output_path)
    try:
        payload = service.build(
            build_dir=args.build_dir,
            verification_report=args.verification_report,
            readiness_manifest=args.readiness_manifest,
            build_evidence_report=args.build_evidence_report,
            acceptance_summary=args.acceptance_summary,
            live_evidence_bundle=args.live_evidence_bundle,
            requested_bindings={
                'with_sdk': bool(args.with_sdk),
                'with_model': bool(args.with_model),
            },
            requested_profiles=list(args.profiles),
            installed_binaries=list(args.installed_binaries),
        )
    except ReleaseLedgerEvidenceError as exc:
        print(f'[FAIL] {exc}', file=sys.stderr)
        return 2
    service.write(payload)
    print(json.dumps({'ok': True, 'ledger': output_path.name, 'claim_boundary': payload['claim_boundary']}, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
