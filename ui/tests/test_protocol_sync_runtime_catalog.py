from __future__ import annotations

import subprocess
import sys


def test_protocol_sync_script_passes_for_runtime_command_catalog() -> None:
    result = subprocess.run(
        [sys.executable, 'scripts/check_protocol_sync.py'],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr



def test_authoritative_runtime_envelope_command_is_in_catalog() -> None:
    from spine_ultrasound_ui.services.runtime_command_catalog import COMMAND_SPECS, is_write_command

    assert 'get_authoritative_runtime_envelope' in COMMAND_SPECS
    assert is_write_command('get_authoritative_runtime_envelope') is False
