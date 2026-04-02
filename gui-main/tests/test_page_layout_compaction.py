from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_scan_page_assigns_extra_height_to_image_splitter() -> None:
    source = _read("spine_ultrasound_ui/pages/scan_page.py")

    assert 'layout.addWidget(imgs, 3)' in source
    assert "imgs.setStretchFactor(0, 1)" in source
    assert "imgs.setStretchFactor(1, 1)" in source
    assert "layout.addWidget(stat_box, 2)" in source


def test_reconstruction_page_assigns_extra_height_to_workspace() -> None:
    source = _read("spine_ultrasound_ui/pages/reconstruction_page.py")

    assert 'layout.addWidget(group, 1)' in source
    assert "grid.setColumnStretch(0, 1)" in source
    assert "grid.setColumnStretch(1, 1)" in source
    assert "grid.setRowStretch(0, 1)" in source
    assert "grid.setRowStretch(1, 1)" in source


def test_vision_page_prioritizes_image_panel() -> None:
    source = _read("spine_ultrasound_ui/pages/vision_page.py")

    assert "layout.addWidget(self.camera_pane, 3)" in source
    assert "layout.addLayout(grid, 2)" in source
    assert "grid.setColumnStretch(0, 1)" in source
    assert "grid.setColumnStretch(1, 1)" in source


def test_image_pane_keeps_original_pixmap_for_resizing() -> None:
    source = _read("spine_ultrasound_ui/widgets/image_pane.py")

    assert "from PySide6.QtCore import QSize, QTimer, Qt" in source
    assert "class _PixmapViewport(QWidget):" in source
    assert "def sizeHint(self) -> QSize:" in source
    assert "return QSize(720, 405)" in source
    assert "self.setMinimumSize(360, 220)" in source
    assert "self._source_pixmap: QPixmap | None = None" in source
    assert "self._resize_timer = QTimer(self)" in source
    assert "self._defer_render = True" in source
    assert 'self._resize_timer.timeout.connect(self._flush_deferred_refresh)' in source
    assert 'self.label = _PixmapViewport("等待图像流")' in source
    assert "layout.setContentsMargins(10, 16, 10, 10)" in source
    assert "layout.addWidget(self.label, 1)" in source
    assert "self._source_pixmap = pix" in source
    assert "if not self.isVisible():" in source
    assert "self._schedule_refresh()" in source
    assert "self._schedule_refresh(260)" in source
    assert "def hideEvent(self, event):" in source
    assert "self._resize_timer.start(delay_ms)" in source
    assert "if self._defer_render or self._timer_is_active():" in source
    assert "def _flush_deferred_refresh(self) -> None:" in source
    assert "self.label.set_display_pixmap(" in source
    assert "self._source_pixmap.scaled(target_size" in source
