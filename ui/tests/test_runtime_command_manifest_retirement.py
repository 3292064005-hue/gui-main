from __future__ import annotations

from spine_ultrasound_ui.services.runtime_command_catalog import (
    active_command_names,
    canonical_aliases,
    canonical_command_name,
    command_alias_kind,
    is_retired_command_alias,
    retired_alias_rejection,
    retired_alias_spec,
    retired_aliases_for,
    is_write_command,
)


def test_compile_scan_plan_is_retired_outside_active_manifest() -> None:
    assert 'compile_scan_plan' not in active_command_names()
    assert canonical_command_name('compile_scan_plan') == 'compile_scan_plan'
    assert command_alias_kind('compile_scan_plan') == ''
    assert is_retired_command_alias('compile_scan_plan') is True
    metadata = retired_alias_spec('compile_scan_plan')
    assert metadata['deprecation_stage'] == 'retired'
    assert metadata['replacement_command'] == 'validate_scan_plan'
    assert retired_alias_rejection('compile_scan_plan') == 'retired command alias: compile_scan_plan; use validate_scan_plan'


def test_start_scan_is_retired_outside_active_manifest() -> None:
    assert 'start_scan' not in active_command_names()
    assert canonical_command_name('start_scan') == 'start_scan'
    assert command_alias_kind('start_scan') == ''
    assert is_retired_command_alias('start_scan') is True
    metadata = retired_alias_spec('start_scan')
    assert metadata['deprecation_stage'] == 'retired'
    assert metadata['replacement_command'] == 'start_procedure'
    assert retired_alias_rejection('start_scan') == 'retired command alias: start_scan; use start_procedure'


def test_retired_aliases_do_not_reenter_active_alias_lists() -> None:
    assert canonical_aliases('validate_scan_plan') == ()
    assert canonical_aliases('start_procedure') == ()
    assert retired_aliases_for('validate_scan_plan') == ('compile_scan_plan',)
    assert retired_aliases_for('start_procedure') == ('start_scan',)


def test_retired_alias_write_classification_uses_compat_manifest() -> None:
    assert is_write_command('compile_scan_plan') is False
    assert is_write_command('start_scan') is True
