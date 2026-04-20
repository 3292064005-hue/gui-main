from __future__ import annotations

import os
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _acceptance_output_root() -> Path:
    configured = os.environ.get('P2_ACCEPTANCE_OUTPUT_ROOT', '').strip()
    if configured:
        return Path(configured).expanduser().resolve()
    default_root = (REPO_ROOT / '.artifacts' / 'p2_acceptance_static').resolve()
    return default_root


def _ensure_generated_acceptance_artifacts(output_root: Path) -> None:
    required = [
        output_root / 'derived/postprocess/postprocess_stage_manifest.json',
        output_root / 'derived/session/session_intelligence_manifest.json',
    ]
    if all(path.exists() for path in required):
        return
    if os.environ.get('P2_ACCEPTANCE_ALLOW_GENERATE', '').strip() not in {'1', 'true', 'TRUE'}:
        missing = ', '.join(str(path) for path in required if not path.exists())
        raise SystemExit(
            'missing P2 acceptance artifacts in configured output root '
            f'{output_root}; set P2_ACCEPTANCE_OUTPUT_ROOT to the audited build directory '
            'or set P2_ACCEPTANCE_ALLOW_GENERATE=1 for an explicit self-generated review run. '
            f'Missing: {missing}'
        )
    env = dict(os.environ)
    env['P2_ACCEPTANCE_OUTPUT_ROOT'] = str(output_root)
    subprocess.run(
        [os.environ.get('PYTHON_BIN', 'python3'), str(REPO_ROOT / 'scripts/generate_p2_acceptance_artifacts.py')],
        check=True,
        cwd=str(REPO_ROOT),
        env=env,
    )

def _assert_exists(path: Path) -> None:
    target = path
    if not target.exists():
        raise SystemExit(f"missing P2 acceptance artifact: {path}")


def _assert_contains(path: Path, needle: str) -> None:
    content = path.read_text(encoding="utf-8")
    if needle not in content:
        raise SystemExit(f"{path} missing required marker: {needle}")


def main() -> None:
    output_root = _acceptance_output_root()
    _ensure_generated_acceptance_artifacts(output_root)
    required_paths = [
        REPO_ROOT / 'docs/05_verification/ACCEPTANCE_TRACKER.md',
        REPO_ROOT / 'docs/07_repo_governance/CANONICAL_MODULES_AND_DEPENDENCIES.md',
        REPO_ROOT / 'docs/07_repo_governance/REPOSITORY_GOVERNANCE.md',
        REPO_ROOT / 'scripts/generate_p2_acceptance_artifacts.py',
        output_root / 'derived/postprocess/postprocess_stage_manifest.json',
        output_root / 'derived/session/session_intelligence_manifest.json',
        REPO_ROOT / 'schemas/session/postprocess_stage_manifest_v1.schema.json',
        REPO_ROOT / 'schemas/session/session_intelligence_manifest_v1.schema.json',
        REPO_ROOT / '.github/CODEOWNERS',
        REPO_ROOT / '.github/workflows/mainline.yml',
        REPO_ROOT / 'scripts/check_canonical_imports.py',
        REPO_ROOT / 'scripts/check_repository_gates.py',
    ]
    for item in required_paths:
        _assert_exists(item)
    _assert_contains(REPO_ROOT / 'docs/05_verification/ACCEPTANCE_TRACKER.md', 'P2-1')
    _assert_contains(REPO_ROOT / 'docs/05_verification/ACCEPTANCE_TRACKER.md', 'P2-2')
    _assert_contains(REPO_ROOT / 'docs/05_verification/ACCEPTANCE_TRACKER.md', 'P2-3')
    _assert_contains(REPO_ROOT / '.github/workflows/mainline.yml', 'canonical-import-gate')
    _assert_contains(REPO_ROOT / '.github/workflows/mainline.yml', 'evidence-gate')
    print('P2 acceptance audit passed')


if __name__ == '__main__':
    main()
