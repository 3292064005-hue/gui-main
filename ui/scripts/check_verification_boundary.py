from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs' / 'VERIFICATION_BOUNDARY.md'
README = ROOT / 'README.md'
GATES = ROOT / 'docs' / 'REPOSITORY_GATES.md'


def main() -> int:
    failures: list[str] = []
    if not DOC.exists():
        failures.append('missing docs/VERIFICATION_BOUNDARY.md')
    else:
        doc_text = DOC.read_text(encoding='utf-8')
        required_doc_terms = [
            'Repository proof',
            'Profile gate proof',
            'Live-controller / HIL validation',
            'VERIFY_PHASE=python',
            'ROBOT_CORE_WITH_XCORE_SDK=OFF',
            '已静态确认',
            '已沙箱验证',
            '未真实环境验证',
        ]
        for term in required_doc_terms:
            if term not in doc_text:
                failures.append(f'verification boundary doc missing term: {term}')
    if README.exists():
        readme_text = README.read_text(encoding='utf-8')
        if 'docs/VERIFICATION_BOUNDARY.md' not in readme_text:
            failures.append('README missing verification-boundary reference')
    else:
        failures.append('missing README.md')
    if GATES.exists():
        gates_text = GATES.read_text(encoding='utf-8')
        if 'docs/VERIFICATION_BOUNDARY.md' not in gates_text:
            failures.append('docs/REPOSITORY_GATES.md missing verification-boundary reference')
    else:
        failures.append('missing docs/REPOSITORY_GATES.md')
    if failures:
        for item in failures:
            print(f'[FAIL] {item}')
        return 1
    print('[PASS] verification-boundary documentation present and referenced')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
