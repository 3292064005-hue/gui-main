from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.core.app_controller import AppController
from spine_ultrasound_ui.services.mock_backend import MockBackend
from spine_ultrasound_ui.views.status_presenters.common import build_status_context
from spine_ultrasound_ui.views.status_presenters.overview_presenter import OverviewPresenter


class _FakeStyle:
    def unpolish(self, widget) -> None:
        return None

    def polish(self, widget) -> None:
        return None


class _FakeLabel:
    def __init__(self) -> None:
        self._text = ""
        self._props: dict[str, object] = {}

    def setText(self, text: str) -> None:
        self._text = str(text)

    def text(self) -> str:
        return self._text

    def setProperty(self, name: str, value: object) -> None:
        self._props[name] = value

    def style(self) -> _FakeStyle:
        return _FakeStyle()

    def update(self) -> None:
        return None


class _FakeTextEdit:
    def __init__(self) -> None:
        self.html = ""

    def setHtml(self, text: str) -> None:
        self.html = text


class _FakeCard:
    def __init__(self) -> None:
        self.title = ""
        self.detail = ""
        self.tone = ""

    def update_text(self, title: str, detail: str) -> None:
        self.title = title
        self.detail = detail

    def set_tone(self, tone: str) -> None:
        self.tone = tone


class _FakeOverviewPage:
    def __init__(self) -> None:
        self.recommended_label = _FakeLabel()
        self.readiness_label = _FakeLabel()
        self.overview_text = _FakeTextEdit()


class _FakeWindow:
    def __init__(self) -> None:
        self.system_state_label = _FakeLabel()
        self.exp_id_label = _FakeLabel()
        self.readiness_label = _FakeLabel()
        self.header_state_pill = _FakeLabel()
        self.header_mode_pill = _FakeLabel()
        self.header_exp_pill = _FakeLabel()
        self.header_step_pill = _FakeLabel()
        self.card_state = _FakeCard()
        self.card_exp = _FakeCard()
        self.card_readiness = _FakeCard()
        self.card_pressure = _FakeCard()
        self.card_pose = _FakeCard()
        self.card_quality = _FakeCard()
        self.card_result = _FakeCard()
        self.overview_page = _FakeOverviewPage()

    def _set_badge_state(self, widget: _FakeLabel, text: str, state: str) -> None:
        widget.setText(text)
        widget.setProperty("state", state)
        widget.style().unpolish(widget)
        widget.style().polish(widget)
        widget.update()

    @staticmethod
    def _system_state_kind(state: str) -> str:
        state_upper = str(state or "").upper()
        if any(token in state_upper for token in ["FAULT", "ESTOP", "ALARM", "ERROR"]):
            return "danger"
        if any(token in state_upper for token in ["PAUSED", "SEEKING", "RETREAT", "BOOT", "DISCONNECTED"]):
            return "warn"
        return "ok"

    @staticmethod
    def _readiness_state(percent: int) -> str:
        if percent >= 100:
            return "ok"
        if percent >= 50:
            return "warn"
        return "danger"


def test_overview_presenter_accepts_windows_without_legacy_summary_labels(tmp_path) -> None:
    backend = MockBackend(Path(tmp_path))
    controller = AppController(Path(tmp_path), backend)
    window = _FakeWindow()

    payload = controller.control_plane_reader.build_status_payload(
        telemetry=controller.telemetry,
        config=controller.config,
        workflow_artifacts=controller.workflow_artifacts,
        current_experiment=controller.session_service.current_experiment,
    )
    ctx = build_status_context(window, payload)

    OverviewPresenter().apply(ctx)

    assert window.header_step_pill.text().startswith("下一步 · ")
    assert window.overview_page.recommended_label.text().startswith("建议下一步：")
    assert "流程就绪度" in window.overview_page.readiness_label.text()
    assert window.overview_page.overview_text.html
