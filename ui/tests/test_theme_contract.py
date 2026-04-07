from __future__ import annotations

import re

from spine_ultrasound_ui.styles import MAIN_STYLESHEET
from spine_ultrasound_ui.views.status_presenters.common import html_summary


def _block(selector: str) -> str:
    pattern = rf"{re.escape(selector)}\s*\{{(.*?)\}}"
    match = re.search(pattern, MAIN_STYLESHEET, re.DOTALL)
    assert match is not None, f"missing selector: {selector}"
    return match.group(1)


def test_theme_keeps_key_selectors() -> None:
    for selector in [
        'QLabel#StatusPill',
        'QLabel#AlarmBanner',
        'QPushButton[kind="primary"]',
        "QProgressBar::chunk",
        "#ImageViewport",
    ]:
        assert selector in MAIN_STYLESHEET


def test_theme_uses_neutral_success_and_warning_buttons() -> None:
    expected_lines = [
        "background: #F5F6F7;",
        "border-color: #C9CFD6;",
        "color: #1F2937;",
    ]
    for selector in ['QPushButton[kind="success"]', 'QPushButton[kind="warning"]']:
        block = _block(selector)
        for line in expected_lines:
            assert line in block


def test_theme_removes_legacy_bright_action_colors() -> None:
    for legacy_color in ["#1D4ED8", "#2563EB", "#0F766E", "#14B8A6", "#9A3412", "#EA580C"]:
        assert legacy_color not in MAIN_STYLESHEET


def test_html_summary_uses_light_theme_contrast_colors() -> None:
    html = html_summary([("键", "值")])
    assert "#6B7280" in html
    assert "#111827" in html
    assert "#F8FAFC" not in html
