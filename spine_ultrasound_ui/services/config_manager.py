import yaml
import os
from typing import Any, Dict, Optional
from PySide6.QtCore import QObject, Signal
from .event_bus import ebus

class ConfigManager(QObject):
    """
    YAML 配置中心 (单例模式)
    管理所有配置参数，与 data/config.yaml 强绑定
    """

    _instance = None
    config_updated = Signal(str, object)  # (key, new_value)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ConfigManager, cls).__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        super().__init__()
        self._initialized = True
        self._config: Dict[str, Any] = {}
        self._config_file = None
        self._load_config()

        # 连接到事件总线
        self.config_updated.connect(ebus.sig_config_updated)

    def _load_config(self):
        """加载配置文件"""
        config_paths = [
            os.path.join(os.path.dirname(__file__), '..', '..', 'configs', 'system.yaml'),
            os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'config.yaml'),
            'config.yaml'
        ]

        for config_path in config_paths:
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        self._config = yaml.safe_load(f) or {}
                    self._config_file = config_path
                    print(f"[CONFIG] Loaded configuration from: {config_path}")
                    break
                except Exception as e:
                    print(f"[CONFIG] Error loading {config_path}: {e}")

        if not self._config:
            # 使用默认配置
            self._config = self._get_default_config()
            print("[CONFIG] Using default configuration")

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            # 阻抗控制参数
            'impedance': {
                'stiffness': [2000.0, 2000.0, 50.0, 200.0, 200.0, 200.0],  # X,Y,Z,RX,RY,RZ
                'damping': [50.0, 50.0, 10.0, 20.0, 20.0, 20.0],
                'desired_force': 10.0,  # N
                'max_z_force': 35.0,   # N
                'max_xy_force': 20.0   # N
            },

            # 滤波参数
            'filtering': {
                'torque_cutoff': 30.0,  # Hz
                'pose_cutoff': 50.0,    # Hz
                'us_frame_rate': 30     # FPS
            },

            # AI 参数
            'ai': {
                'confidence_threshold': 0.8,
                'model_path': 'models/spine_detector.onnx',
                'enable_realtime': True
            },

            # UI 参数
            'ui': {
                'theme': 'medical_dark',
                'language': 'zh_CN',
                'auto_save_interval': 30  # seconds
            },

            # 硬件参数
            'hardware': {
                'robot_ip': '192.168.1.100',
                'us_device_id': '/dev/us_probe',
                'shm_buffer_size': 1048576  # 1MB
            },

            # 安全参数
            'safety': {
                'emergency_stop_timeout': 100,  # ms
                'force_warning_threshold': 25.0,  # N
                'heartbeat_timeout': 500  # ms
            }
        }

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any, save: bool = True):
        """设置配置值"""
        keys = key.split('.')
        config = self._config

        # 导航到父级字典
        for k in keys[:-1]:
            if k not in config or not isinstance(config[k], dict):
                config[k] = {}
            config = config[k]

        # 设置值
        old_value = config.get(keys[-1])
        config[keys[-1]] = value

        # 如果值发生变化，发送信号
        if old_value != value:
            self.config_updated.emit(key, value)

        # 保存到文件
        if save:
            self.save_config()

        print(f"[CONFIG] Updated {key}: {old_value} -> {value}")

    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置节"""
        return self._config.get(section, {})

    def set_section(self, section: str, data: Dict[str, Any], save: bool = True):
        """设置配置节"""
        self._config[section] = data

        if save:
            self.save_config()

        print(f"[CONFIG] Updated section: {section}")

    def save_config(self):
        """保存配置到文件"""
        if not self._config_file:
            # 如果没有配置文件，创建默认路径
            config_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
            os.makedirs(config_dir, exist_ok=True)
            self._config_file = os.path.join(config_dir, 'config.yaml')

        try:
            with open(self._config_file, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
            print(f"[CONFIG] Saved configuration to: {self._config_file}")
        except Exception as e:
            print(f"[CONFIG] Error saving configuration: {e}")

    def reload_config(self):
        """重新加载配置"""
        self._load_config()
        print("[CONFIG] Configuration reloaded")

    def get_all_config(self) -> Dict[str, Any]:
        """获取所有配置"""
        return self._config.copy()

# 全局配置管理器实例
config_manager = ConfigManager()