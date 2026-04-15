from __future__ import annotations

from spine_ultrasound_ui.services.runtime_command_catalog import (
    canonical_command_name,
    command_deprecation_metadata,
    is_deprecated_alias,
)


def test_compile_scan_plan_deprecation_metadata_is_manifest_backed() -> None:
    assert canonical_command_name('compile_scan_plan') == 'validate_scan_plan'
    assert is_deprecated_alias('compile_scan_plan') is True
    metadata = command_deprecation_metadata('compile_scan_plan')
    assert metadata['deprecation_stage'] == 'warn_only'
    assert metadata['removal_target'] == '2026-Q4'
    assert metadata['replacement_command'] == 'validate_scan_plan'
    assert 'new code must call validate_scan_plan' in metadata['compatibility_note']
