from __future__ import annotations

from functools import partial

from spine_ultrasound_ui.services.backend_errors import normalize_backend_exception
from typing import Callable


class MainWindowActionRouter:
    """Route UI actions through a window-owned semantic surface.

    The router keeps widgets from binding directly to backend methods so UI code
    only depends on stable semantic actions owned by MainWindow.
    """

    def __init__(self, window) -> None:
        self.window = window

    def dispatch(self, action_name: str) -> Callable[[], None]:
        return partial(self._invoke, action_name)

    def _invoke(self, action_name: str) -> None:
        callback = getattr(self.window, f'_action_{action_name}', None)
        if callback is None:
            reporter = getattr(self.window, '_report_unsupported_window_action', None)
            if reporter is not None:
                reporter(action_name)
                return
            raise AttributeError(f'unsupported window action: {action_name}')
        callback()


def report_action_failure(window, action_name: str, exc: Exception) -> None:
    """Report a UI/backend action failure without crashing the desktop shell.

    Args:
        window: Host object exposing ``runtime_bridge`` and ``statusBar``.
        action_name: Semantic action name routed from the UI surface.
        exc: Failure raised while resolving or executing the action.

    Boundary behavior:
        - Normalizes the failure into the stable backend error taxonomy.
        - Emits a user-visible status-bar message and an ERROR log entry.
        - Never raises; action failures must not crash the UI event loop.
    """
    normalized = normalize_backend_exception(exc, command=action_name, context='desktop_action')
    message = f"动作 {action_name} 失败：{normalized.message}"
    window.runtime_bridge.append_log('ERROR', message)
    window.statusBar().showMessage(message, 5000)


def invoke_backend_action(window, action_name: str) -> bool:
    """Execute a backend action from the desktop semantic action surface.

    Args:
        window: Host object exposing ``backend``, ``runtime_bridge`` and ``statusBar``.
        action_name: Name of the backend method to execute.

    Returns:
        ``True`` when the backend action exists and completes successfully.
        ``False`` when the action is unavailable or raises at the UI boundary.

    Boundary behavior:
        Missing or failing backend actions are converted into typed log/status
        messages so the desktop shell remains interactive.
    """
    callback = getattr(window.backend, action_name, None)
    if callback is None:
        report_action_failure(window, action_name, RuntimeError(f'backend action not available: {action_name}'))
        return False
    try:
        callback()
    except Exception as exc:  # pragma: no cover - UI action boundary safety net
        report_action_failure(window, action_name, exc)
        return False
    return True
