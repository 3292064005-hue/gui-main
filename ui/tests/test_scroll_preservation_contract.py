from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_common_text_edit_helpers_exist() -> None:
    source = _read("spine_ultrasound_ui/views/status_presenters/common.py")

    assert "def set_text_edit_plain_preserve_scroll" in source
    assert "def set_text_edit_html_preserve_scroll" in source
    assert 'cache_key = f"_presenter_last_{mode}"' in source
    assert "vertical = editor.verticalScrollBar()" in source
    assert "horizontal = editor.horizontalScrollBar()" in source
    assert "vertical.setValue(min(old_v, vertical.maximum()))" in source


def test_state_timeline_no_longer_forces_scroll_to_active_item() -> None:
    source = _read("spine_ultrasound_ui/widgets/state_timeline.py")

    assert "self._current_state = \"\"" in source
    assert "if state == self._current_state:" in source
    assert "scrollToItem" not in source


def test_presenters_use_scroll_preserving_text_updates() -> None:
    expected = {
        "spine_ultrasound_ui/views/status_presenters/overview_presenter.py": "set_text_edit_html_preserve_scroll",
        "spine_ultrasound_ui/views/status_presenters/prepare_presenter.py": "set_text_edit_plain_preserve_scroll",
        "spine_ultrasound_ui/views/status_presenters/replay_presenter.py": "set_text_edit_plain_preserve_scroll",
        "spine_ultrasound_ui/views/status_presenters/execution_presenter.py": "set_text_edit_plain_preserve_scroll",
        "spine_ultrasound_ui/views/status_presenters/monitor_presenter.py": "set_text_edit_plain_preserve_scroll",
    }

    for relative_path, marker in expected.items():
        assert marker in _read(relative_path), relative_path


def test_settings_page_preserves_scroll_positions_for_runtime_note() -> None:
    source = _read("spine_ultrasound_ui/pages/settings_page.py")

    assert "self.page_scroll = scroll" in source
    assert 'self.note_view.property("_last_sdk_note") != sdk_note' in source
    assert 'self.note_view.setProperty("_last_sdk_note", sdk_note)' in source
    assert "page_vertical.setValue(min(old_page_v, page_vertical.maximum()))" in source
    assert "note_vertical.setValue(min(old_note_v, note_vertical.maximum()))" in source
