from __future__ import annotations

from typing import Any

from spine_ultrasound_ui.views.status_presenters import (
    ExecutionPresenter,
    MonitorPresenter,
    OverviewPresenter,
    PreparePresenter,
    ReplayPresenter,
    SettingsPresenter,
    build_status_context,
)


class MainWindowStatusPresenter:
    """Coordinates page-specific presenters so MainWindow stays wiring-focused."""

    def __init__(self) -> None:
        self.overview_presenter = OverviewPresenter()
        self.prepare_presenter = PreparePresenter()
        self.execution_presenter = ExecutionPresenter()
        self.monitor_presenter = MonitorPresenter()
        self.replay_presenter = ReplayPresenter()
        self.settings_presenter = SettingsPresenter()

    def apply(self, window: Any, payload: dict) -> None:
        ctx = build_status_context(window, payload)
        window._apply_permissions(payload)
        for name, (lab, det) in window.overview_page.device_labels.items():
            status = ctx.devices[name]
            state_kind = window._device_state(status.get("connected", False), status.get("health", ""))
            window._set_badge_state(lab, status["health"], state_kind)
            det.setText(status["detail"])
        window.overview_page.timeline.set_current(ctx.system_state)
        self.overview_presenter.apply(ctx)
        self.prepare_presenter.apply(ctx)
        self.execution_presenter.apply(ctx)
        self.monitor_presenter.apply(ctx)
        self.replay_presenter.apply(ctx)
        self.settings_presenter.apply(ctx)
        if ctx.safety.get("safe_to_scan", False) and window._system_state_kind(ctx.system_state) != "danger":
            window.alarm_banner.set_normal("系统正常 · 安全联锁通过，可继续执行流程")
        else:
            blockers = ctx.readiness.get("blockers", [])
            details = "、".join(str(item) for item in blockers[:3]) if blockers else ctx.recommended_reason
            window.alarm_banner.set_alarm("WARN", f"当前不满足执行条件 · {details}")
