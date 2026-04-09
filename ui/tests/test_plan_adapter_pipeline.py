from __future__ import annotations

from spine_ultrasound_ui.core.plan_service import PlanService
def _device_roster() -> dict:
    return {
        "robot": {"online": True, "fresh": True, "fact_source": "test"},
        "camera": {"online": True, "fresh": True, "fact_source": "test"},
        "ultrasound": {"online": True, "fresh": True, "fact_source": "test"},
        "pressure": {"online": True, "fresh": True, "fact_source": "test"},
    }


from spine_ultrasound_ui.models import ExperimentRecord, RuntimeConfig


def _experiment() -> ExperimentRecord:
    return ExperimentRecord(
        exp_id='EXP_PIPELINE_0001',
        created_at='2026-04-08 10:00:00',
        state='AUTO_READY',
        cobb_angle=0.0,
        pressure_target=1.5,
        save_dir='/tmp/demo',
    )


def test_preview_plan_records_adapter_pipeline() -> None:
    service = PlanService()
    config = RuntimeConfig()
    localization = service.run_localization(_experiment(), config, device_roster=_device_roster())
    plan, _status = service.build_preview_plan(_experiment(), localization, config)
    pipeline = dict(plan.validation_summary.get('adapter_pipeline', {}))
    assert pipeline.get('stage') == 'preview'
    assert pipeline.get('plan_hash') == pipeline.get('canonical_plan_hash')
    assert pipeline.get('template_hash') == pipeline.get('canonical_template_hash')
    assert pipeline.get('plan_hash')
    assert pipeline.get('template_hash')
    assert 'resolve_frames' in pipeline.get('applied_adapters', [])
    assert 'plan_digest' in pipeline.get('applied_adapters', [])


def test_execution_plan_populates_safety_contact_band_and_adapter_pipeline() -> None:
    service = PlanService()
    config = RuntimeConfig()
    localization = service.run_localization(_experiment(), config, device_roster=_device_roster())
    preview, _ = service.build_preview_plan(_experiment(), localization, config)
    execution = service.build_execution_plan(preview, config=config)
    pipeline = dict(execution.validation_summary.get('adapter_pipeline', {}))
    assert pipeline.get('stage') == 'execution'
    assert execution.execution_constraints.allowed_contact_band['upper_n'] > execution.execution_constraints.allowed_contact_band['lower_n']
    for segment in execution.segments:
        assert segment.contact_band['upper_n'] > segment.contact_band['lower_n']


def test_adapter_pipeline_digest_is_idempotent() -> None:
    service = PlanService()
    config = RuntimeConfig()
    localization = service.run_localization(_experiment(), config, device_roster=_device_roster())
    preview, _ = service.build_preview_plan(_experiment(), localization, config)
    first_pipeline = dict(preview.validation_summary.get('adapter_pipeline', {}))
    context = service.plan_strategy.graph.context_for(localization=localization, config=config)
    from spine_ultrasound_ui.services.planning.request_adapters import ScanPlanAdapterContext
    rerun = service.plan_strategy.graph.preview_pipeline.apply(
        preview,
        ScanPlanAdapterContext(
            stage='preview',
            config=config,
            localization=localization,
            planner_context={'surface_model': context.surface_model, 'contact_model': context.contact_model},
        ),
    )
    second_pipeline = dict(rerun.validation_summary.get('adapter_pipeline', {}))
    assert second_pipeline.get('plan_hash') == first_pipeline.get('plan_hash')
    assert second_pipeline.get('template_hash') == first_pipeline.get('template_hash')
    assert second_pipeline.get('segment_hashes') == first_pipeline.get('segment_hashes')
