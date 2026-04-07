from enum import Enum
from typing import Dict, Any, Optional
from PySide6.QtCore import QObject, Signal
from .qt_signal_bus import get_qt_signal_bus as get_event_bus

class SystemState(Enum):
    """系统全局状态枚举"""
    IDLE = "idle"           # 空闲状态，等待用户操作
    INITIALIZING = "initializing"  # 系统初始化中
    READY = "ready"         # 准备就绪，可以开始扫描
    SCANNING = "scanning"   # 正在执行扫描
    PAUSED = "paused"       # 扫描暂停
    ERROR = "error"         # 错误状态
    EMERGENCY_STOP = "emergency_stop"  # 紧急停止
    SHUTTING_DOWN = "shutting_down"  # 系统关闭中

class StateMachine(QObject):
    """
    全局状态机 - 管理整个医疗系统的状态转换
    确保状态转换的原子性和一致性
    """
    _instance = None

    # 状态变化信号
    state_changed = Signal(SystemState, SystemState)  # (old_state, new_state)

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(StateMachine, cls).__new__(cls)
            QObject.__init__(cls._instance)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        super().__init__()
        self._initialized = True
        self._current_state = SystemState.IDLE
        self._state_data: Dict[str, Any] = {}
        self._transition_rules = self._build_transition_rules()

        # 连接事件总线
        ebus = get_event_bus()
        ebus.sig_cmd_emergency_stop.connect(self._handle_emergency_stop)
        ebus.sig_process_health_changed.connect(self._handle_process_health_change)

    def _build_transition_rules(self) -> Dict[SystemState, set[SystemState]]:
        """定义状态转换规则"""
        return {
            SystemState.IDLE: {SystemState.INITIALIZING, SystemState.SHUTTING_DOWN},
            SystemState.INITIALIZING: {SystemState.READY, SystemState.ERROR},
            SystemState.READY: {SystemState.SCANNING, SystemState.IDLE, SystemState.ERROR},
            SystemState.SCANNING: {SystemState.PAUSED, SystemState.READY, SystemState.ERROR, SystemState.EMERGENCY_STOP},
            SystemState.PAUSED: {SystemState.SCANNING, SystemState.READY, SystemState.ERROR},
            SystemState.ERROR: {SystemState.IDLE, SystemState.SHUTTING_DOWN},
            SystemState.EMERGENCY_STOP: {SystemState.IDLE},
            SystemState.SHUTTING_DOWN: set()  # 最终状态
        }

    def get_current_state(self) -> SystemState:
        """获取当前状态"""
        return self._current_state

    def can_transition_to(self, new_state: SystemState) -> bool:
        """检查是否可以转换到指定状态"""
        return new_state in self._transition_rules.get(self._current_state, set())

    def transition_to(self, new_state: SystemState, data: Optional[Dict[str, Any]] = None) -> bool:
        """
        尝试转换到新状态
        Returns: 是否转换成功
        """
        if not self.can_transition_to(new_state):
            print(f"[STATE] Invalid transition: {self._current_state} -> {new_state}")
            return False

        old_state = self._current_state
        self._current_state = new_state

        if data:
            self._state_data.update(data)

        print(f"[STATE] Transition: {old_state.value} -> {new_state.value}")

        # 发送状态变化信号
        self.state_changed.emit(old_state, new_state)

        # 广播到事件总线
        ebus.sig_robot_state_changed.emit(new_state.value)

        # 执行状态进入动作
        self._on_enter_state(new_state, data)

        return True

    def _on_enter_state(self, state: SystemState, data: Optional[Dict[str, Any]] = None):
        """状态进入时的动作"""
        if state == SystemState.EMERGENCY_STOP:
            # 紧急停止时立即停止所有运动
            ebus.sig_cmd_emergency_stop.emit()
            print("[EMERGENCY] System emergency stop activated!")

        elif state == SystemState.ERROR:
            # 错误状态时记录错误信息
            error_msg = data.get('error_message', 'Unknown error') if data else 'Unknown error'
            print(f"[ERROR] System entered error state: {error_msg}")

    def _handle_emergency_stop(self):
        """处理紧急停止命令"""
        if self._current_state != SystemState.EMERGENCY_STOP:
            self.transition_to(SystemState.EMERGENCY_STOP)

    def _handle_process_health_change(self, process_name: str, is_healthy: bool):
        """处理进程健康状态变化"""
        if not is_healthy and self._current_state in [SystemState.SCANNING, SystemState.READY]:
            # 关键进程不健康时进入错误状态
            self.transition_to(SystemState.ERROR, {
                'error_message': f'Process {process_name} health check failed'
            })

    def get_state_data(self, key: str) -> Any:
        """获取状态数据"""
        return self._state_data.get(key)

    def set_state_data(self, key: str, value: Any):
        """设置状态数据"""
        self._state_data[key] = value

def get_state_machine():
    """获取全局状态机实例"""
    return StateMachine()

# 全局状态机实例 - 延迟创建
state_machine = None