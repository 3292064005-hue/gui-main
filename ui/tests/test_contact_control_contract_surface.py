from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile


def test_runtime_config_roundtrip_preserves_nested_contact_control():
    cfg = RuntimeConfig()
    cfg.contact_control.virtual_mass = 1.1
    cfg.force_estimator.preferred_source = "pressure"
    cfg.orientation_trim.lowpass_hz = 6.0
    rebuilt = RuntimeConfig.from_dict(cfg.to_dict())
    assert rebuilt.contact_control.virtual_mass == 1.1
    assert rebuilt.force_estimator.preferred_source == "pressure"
    assert rebuilt.orientation_trim.lowpass_hz == 6.0
    assert rebuilt.seek_contact_max_step_mm == rebuilt.contact_control.max_normal_step_mm


def test_clinical_defaults_emit_nested_contracts():
    service = ClinicalConfigService()
    cfg = service.apply_mainline_defaults(RuntimeConfig())
    assert cfg.contact_control.mode == "normal_axis_admittance"
    assert cfg.force_estimator.preferred_source == "fused"
    assert cfg.orientation_trim.max_trim_deg > 0.0


def test_xmate_profile_rt_contract_contains_nested_contact_control():
    profile = load_xmate_profile()
    rt_contract = profile.build_rt_phase_contract()
    assert "contact_control" in rt_contract["seek_contact"]
    assert "force_estimator" in rt_contract["seek_contact"]
    assert "orientation_trim" in rt_contract["scan_follow"]
