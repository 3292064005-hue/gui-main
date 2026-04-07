from __future__ import annotations

from pathlib import Path


def _assert_exists(path: str) -> None:
    target = Path(path)
    if not target.exists():
        raise SystemExit(f"missing P2 acceptance artifact: {path}")


def _assert_contains(path: str, needle: str) -> None:
    content = Path(path).read_text(encoding="utf-8")
    if needle not in content:
        raise SystemExit(f"{path} missing required marker: {needle}")


def main() -> None:
    required_paths = [
        'docs/P2_ACCEPTANCE_CHECKLIST.md',
        'docs/CANONICAL_MODULE_REGISTRY.md',
        'docs/REPOSITORY_GATES.md',
        'scripts/generate_p2_acceptance_artifacts.py',
        'derived/postprocess/postprocess_stage_manifest.json',
        'derived/session/session_intelligence_manifest.json',
        'schemas/session/postprocess_stage_manifest_v1.schema.json',
        'schemas/session/session_intelligence_manifest_v1.schema.json',
        '.github/CODEOWNERS',
        '.github/workflows/mainline.yml',
        'scripts/check_canonical_imports.py',
        'scripts/check_repository_gates.py',
    ]
    for item in required_paths:
        _assert_exists(item)
    _assert_contains('docs/P2_ACCEPTANCE_CHECKLIST.md', 'P2-1')
    _assert_contains('docs/P2_ACCEPTANCE_CHECKLIST.md', 'P2-2')
    _assert_contains('docs/P2_ACCEPTANCE_CHECKLIST.md', 'P2-3')
    _assert_contains('.github/workflows/mainline.yml', 'canonical-import-gate')
    _assert_contains('.github/workflows/mainline.yml', 'evidence-gate')
    print('P2 acceptance audit passed')


if __name__ == '__main__':
    main()
