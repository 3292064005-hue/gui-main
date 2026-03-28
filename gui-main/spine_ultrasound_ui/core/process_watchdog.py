import time
import threading
from typing import Dict, Callable, Any
from PySide6.QtCore import QTimer, QObject, Signal
from .event_bus import ebus

class ProcessWatchdog(QObject):
    """
    多进程健康度监控系统
    基于心跳机制监控所有子进程的健康状态
    """

    # 健康状态变化信号
    health_status_changed = Signal(str, bool)  # (process_name, is_healthy)

    def __init__(self, heartbeat_timeout_ms: int = 500):
        super().__init__()
        self.heartbeat_timeout_ms = heartbeat_timeout_ms
        self.processes: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()
        self._running = True

        # 启动监控定时器
        self.monitor_timer = QTimer()
        self.monitor_timer.timeout.connect(self._check_health)
        self.monitor_timer.start(100)  # 每100ms检查一次

        # 连接到事件总线
        self.health_status_changed.connect(ebus.sig_process_health_changed)

    def register_process(self, process_name: str, heartbeat_callback: Callable[[], bool] = None):
        """
        注册需要监控的进程

        Args:
            process_name: 进程名称
            heartbeat_callback: 心跳检查回调函数，返回True表示健康
        """
        with self._lock:
            self.processes[process_name] = {
                'last_heartbeat': time.time(),
                'is_healthy': True,
                'heartbeat_callback': heartbeat_callback,
                'consecutive_failures': 0
            }
        print(f"[WATCHDOG] Registered process: {process_name}")

    def unregister_process(self, process_name: str):
        """注销进程监控"""
        with self._lock:
            if process_name in self.processes:
                del self.processes[process_name]
                print(f"[WATCHDOG] Unregistered process: {process_name}")

    def heartbeat(self, process_name: str):
        """接收进程心跳"""
        with self._lock:
            if process_name in self.processes:
                self.processes[process_name]['last_heartbeat'] = time.time()
                self.processes[process_name]['consecutive_failures'] = 0

                # 如果之前不健康，现在恢复健康
                if not self.processes[process_name]['is_healthy']:
                    self.processes[process_name]['is_healthy'] = True
                    self.health_status_changed.emit(process_name, True)
                    print(f"[WATCHDOG] Process {process_name} recovered")

    def _check_health(self):
        """检查所有进程的健康状态"""
        if not self._running:
            return

        current_time = time.time()
        timeout_seconds = self.heartbeat_timeout_ms / 1000.0

        with self._lock:
            for process_name, info in self.processes.items():
                time_since_last_heartbeat = current_time - info['last_heartbeat']
                was_healthy = info['is_healthy']

                # 检查心跳超时
                if time_since_last_heartbeat > timeout_seconds:
                    info['consecutive_failures'] += 1

                    # 如果连续失败超过阈值，标记为不健康
                    if info['consecutive_failures'] >= 3:  # 3次连续超时
                        if was_healthy:
                            info['is_healthy'] = False
                            self.health_status_changed.emit(process_name, False)
                            print(f"[WATCHDOG] Process {process_name} became unhealthy (timeout)")

                # 检查自定义心跳回调
                elif info['heartbeat_callback']:
                    try:
                        if not info['heartbeat_callback']():
                            info['consecutive_failures'] += 1
                            if info['consecutive_failures'] >= 2:  # 自定义检查失败阈值
                                if was_healthy:
                                    info['is_healthy'] = False
                                    self.health_status_changed.emit(process_name, False)
                                    print(f"[WATCHDOG] Process {process_name} became unhealthy (callback)")
                        else:
                            # 回调成功，重置失败计数
                            info['consecutive_failures'] = 0
                            if not was_healthy:
                                info['is_healthy'] = True
                                self.health_status_changed.emit(process_name, True)
                                print(f"[WATCHDOG] Process {process_name} recovered (callback)")
                    except Exception as e:
                        print(f"[WATCHDOG] Error in heartbeat callback for {process_name}: {e}")
                        info['consecutive_failures'] += 1

    def get_process_status(self, process_name: str) -> Dict[str, Any]:
        """获取进程状态信息"""
        with self._lock:
            return self.processes.get(process_name, {}).copy()

    def get_all_status(self) -> Dict[str, Dict[str, Any]]:
        """获取所有进程状态"""
        with self._lock:
            return {name: info.copy() for name, info in self.processes.items()}

    def is_system_healthy(self) -> bool:
        """检查整个系统是否健康"""
        with self._lock:
            return all(info['is_healthy'] for info in self.processes.values())

    def stop(self):
        """停止监控"""
        self._running = False
        if self.monitor_timer:
            self.monitor_timer.stop()

# 全局看门狗实例
watchdog = ProcessWatchdog()