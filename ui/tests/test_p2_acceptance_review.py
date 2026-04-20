from pathlib import Path


def _read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_acceptance_tracker_references_executable_audits() -> None:
    doc = _read('docs/05_verification/ACCEPTANCE_TRACKER.md')
    assert 'docs/05_verification/CURRENT_KNOWN_GAPS.md' in doc
    assert 'docs/05_verification/HIL_AND_BUILD_EVIDENCE.md' in doc


def test_p2_acceptance_script_checks_core_deliverables() -> None:
    script = _read('scripts/check_p2_acceptance.py')
    assert 'postprocess_stage_manifest.json' in script
    assert 'session_intelligence_manifest.json' in script
    assert 'canonical-import-gate' in script
    assert 'evidence-gate' in script



def test_p2_acceptance_script_is_fail_closed_and_avoids_global_tmp_root() -> None:
    script = _read('scripts/check_p2_acceptance.py')
    assert '/tmp/spine_p2_acceptance_static' not in script
    assert 'missing P2 acceptance artifacts in configured output root' in script
    assert 'P2_ACCEPTANCE_OUTPUT_ROOT' in script
    assert 'P2_ACCEPTANCE_ALLOW_GENERATE=1' in script
