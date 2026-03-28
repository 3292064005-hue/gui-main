from PySide6.QtCore import QObject, Signal
import numpy as np

class EventBus(QObject):
    """
    全局单例事件总线。
    所有的组件都只和 EventBus 通信，彻底解耦。
    """
    _instance = None

    # --- 定义系统级强类型信号 ---

    # 硬件状态信号
    sig_robot_state_changed = Signal(str) # 例如: "IDLE", "SCANNING", "ERROR"
    sig_force_warning = Signal(float)     # 传出力矩过载的数值

    # 数据流信号
    sig_new_us_frame = Signal(np.ndarray) # 高频超声图像帧
    sig_new_pose = Signal(np.ndarray, np.ndarray) # 高频位姿 (pos, quat)

    # 业务指令信号
    sig_cmd_start_scan = Signal()
    sig_cmd_emergency_stop = Signal()

    # 配置更新信号
    sig_config_updated = Signal(str, object) # (config_key, new_value)

    # 进程健康状态信号
    sig_process_health_changed = Signal(str, bool) # (process_name, is_healthy)

    # 诊断和分析信号
    sig_new_diagnostic_data = Signal(dict) # 诊断数据字典
    sig_scan_progress = Signal(float) # 扫描进度 (0.0-1.0)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
            # 在这里必须调用 QObject 的 __init__，这是 PySide6 单例的避坑点
            QObject.__init__(cls._instance)
        return cls._instance

def get_event_bus():
    """获取全局事件总线实例"""
    return EventBus()

# 全局便捷访问点 - 延迟创建
ebus = None

# 使用示例 (在接收到 SHM 数据的后台 QThread 中)：
# ebus.sig_new_us_frame.emit(numpy_image_array)

# 使用示例 (在 USImageView 组件的 __init__ 中)：
# ebus.sig_new_us_frame.connect(self.update_frame)
