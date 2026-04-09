from __future__ import annotations

import os
import tempfile
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _acceptance_output_root() -> Path:
    configured = os.environ.get('P2_ACCEPTANCE_OUTPUT_ROOT', '').strip()
    if configured:
        return Path(configured).expanduser().resolve()
    return Path(tempfile.gettempdir()) / 'spine_p2_acceptance_static'


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
    required_paths = [
        REPO_ROOT / 'docs/P2_ACCEPTANCE_CHECKLIST.md',
        REPO_ROOT / 'docs/CANONICAL_MODULE_REGISTRY.md',
        REPO_ROOT / 'docs/REPOSITORY_GATES.md',
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
    _assert_contains(REPO_ROOT / 'docs/P2_ACCEPTANCE_CHECKLIST.md', 'P2-1')
    _assert_contains(REPO_ROOT / 'docs/P2_ACCEPTANCE_CHECKLIST.md', 'P2-2')
    _assert_contains(REPO_ROOT / 'docs/P2_ACCEPTANCE_CHECKLIST.md', 'P2-3')
    _assert_contains(REPO_ROOT / '.github/workflows/mainline.yml', 'canonical-import-gate')
    _assert_contains(REPO_ROOT / '.github/workflows/mainline.yml', 'evidence-gate')
    print('P2 acceptance audit passed')


if __name__ == '__main__':
    main()
