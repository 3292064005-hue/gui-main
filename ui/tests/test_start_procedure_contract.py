from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_start_procedure_is_canonical_and_start_scan_is_retired() -> None:
    manifest = json.loads((ROOT / 'schemas' / 'runtime_command_manifest.json').read_text(encoding='utf-8'))
    commands = {item['name']: item for item in manifest['commands']}
    compat = json.loads((ROOT / 'schemas' / 'runtime_command_compat_manifest.json').read_text(encoding='utf-8'))
    retired = {item['name']: item for item in compat['retired_aliases']}
    assert commands['start_procedure']['canonical_command'] == 'start_procedure'
    assert 'start_scan' not in commands
    assert retired['start_scan']['replacement_command'] == 'start_procedure'
    assert retired['start_scan']['deprecation_stage'] == 'retired'


def test_workflow_uses_start_procedure_payload() -> None:
    source = (ROOT / 'spine_ultrasound_ui' / 'core' / 'app_workflow_operations.py').read_text(encoding='utf-8')
    assert '_run_scan_start_step("start_procedure", {"procedure": "scan"})' in source
