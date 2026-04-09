
from __future__ import annotations

from PySide6.QtWidgets import QApplication

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.widgets.config_form import ConfigForm


def _app():
    app = QApplication.instance()
    if app is None:
        app = QApplication([])
    return app


def test_config_form_locks_mainline_identity_controls() -> None:
    _app()
    form = ConfigForm(RuntimeConfig(rt_mode='directTorque', preferred_link='wifi', requires_single_control_source=False))
    assert form.rt_mode.isEnabled() is False
    assert form.preferred_link.isEnabled() is False
    assert form.robot_model.isEnabled() is False
    assert form.sdk_robot_class.isEnabled() is False
    assert form.axis_count.isEnabled() is False
    assert form.requires_single_control_source.isEnabled() is False
    config = form.read_config()
    assert config.rt_mode == 'cartesianImpedance'
    assert config.preferred_link == 'wired_direct'
    assert config.robot_model == 'xmate3'
    assert config.sdk_robot_class == 'xMateRobot'
    assert config.axis_count == 6
    assert config.requires_single_control_source is True
