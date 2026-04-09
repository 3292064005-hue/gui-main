
from __future__ import annotations

from pathlib import Path
from typing import Any

from spine_ultrasound_ui.core.settings_store import SettingsStore
from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.clinical_config_service import ClinicalConfigService
from spine_ultrasound_ui.services.config_service import ConfigService
from spine_ultrasound_ui.utils import now_text


class RuntimePersistenceService:
    """Owns workspace-backed runtime/UI persistence for the desktop shell.

    The service is the authoritative ingress for persisted runtime config.
    Every config loaded from disk is normalized back onto the active clinical
    profile baseline before it can re-enter the controller/backend chain.
    """

    def __init__(
        self,
        *,
        config_service: ConfigService,
        runtime_config_path: Path,
        ui_prefs_path: Path,
        session_meta_path: Path,
        profile_service: ClinicalConfigService | None = None,
    ) -> None:
        self.config_service = config_service
        self.runtime_config_path = runtime_config_path
        self.ui_prefs_store = SettingsStore(ui_prefs_path)
        self.session_meta_store = SettingsStore(session_meta_path)
        self.profile_service = profile_service or ClinicalConfigService()

    def _baseline_config(self) -> RuntimeConfig:
        """Return the active profile baseline runtime config."""
        return self.profile_service.apply_mainline_defaults(RuntimeConfig())

    def _normalize_loaded_config(self, config: RuntimeConfig) -> RuntimeConfig:
        """Clamp a loaded config onto the active profile baseline.

        Boundary behavior:
            - Mainline identity/control-source/runtime-mode fields are forced
              back to the active clinical baseline.
            - Non-mainline user-tunable fields are preserved when legal.
        """
        return self.profile_service.apply_mainline_defaults(config)

    def load_initial_config(self) -> RuntimeConfig:
        """Load startup config and repair persisted drift before controller start.

        Returns:
            The normalized runtime config safe to hand to the controller/backend.

        Boundary behavior:
            - Missing config file => returns profile baseline.
            - Corrupt/unreadable config => rewrites baseline to disk.
            - Drifted config => rewrites normalized baseline-clamped payload.
        """
        baseline = self._baseline_config()
        if not self.runtime_config_path.exists():
            return baseline
        try:
            loaded = self.config_service.load(self.runtime_config_path)
        except Exception:
            self.config_service.save(self.runtime_config_path, baseline)
            self.write_meta(last_config_load=now_text(), last_config_repair='startup_rebuilt_from_baseline')
            return baseline
        normalized = self._normalize_loaded_config(loaded)
        if normalized.to_dict() != loaded.to_dict():
            self.config_service.save(self.runtime_config_path, normalized)
            self.write_meta(last_config_repair='startup_clamped_to_profile_baseline')
        self.write_meta(last_config_load=now_text())
        return normalized

    def save_runtime_config(self, config: RuntimeConfig) -> Path:
        self.config_service.save(self.runtime_config_path, config)
        self.write_meta(last_config_save=now_text())
        return self.runtime_config_path

    def reload_runtime_config(self) -> RuntimeConfig:
        """Reload persisted config through the same mainline clamp used at startup.

        Returns:
            Normalized runtime config safe to hand back to the controller.

        Raises:
            FileNotFoundError: When no persisted runtime config exists.

        Boundary behavior:
            - Missing config file => raises ``FileNotFoundError`` so the caller
              can report the missing persistence target.
            - Corrupt/unreadable config => rewrites baseline to disk and raises
              ``RuntimeError`` so UI/controller code can keep the current live
              config while still repairing the persisted file on disk.
            - Drifted config => rewrites normalized baseline-clamped payload.
        """
        if not self.runtime_config_path.exists():
            raise FileNotFoundError(self.runtime_config_path)
        baseline = self._baseline_config()
        try:
            loaded = self.config_service.load(self.runtime_config_path)
        except Exception as exc:
            self.config_service.save(self.runtime_config_path, baseline)
            self.write_meta(last_config_load=now_text(), last_config_repair='reload_rebuilt_from_baseline')
            raise RuntimeError(f'failed to load runtime config: {self.runtime_config_path}') from exc
        normalized = self._normalize_loaded_config(loaded)
        if normalized.to_dict() != loaded.to_dict():
            self.config_service.save(self.runtime_config_path, normalized)
            self.write_meta(last_config_repair='reload_clamped_to_profile_baseline')
        self.write_meta(last_config_load=now_text())
        return normalized

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
            'workspace': str(workspace),
            'config_path': str(self.runtime_config_path),
            'ui_path': str(self.ui_prefs_store.path),
            'last_config_save': meta.get('last_config_save', '未保存'),
            'last_ui_save': meta.get('last_ui_save', '未保存'),
            'last_config_load': meta.get('last_config_load', '未加载'),
            'config_exists': self.runtime_config_path.exists(),
            'ui_exists': self.ui_prefs_store.path.exists(),
        }
