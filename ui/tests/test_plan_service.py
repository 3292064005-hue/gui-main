from spine_ultrasound_ui.core.plan_service import DeterministicPlanStrategy, PlanService
def _device_roster() -> dict:
    return {
        "robot": {"online": True, "fresh": True, "fact_source": "test"},
        "camera": {"online": True, "fresh": True, "fact_source": "test"},
        "ultrasound": {"online": True, "fresh": True, "fact_source": "test"},
        "pressure": {"online": True, "fresh": True, "fact_source": "test"},
    }


from spine_ultrasound_ui.models import ExperimentRecord, RuntimeConfig


def test_plan_service_generates_preview_hash_without_session_binding():
    service = PlanService()
    experiment = ExperimentRecord(
        exp_id="EXP_2026_0001",
        created_at="2026-03-26 10:00:00",
        state="AUTO_READY",
        cobb_angle=0.0,
        pressure_target=1.5,
        save_dir="/tmp/demo",
    )
    localization = service.run_localization(experiment, RuntimeConfig(), device_roster=_device_roster())
    plan, status = service.build_preview_plan(experiment, localization, RuntimeConfig())
    assert status.ready is True
    assert plan.session_id == ""
    assert plan.template_hash()


def test_plan_validator_rejects_empty_plan():
    strategy = DeterministicPlanStrategy()
    experiment = ExperimentRecord(
        exp_id="EXP_2026_0002",
        created_at="2026-03-26 10:00:00",
        state="AUTO_READY",
        cobb_angle=0.0,
        pressure_target=1.5,
        save_dir="/tmp/demo",
    )
    localization = service = PlanService().run_localization(experiment, RuntimeConfig(), device_roster=_device_roster())
    plan, _ = PlanService().build_preview_plan(experiment, localization, RuntimeConfig(segment_length_mm=1.0, sample_step_mm=1.0))
    plan.segments = []
    try:
        strategy.validate(plan)
    except ValueError as exc:
        assert "at least one segment" in str(exc)
    else:
        raise AssertionError("empty plan should be rejected")


def test_execution_plan_requires_canonical_localization():
    service = PlanService()
    experiment = ExperimentRecord(
        exp_id="EXP_2026_0003",
        created_at="2026-03-26 10:00:00",
        state="AUTO_READY",
        cobb_angle=0.0,
        pressure_target=1.5,
        save_dir="/tmp/demo",
    )
    localization = service.run_localization(experiment, RuntimeConfig(), device_roster=_device_roster())
    preview, _ = service.build_preview_plan(experiment, localization, RuntimeConfig())
    service._last_localization = None
    try:
        service.build_execution_plan(preview, config=RuntimeConfig())
    except RuntimeError as exc:
        assert 'canonical localization' in str(exc)
    else:
        raise AssertionError('execution plan should require canonical localization and reject synthetic fallback')
