from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import QObject, Signal

from spine_ultrasound_ui.models import RuntimeConfig
from spine_ultrasound_ui.services.config_service import ConfigService
from spine_ultrasound_ui.core.qt_signal_bus import qt_bus as ebus


class ConfigManager(QObject):
    """Legacy compatibility wrapper for the canonical RuntimeConfig mainline.

    Historical UI code expected a mutable dotted-key config manager backed by a
    repository-local file. The canonical configuration path is now
    :class:`RuntimeConfig` + :class:`ConfigService`; this wrapper survives only as
    a compatibility shim so that any stray legacy callers do not create a second
    configuration truth source.

    Persistence strategy:
    - prefer an explicit ``RUNTIME_CONFIG_PATH`` override,
    - otherwise use ``data/runtime/runtime_config.json`` under the repository root,
    - fall back to ``RuntimeConfig()`` defaults when no persisted file exists.

    Compatibility semantics:
    - canonical flat RuntimeConfig fields remain the source of truth,
    - legacy dotted keys are resolved to canonical fields by leaf-name matching,
    - section reads/writes expose curated field subsets without re-introducing a
      second mutable nested configuration schema.
    """

    _instance: "ConfigManager | None" = None
    _CANONICAL_FIELDS = frozenset(RuntimeConfig.__dataclass_fields__.keys())
    _SECTION_FIELDS: dict[str, tuple[str, ...]] = {
        'robot': (
            'remote_ip', 'local_ip', 'robot_model', 'axis_count', 'sdk_robot_class', 'preferred_link',
            'requires_single_control_source', 'force_sensor_provider', 'rt_network_tolerance_percent',
            'joint_filter_hz', 'cart_filter_hz', 'torque_filter_hz', 'collision_detection_enabled',
            'collision_sensitivity', 'collision_behavior', 'collision_fallback_mm', 'soft_limit_enabled',
            'joint_soft_limit_margin_deg', 'singularity_avoidance_enabled', 'rl_project_name', 'rl_task_name',
            'xpanel_vout_mode', 'cartesian_impedance', 'desired_wrench_n', 'fc_frame_type', 'fc_frame_matrix',
            'tcp_frame_matrix', 'load_kg', 'load_com_mm', 'load_inertia',
        ),
        'scan': (
            'scan_speed_mm_s', 'sample_step_mm', 'segment_length_mm', 'strip_width_mm', 'strip_overlap_mm',
            'scan_follow_lateral_amplitude_mm', 'scan_follow_frequency_hz', 'scan_force_target_n',
            'scan_force_tolerance_n', 'scan_normal_pi_kp', 'scan_normal_pi_ki', 'scan_tangent_speed_min_mm_s',
            'scan_tangent_speed_max_mm_s', 'scan_pose_trim_gain', 'scan_follow_enable_lateral_modulation', 'orientation_trim',
        ),
        'contact': (
            'pressure_target', 'pressure_upper', 'pressure_lower', 'contact_seek_speed_mm_s', 'retreat_speed_mm_s',
            'seek_contact_max_travel_mm', 'seek_contact_max_step_mm', 'contact_force_target_n',
            'contact_force_tolerance_n', 'contact_establish_cycles', 'normal_admittance_gain',
            'normal_damping_gain', 'normal_velocity_quiet_threshold_mm_s', 'retract_travel_mm',
            'retract_release_force_n', 'retract_release_cycles', 'retract_safe_gap_mm', 'retract_max_travel_mm',
            'retract_jerk_limit_mm_s3', 'retract_timeout_ms', 'contact_control', 'force_estimator',
        ),
        'runtime': (
            'rt_mode', 'network_stale_ms', 'pressure_stale_ms', 'telemetry_rate_hz', 'rt_stale_state_timeout_ms',
            'rt_phase_transition_debounce_cycles', 'rt_max_cart_step_mm', 'rt_max_cart_vel_mm_s',
            'rt_max_cart_acc_mm_s2', 'rt_max_pose_trim_deg', 'rt_max_force_error_n', 'rt_integrator_limit_n',
            'pause_hold_position_guard_mm', 'pause_hold_force_guard_n', 'pause_hold_drift_kp',
            'pause_hold_drift_ki', 'pause_hold_integrator_leak',
        ),
        'quality': (
            'image_quality_threshold', 'roi_mode', 'smoothing_factor', 'reconstruction_step', 'feature_threshold',
        ),
    }
    config_updated = Signal(str, object)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance

    def __init__(self) -> None:
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self._initialized = True
        self._config_service = ConfigService()
        self._root_dir = Path(__file__).resolve().parents[2]
        self._config_file = self._resolve_runtime_config_path()
        self._runtime_config = self._load_runtime_config()
        self.config_updated.connect(ebus.sig_config_updated.emit)

    def _resolve_runtime_config_path(self) -> Path:
        env_path = os.getenv("RUNTIME_CONFIG_PATH", "").strip()
        if env_path:
            return Path(env_path)
        return self._root_dir / "data" / "runtime" / "runtime_config.json"

    def _load_runtime_config(self) -> RuntimeConfig:
        try:
            if self._config_file.exists():
                return self._config_service.load(self._config_file)
        except Exception:
            # Compatibility path: malformed legacy runtime config should not crash
            # desktop startup; callers receive canonical defaults instead.
            pass
        return RuntimeConfig()

    def _runtime_payload(self) -> dict[str, Any]:
        return self._runtime_config.to_dict()

    @classmethod
    def _canonical_key(cls, key: str) -> str | None:
        normalized = str(key or '').strip()
        if not normalized:
            return None
        if normalized in cls._CANONICAL_FIELDS:
            return normalized
        leaf = normalized.split('.')[-1]
        if leaf in cls._CANONICAL_FIELDS:
            return leaf
        return None

    @classmethod
    def _section_payload(cls, payload: dict[str, Any], section: str) -> dict[str, Any]:
        fields = cls._SECTION_FIELDS.get(section, ())
        return {field: payload[field] for field in fields if field in payload}

    def get(self, key: str, default: Any = None) -> Any:
        normalized = str(key or '').strip()
        if not normalized:
            return default
        payload = self._runtime_payload()
        canonical = self._canonical_key(normalized)
        if canonical is not None:
            return payload.get(canonical, default)
        if normalized in self._SECTION_FIELDS:
            section = self._section_payload(payload, normalized)
            return section if section else default
        if '.' in normalized:
            section, leaf = normalized.split('.', 1)
            section_payload = self._section_payload(payload, section)
            if leaf in section_payload:
                return section_payload[leaf]
        return default

    def set(self, key: str, value: Any, save: bool = True) -> None:
        normalized = str(key or '').strip()
        canonical = self._canonical_key(normalized)
        if canonical is None:
            raise KeyError(f"legacy ConfigManager only supports canonical RuntimeConfig fields or dotted aliases: {key}")
        updated = self._runtime_payload()
        updated[canonical] = value
        self._runtime_config = RuntimeConfig.from_dict(updated)
        self.config_updated.emit(canonical, value)
        if save:
            self.save_config()

    def get_section(self, section: str) -> dict[str, Any]:
        payload = self._section_payload(self._runtime_payload(), str(section or '').strip())
        return dict(payload)

    def set_section(self, section: str, data: dict[str, Any], save: bool = True) -> None:
        section_name = str(section or '').strip()
        fields = self._SECTION_FIELDS.get(section_name)
        if not fields:
            raise KeyError(f"legacy ConfigManager only supports compatibility sections: {section_name}")
        updated = self._runtime_payload()
        for key, value in dict(data or {}).items():
            canonical = self._canonical_key(f'{section_name}.{key}')
            if canonical is None or canonical not in fields:
                raise KeyError(f"unsupported legacy config field for section {section_name}: {key}")
            updated[canonical] = value
            self.config_updated.emit(canonical, value)
        self._runtime_config = RuntimeConfig.from_dict(updated)
        if save:
            self.save_config()

    def save_config(self) -> None:
        self._config_file.parent.mkdir(parents=True, exist_ok=True)
        self._config_service.save(self._config_file, self._runtime_config)

    def reload_config(self) -> None:
        self._runtime_config = self._load_runtime_config()

    def get_all_config(self) -> dict[str, Any]:
        return dict(self._runtime_payload())


config_manager = ConfigManager()
