from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'cpp_robot_core' / 'src' / 'core_runtime_command_helpers.h'
COMMAND_SOURCES = [
    ROOT / 'cpp_robot_core' / 'src' / 'core_runtime_session_commands.cpp',
    ROOT / 'cpp_robot_core' / 'src' / 'core_runtime_execution_commands.cpp',
    ROOT / 'cpp_robot_core' / 'src' / 'core_runtime_authority.cpp',
]


def test_authority_token_and_claim_helpers_are_centralized() -> None:
    helper_text = HELPER.read_text(encoding='utf-8')
    source_text = '\n'.join(path.read_text(encoding='utf-8') for path in COMMAND_SOURCES)
    assert 'normalizeAuthorityToken' in helper_text
    assert 'joinClaims' in helper_text
    assert 'Pure helper' in helper_text
    assert 'std::string normalizeAuthorityToken' not in source_text
    assert source_text.count('normalizeAuthorityToken(') >= 5
    assert source_text.count('joinClaims(') >= 1
