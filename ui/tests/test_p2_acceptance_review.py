from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_p2_acceptance_review_doc_references_executable_audits() -> None:
    doc = _read('docs/P2_ACCEPTANCE_REVIEW.md')
    assert 'scripts/check_p2_acceptance.py' in doc
    assert 'scripts/check_canonical_imports.py' in doc
    assert 'scripts/check_repository_gates.py' in doc


def test_p2_acceptance_script_checks_core_deliverables() -> None:
    script = _read('scripts/check_p2_acceptance.py')
    assert 'postprocess_stage_manifest.json' in script
    assert 'session_intelligence_manifest.json' in script
    assert 'canonical-import-gate' in script
    assert 'evidence-gate' in script
