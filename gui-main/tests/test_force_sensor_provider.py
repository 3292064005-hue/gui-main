from spine_ultrasound_ui.services.pressure_sensor_service import (
    MockForceSensorProvider,
    UnavailableForceSensorProvider,
)


def test_mock_force_sensor_provider_emits_six_axis_sample():
    provider = MockForceSensorProvider()
    sample = provider.read_sample(contact_active=True, desired_force_n=10.0)
    assert sample.status == "ok"
    assert sample.source == "mock_force_sensor"
    assert len(sample.wrench_n) == 6
    assert sample.ts_ns > 0


def test_unavailable_force_sensor_provider_marks_sample_unavailable():
    provider = UnavailableForceSensorProvider()
    sample = provider.read_sample(contact_active=True, desired_force_n=10.0)
    assert sample.status == "unavailable"
    assert sample.source == "unavailable_force_sensor"
    assert sample.wrench_n == [0.0] * 6
