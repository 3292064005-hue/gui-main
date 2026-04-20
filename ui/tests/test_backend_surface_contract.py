from spine_ultrasound_ui.services.backend_capability_matrix_service import BackendCapabilityMatrixService


def test_page_contract_hides_tabs_when_backend_is_hidden():
    matrix = BackendCapabilityMatrixService.build({
        'camera': 'hidden',
        'ultrasound': 'hidden',
        'reconstruction': 'monitor_only',
        'recording': 'hidden',
    })
    surface = BackendCapabilityMatrixService.page_contract(matrix)
    assert surface['vision']['visible'] is False
    assert surface['reconstruction']['visible'] is True
    assert surface['reconstruction']['monitor_only'] is True
