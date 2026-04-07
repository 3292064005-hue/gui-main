from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.xmate_profile import load_xmate_profile
from spine_ultrasound_ui.utils.sdk_unit_contract import build_sdk_boundary_contract


def test_sdk_boundary_contract_normalizes_ui_mm_to_sdk_m() -> None:
    contract = build_sdk_boundary_contract(
        fc_frame_matrix=[1.0, 0.0, 0.0, 0.0,
                         0.0, 1.0, 0.0, 0.0,
                         0.0, 0.0, 1.0, 0.0,
                         0.0, 0.0, 0.0, 1.0],
        tcp_frame_matrix=[1.0, 0.0, 0.0, 0.0,
                          0.0, 1.0, 0.0, 0.0,
                          0.0, 0.0, 1.0, 62.0,
                          0.0, 0.0, 0.0, 1.0],
        load_com_mm=[0.0, 0.0, 62.0],
    )
    assert contract["ui_length_unit"] == "mm"
    assert contract["sdk_length_unit"] == "m"
    assert contract["tcp_frame_matrix_m"][11] == 0.062
    assert contract["load_com_m"][2] == 0.062


def test_profile_export_contains_sdk_boundary_fields() -> None:
    profile = load_xmate_profile()
    payload = profile.to_dict()
    assert payload["sdk_boundary_units"]["tcp_frame_matrix_m"][11] == 0.062
    assert payload["load_com_m"][2] == 0.062


def test_clinical_report_exposes_boundary_units() -> None:
    config = RuntimeConfig()
    report = ClinicalConfigService().build_report(config)
    assert report["baseline_summary"]["sdk_boundary_units"]["sdk_length_unit"] == "m"
