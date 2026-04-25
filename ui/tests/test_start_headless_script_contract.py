from pathlib import Path


def test_start_headless_parses_runtime_policy_mode_field() -> None:
    source = Path('scripts/start_headless.sh').read_text(encoding='utf-8')
    assert '.get("mode", "core")' in source
    assert 'resolved_mode' not in source
