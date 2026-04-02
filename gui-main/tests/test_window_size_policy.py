from __future__ import annotations

from spine_ultrasound_ui.views.main_window_runtime_bridge import _clamp_window_position, _clamp_window_size


def test_clamp_window_size_limits_to_available_screen(monkeypatch) -> None:
    class _Geometry:
        def x(self) -> int:
            return 0

        def y(self) -> int:
            return 0

        def width(self) -> int:
            return 1366

        def height(self) -> int:
            return 768

    class _Screen:
        def availableGeometry(self) -> _Geometry:
            return _Geometry()

    monkeypatch.setattr(
        "spine_ultrasound_ui.views.main_window_runtime_bridge.QApplication.primaryScreen",
        lambda: _Screen(),
        raising=False,
    )

    width, height = _clamp_window_size(1720, 1020)

    assert width == 1342
    assert height == 744


def test_clamp_window_position_moves_window_back_into_visible_area(monkeypatch) -> None:
    class _Geometry:
        def x(self) -> int:
            return 0

        def y(self) -> int:
            return 0

        def width(self) -> int:
            return 1366

        def height(self) -> int:
            return 768

    class _Screen:
        def availableGeometry(self) -> _Geometry:
            return _Geometry()

    monkeypatch.setattr(
        "spine_ultrasound_ui.views.main_window_runtime_bridge.QApplication.primaryScreen",
        lambda: _Screen(),
        raising=False,
    )

    pos_x, pos_y = _clamp_window_position(1200, 900, 1342, 744)

    assert pos_x == 12
    assert pos_y == 12
