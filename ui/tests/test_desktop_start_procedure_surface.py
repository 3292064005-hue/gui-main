from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_app_controller_exposes_canonical_start_procedure_entry() -> None:
    source = (ROOT / 'spine_ultrasound_ui' / 'core' / 'app_controller_runtime_mixin.py').read_text(encoding='utf-8')
    assert 'def start_procedure(self, procedure: str = "scan") -> None:' in source
    assert 'if normalized_procedure != "scan":' in source
    assert 'def start_scan(self)' not in source
    assert 'retired command alias: start_scan; use start_procedure(scan)' in source


def test_main_window_routes_scan_button_permissions_and_actions_to_start_procedure() -> None:
    main_window = (ROOT / 'spine_ultrasound_ui' / 'main_window.py').read_text(encoding='utf-8')
    layout = (ROOT / 'spine_ultrasound_ui' / 'views' / 'main_window_layout.py').read_text(encoding='utf-8')
    assert 'self.btn_scan_start: "start_procedure"' in main_window
    assert 'def _action_start_procedure(self) -> None:' in main_window
    assert 'self._invoke_backend_action("start_procedure")' in main_window
    assert '("btn_scan_start", "开始扫查", "start_procedure")' in layout


def test_permission_and_recommendation_surfaces_include_canonical_start_procedure() -> None:
    workflow = (ROOT / 'spine_ultrasound_ui' / 'core' / 'workflow_state_machine.py').read_text(encoding='utf-8')
    view_state = (ROOT / 'spine_ultrasound_ui' / 'core' / 'view_state_factory.py').read_text(encoding='utf-8')
    assert '"start_procedure": self._rule(' in workflow
    assert '"start_procedure": "开始扫查"' in workflow
    assert '"refresh_sdk_assets", "start_procedure", "run_preprocess"' in view_state
    assert '"start_procedure": "自动扫查"' in view_state


def test_view_state_factory_prefers_canonical_start_procedure_for_recommendations() -> None:
    from spine_ultrasound_ui.core.view_state_factory import ViewStateFactory
    action = ViewStateFactory._pick_recommended_command({
        "start_procedure": {"enabled": True, "reason": "ok"},
        "start_scan": {"enabled": True, "reason": "compat"},
    })
    assert action == "start_procedure"
    assert ViewStateFactory._recommended_tab("start_procedure") == "自动扫查"
