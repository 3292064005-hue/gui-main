from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.config_service import ConfigService


def test_config_service_roundtrip(tmp_path):
    path = tmp_path / "runtime.json"
    config = RuntimeConfig(scan_speed_mm_s=12.0, telemetry_rate_hz=30)
    service = ConfigService()
    service.save(path, config)
    loaded = service.load(path)
    assert loaded.scan_speed_mm_s == 12.0
    assert loaded.telemetry_rate_hz == 30
