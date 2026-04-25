from __future__ import annotations

from types import SimpleNamespace

from spine_ultrasound_ui.views.main_window_action_router import MainWindowActionRouter, invoke_backend_action, report_action_failure


class _FakeStatusBar:
    def __init__(self) -> None:
        self.messages: list[tuple[str, int]] = []

    def showMessage(self, message: str, timeout: int) -> None:
        self.messages.append((message, timeout))


class _FakeRuntimeBridge:
    def __init__(self) -> None:
        self.logs: list[tuple[str, str]] = []

    def append_log(self, level: str, message: str) -> None:
        self.logs.append((level, message))


class _WindowHarness:
    def __init__(self) -> None:
        self.called: list[str] = []
        self.unsupported: list[str] = []

    def _action_start_procedure(self) -> None:
        self.called.append('start_procedure')

    def _report_unsupported_window_action(self, action_name: str) -> None:
        self.unsupported.append(action_name)


class _BackendHarness:
    def __init__(self, callback=None) -> None:
        self.runtime_bridge = _FakeRuntimeBridge()
        self._status_bar = _FakeStatusBar()
        self.backend = SimpleNamespace()
        if callback is not None:
            setattr(self.backend, 'start_procedure', callback)

    def statusBar(self) -> _FakeStatusBar:
        return self._status_bar


def test_action_router_dispatches_semantic_window_action() -> None:
    window = _WindowHarness()
    router = MainWindowActionRouter(window)
    router.dispatch('start_procedure')()
    assert window.called == ['start_procedure']


def test_action_router_reports_unsupported_action_without_crashing() -> None:
    window = _WindowHarness()
    router = MainWindowActionRouter(window)
    router.dispatch('unknown_action')()
    assert window.unsupported == ['unknown_action']


def test_invoke_backend_action_reports_missing_backend_action() -> None:
    window = _BackendHarness()
    result = invoke_backend_action(window, 'start_procedure')
    assert result is False
    assert window.runtime_bridge.logs and window.runtime_bridge.logs[-1][0] == 'ERROR'
    assert 'backend action not available' in window.runtime_bridge.logs[-1][1]
    assert window.statusBar().messages and '动作 start_procedure 失败' in window.statusBar().messages[-1][0]


def test_invoke_backend_action_reports_runtime_failure_without_raising() -> None:
    def _boom() -> None:
        raise RuntimeError('transport timeout during start_procedure')

    window = _BackendHarness(callback=_boom)
    result = invoke_backend_action(window, 'start_procedure')
    assert result is False
    level, message = window.runtime_bridge.logs[-1]
    assert level == 'ERROR'
    assert 'transport timeout during start_procedure' in message


def test_report_action_failure_emits_log_and_status() -> None:
    window = _BackendHarness()
    report_action_failure(window, 'export_summary', RuntimeError('authority conflict'))
    assert window.runtime_bridge.logs[-1][0] == 'ERROR'
    assert 'authority conflict' in window.runtime_bridge.logs[-1][1]
    assert window.statusBar().messages[-1][1] == 5000
