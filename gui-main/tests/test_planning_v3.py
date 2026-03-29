from __future__ import annotations

from spine_ultrasound_ui.core.plan_service import PlanService
from spine_ultrasound_ui.models import ExperimentRecord, RuntimeConfig


def _experiment() -> ExperimentRecord:
    return ExperimentRecord(
        exp_id='EXP_2026_0101',
        created_at='2026-03-29 10:00:00',
        state='AUTO_READY',
        cobb_angle=0.0,
        pressure_target=1.5,
        save_dir='/tmp/demo',
    )


def test_execution_plan_is_distinct_from_preview_plan():
    service = PlanService()
    experiment = _experiment()
    config = RuntimeConfig()
    localization = service.run_localization(experiment, config)
    preview, _ = service.build_preview_plan(experiment, localization, config)
    execution = service.build_execution_plan(preview, config=config)
    assert execution.plan_kind == 'execution'
    assert execution.plan_id != preview.plan_id
    assert execution.validation_summary['score']['composite_score'] > 0


def test_rescan_patch_supports_window_hotspots():
    service = PlanService()
    experiment = _experiment()
    config = RuntimeConfig()
    localization = service.run_localization(experiment, config)
    preview, _ = service.build_preview_plan(experiment, localization, config)
    patch = service.build_rescan_patch_plan(
        base_plan=preview,
        low_quality_segments=[1],
        quality_target=0.9,
        hotspot_windows=[{'segment_id': 1, 'start_index': 1, 'end_index': 3}],
    )
    assert patch.plan_kind == 'rescan_patch'
    assert patch.segments[0].needs_resample is True
    assert len(patch.segments[0].waypoints) == 2
