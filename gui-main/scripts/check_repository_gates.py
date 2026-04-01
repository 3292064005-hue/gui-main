from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_CODEOWNERS_ENTRIES = [
    '/cpp_robot_core/',
    '/spine_ultrasound_ui/services/',
    '/scripts/',
    '/docs/',
    '/.github/CODEOWNERS',
]
REQUIRED_WORKFLOW_JOBS = [
    'hygiene',
    'mainline-verification',
    'canonical-import-gate',
    'protocol-sync-gate',
    'runtime-core-gate',
    'evidence-gate',
    'mock-e2e',
]


def main() -> int:
    failures: list[str] = []
    codeowners = ROOT / '.github' / 'CODEOWNERS'
    workflow = ROOT / '.github' / 'workflows' / 'mainline.yml'
    if not codeowners.exists():
        failures.append('missing .github/CODEOWNERS')
    else:
        text = codeowners.read_text(encoding='utf-8')
        for entry in REQUIRED_CODEOWNERS_ENTRIES:
            if entry not in text:
                failures.append(f'CODEOWNERS missing entry: {entry}')
    if not workflow.exists():
        failures.append('missing .github/workflows/mainline.yml')
    else:
        text = workflow.read_text(encoding='utf-8')
        for job in REQUIRED_WORKFLOW_JOBS:
            if f'  {job}:' not in text:
                failures.append(f'workflow missing required job: {job}')
    if failures:
        for item in failures:
            print(f'[FAIL] {item}')
        return 1
    print('[PASS] repository gates present')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
