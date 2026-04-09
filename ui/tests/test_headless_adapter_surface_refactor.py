from pathlib import Path


def test_headless_adapter_surface_delegates_to_split_services() -> None:
    text = Path('spine_ultrasound_ui/services/headless_adapter_surface.py').read_text(encoding='utf-8')
    assert 'HeadlessControlPlaneStatusService' in text
    assert 'HeadlessEventSurfaceService' in text
    assert 'HeadlessFrameSurfaceService' in text
