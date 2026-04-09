from pathlib import Path


def test_main_window_layout_no_direct_backend_binding() -> None:
    text = Path('spine_ultrasound_ui/views/main_window_layout.py').read_text(encoding='utf-8')
    assert 'w.backend.' not in text
    assert 'action_router.dispatch' in text
