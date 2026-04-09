
from __future__ import annotations

from pathlib import Path
import json

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.utils import ensure_dir


class AppControllerConfigMixin:
    def save_runtime_config(self) -> Path:
        path = self.persistence.save_runtime_config(self.config)
        self._log('INFO', f'运行配置已保存到 {path}')
        self._emit_status()
        return path

    def reload_persisted_config(self) -> None:
        """Reload the persisted runtime config without breaking the active UI flow.

        Boundary behavior:
            - Missing persisted config => warn and keep the current in-memory
              runtime config.
            - Repaired/corrected persisted config => apply the normalized
              profile-baseline-aligned config and emit an informational log.
            - Unexpected reload failure => keep the current runtime config,
              surface the error in logs, and avoid propagating raw exceptions
              into the settings UI action path.
        """
        if not self.runtime_config_path.exists():
            self._log('WARN', '当前工作区还没有已保存的运行配置。')
            return
        try:
            reloaded = self.persistence.reload_runtime_config()
        except Exception as exc:
            self._log('ERROR', f'重新加载运行配置失败：{exc}')
            self._log('INFO', '已保留当前运行配置，未应用损坏或不可读的持久化文件。')
            self._emit_status()
            return
        self.update_config(reloaded)
        self._log('INFO', f'已从 {self.runtime_config_path} 重新加载运行配置。')
        self._emit_status()

    def restore_default_config(self) -> None:
        """Restore the active runtime configuration to the profile baseline."""
        baseline = self.config_profile_service.apply_mainline_defaults(RuntimeConfig())
        self.update_config(baseline)
        self._log('INFO', '运行配置已恢复为当前 profile 的主线基线。')
        self._emit_status()

    def apply_clinical_baseline(self) -> None:
        self.update_config(self.config_profile_service.apply_mainline_defaults(self.config))
        self._log('INFO', '已应用 xMate 临床主线基线配置。')
        self._emit_status()

    def export_governance_snapshot(self) -> Path:
        payload = self.control_plane_reader.build_governance_payload(
            telemetry=self.telemetry,
            config=self.config,
            workflow_artifacts=self.workflow_artifacts,
            current_experiment=self.session_service.current_experiment,
        )
        if self.session_service.current_session_dir is not None:
            target = ensure_dir(self.session_service.current_session_dir / 'export') / 'governance_snapshot.json'
        else:
            target = self.runtime_dir / 'governance_snapshot.json'
        target.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding='utf-8')
        self._log('INFO', f'治理快照已导出到 {target}')
        return target

    def refresh_session_governance(self) -> None:
        self.runtime_bridge.refresh_session_governance()
        self._log('INFO', '会话治理快照已刷新。')
        self._emit_status()

    def load_ui_preferences(self) -> dict:
        return self.persistence.load_ui_preferences()

    def save_ui_preferences(self, data: dict) -> None:
        self.persistence.save_ui_preferences(data)
        self._log('INFO', f'界面布局已保存到 {self.persistence.ui_prefs_store.path}')
        self._emit_status()

    def get_persistence_snapshot(self) -> dict:
        return self.persistence.snapshot(self.root_dir)
