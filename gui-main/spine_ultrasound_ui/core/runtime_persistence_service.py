from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.core.settings_store import SettingsStore
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.config_service import ConfigService
from spine_ultrasound_ui.utils import now_text


class RuntimePersistenceService:
    """Owns workspace-backed runtime/UI persistence for the desktop shell.

    Keeping this logic out of AppController prevents persistence from becoming
    a second orchestration surface and makes it easier to reuse from future
    CLI/headless tooling.
    """

    def __init__(
        self,
        *,
        config_service: ConfigService,
        runtime_config_path: Path,
        ui_prefs_path: Path,
        session_meta_path: Path,
    ) -> None:
        self.config_service = config_service
        self.runtime_config_path = runtime_config_path
        self.ui_prefs_store = SettingsStore(ui_prefs_path)
        self.session_meta_store = SettingsStore(session_meta_path)

    def load_initial_config(self) -> RuntimeConfig:
        if self.runtime_config_path.exists():
            try:
                return self.config_service.load(self.runtime_config_path)
            except Exception:
                pass
        return RuntimeConfig()

    def save_runtime_config(self, config: RuntimeConfig) -> Path:
        self.config_service.save(self.runtime_config_path, config)
        self.write_meta(last_config_save=now_text())
        return self.runtime_config_path

    def reload_runtime_config(self) -> RuntimeConfig:
        config = self.config_service.load(self.runtime_config_path)
        self.write_meta(last_config_load=now_text())
        return config

    def load_ui_preferences(self) -> dict[str, Any]:
        return self.ui_prefs_store.load()

    def save_ui_preferences(self, data: dict[str, Any]) -> None:
        self.ui_prefs_store.save(data)
        self.write_meta(last_ui_save=now_text())

    def write_meta(self, **updates: str) -> None:
        data = self.session_meta_store.load()
        data.update({k: v for k, v in updates.items() if v})
        self.session_meta_store.save(data)

    def snapshot(self, workspace: Path) -> dict[str, Any]:
        meta = self.session_meta_store.load()
        return {
            "workspace": str(workspace),
            "config_path": str(self.runtime_config_path),
            "ui_path": str(self.ui_prefs_store.path),
            "last_config_save": meta.get("last_config_save", "未保存"),
            "last_ui_save": meta.get("last_ui_save", "未保存"),
            "last_config_load": meta.get("last_config_load", "未加载"),
            "config_exists": self.runtime_config_path.exists(),
            "ui_exists": self.ui_prefs_store.path.exists(),
        }
