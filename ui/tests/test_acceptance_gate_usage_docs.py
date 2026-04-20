from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding='utf-8')


def test_acceptance_tracker_documents_fail_closed_p2_usage() -> None:
    doc = _read('docs/05_verification/ACCEPTANCE_TRACKER.md')
    assert 'P2 acceptance gate usage' in doc
    assert 'P2_ACCEPTANCE_OUTPUT_ROOT' in doc
    assert 'P2_ACCEPTANCE_ALLOW_GENERATE=1' in doc
    assert 'fail-closed' in doc


def test_verification_policy_documents_audited_vs_self_generated_p2_runs() -> None:
    doc = _read('docs/05_verification/VERIFICATION_POLICY.md')
    assert 'P2 acceptance gate usage' in doc
    assert 'P2_ACCEPTANCE_OUTPUT_ROOT' in doc
    assert 'P2_ACCEPTANCE_ALLOW_GENERATE=1' in doc
    assert 'audited build proof' in doc
