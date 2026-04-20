from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'docs' / '05_verification' / 'VERIFICATION_POLICY.md'
README = ROOT / 'README.md'
GATES = ROOT / 'docs' / '07_repo_governance' / 'REPOSITORY_GOVERNANCE.md'


def main() -> int:
    failures: list[str] = []
    if not DOC.exists():
        failures.append('missing docs/05_verification/VERIFICATION_POLICY.md')
    else:
        doc_text = DOC.read_text(encoding='utf-8')
        required_doc_terms = [
            'Repository proof',
            'Profile gate proof',
            'Live-controller proof',
            '已静态确认',
            '已沙箱验证',
            '未真实环境验证',
        ]
        for term in required_doc_terms:
            if term not in doc_text:
                failures.append(f'verification policy missing term: {term}')
    if README.exists():
        readme_text = README.read_text(encoding='utf-8')
        if 'docs/05_verification/VERIFICATION_POLICY.md' not in readme_text and 'docs/00_START_HERE.md' not in readme_text:
            failures.append('README missing verification-policy or start-here reference')
    else:
        failures.append('missing README.md')
    if GATES.exists():
        gates_text = GATES.read_text(encoding='utf-8')
        if 'docs/05_verification/VERIFICATION_POLICY.md' not in gates_text:
            failures.append('repository governance doc missing verification-policy reference')
    else:
        failures.append('missing docs/07_repo_governance/REPOSITORY_GOVERNANCE.md')
    if failures:
        for item in failures:
            print(f'[FAIL] {item}')
        return 1
    print('[PASS] verification policy present and referenced canonically')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
