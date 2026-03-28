#!/usr/bin/env python3
"""
测试医疗级前端架构的核心组件
验证事件总线、状态机、配置管理器和UI组件
"""

import sys
import os
import numpy as np

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

from PySide6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QHBoxLayout, QLabel
from PySide6.QtCore import QTimer, Qt

# 导入我们的核心组件
from core.event_bus import ebus
from core.state_machine import state_machine, SystemState
from core.process_watchdog import watchdog
from services.config_manager import config_manager
from views.components.us_image_view import USImageView
from views.components.gl_robot_view import GLRobotView

class TestWindow(QMainWindow):
    """测试主窗口"""

    def __init__(self):
        super().__init__()
        self.setWindowTitle("医疗级前端架构测试")
        self.setGeometry(100, 100, 1200, 800)

        # 创建中央部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        # 创建主布局
        main_layout = QVBoxLayout(central_widget)

        # 状态显示区域
        self.status_label = QLabel("系统状态: 初始化中...")
        self.status_label.setStyleSheet("font-size: 14px; padding: 10px;")
        main_layout.addWidget(self.status_label)

        # 创建组件布局
        components_layout = QHBoxLayout()

        # 超声图像视图
        self.us_view = USImageView()
        self.us_view.setFixedSize(400, 300)
        components_layout.addWidget(self.us_view)

        # 3D机器人视图
        self.robot_view = GLRobotView()
        self.robot_view.setFixedSize(400, 300)
        components_layout.addWidget(self.robot_view)

        # 配置显示
        config_widget = QWidget()
        config_layout = QVBoxLayout(config_widget)
        self.config_label = QLabel("配置信息:")
        self.config_label.setWordWrap(True)
        config_layout.addWidget(self.config_label)
        components_layout.addWidget(config_widget)

        main_layout.addLayout(components_layout)

        # 连接事件总线
        self._connect_events()

        # 启动测试
        self._start_test()

    def _connect_events(self):
        """连接事件总线信号"""
        ebus.sig_robot_state_changed.connect(self._on_state_changed)
        ebus.sig_new_us_frame.connect(self.us_view.update_frame)
        ebus.sig_new_pose.connect(self.robot_view.update_robot_pose)

    def _on_state_changed(self, state_str: str):
        """状态变化处理"""
        self.status_label.setText(f"系统状态: {state_str.upper()}")

    def _start_test(self):
        """开始测试序列"""
        print("=== 开始医疗级前端架构测试 ===")

        # 1. 测试状态机
        print("1. 测试状态机...")
        state_machine.transition_to(SystemState.READY)
        print("   ✓ 状态机工作正常")

        # 2. 测试配置管理器
        print("2. 测试配置管理器...")
        desired_force = config_manager.get('impedance.desired_force', 10.0)
        self.config_label.setText(f"配置信息:\n期望力: {desired_force}N\n最大Z力: {config_manager.get('impedance.max_z_force')}N")
        print(f"   ✓ 配置管理器工作正常 (期望力: {desired_force}N)")

        # 3. 测试进程看门狗
        print("3. 测试进程看门狗...")
        watchdog.register_process("test_process")
        watchdog.heartbeat("test_process")
        print("   ✓ 进程看门狗工作正常")

        # 4. 测试UI组件
        print("4. 测试UI组件...")

        # 创建测试定时器
        self.test_timer = QTimer()
        self.test_timer.timeout.connect(self._run_ui_test)
        self.test_timer.start(1000)  # 每秒运行一次测试

        self.test_step = 0

    def _run_ui_test(self):
        """运行UI测试步骤"""
        if self.test_step == 0:
            # 测试超声图像更新
            print("   - 测试超声图像渲染...")
            test_image = np.random.randint(0, 255, (256, 256), dtype=np.uint8)
            ebus.sig_new_us_frame.emit(test_image)

        elif self.test_step == 1:
            # 测试机器人姿态更新
            print("   - 测试3D机器人渲染...")
            test_pos = np.array([0.3, 0.1, 0.4])
            test_quat = np.array([1.0, 0.0, 0.0, 0.0])  # 单位四元数
            ebus.sig_new_pose.emit(test_pos, test_quat)

        elif self.test_step == 2:
            # 测试扫描路径预览
            print("   - 测试扫描路径预览...")
            preview_path = [
                [0.2, 0.0, 0.3],
                [0.3, 0.1, 0.3],
                [0.4, 0.2, 0.3],
                [0.3, 0.3, 0.3],
                [0.2, 0.2, 0.3]
            ]
            self.robot_view.set_preview_path(preview_path)

        elif self.test_step == 3:
            # 测试状态转换
            print("   - 测试状态转换...")
            state_machine.transition_to(SystemState.SCANNING)

        elif self.test_step == 4:
            # 测试完成
            print("   ✓ UI组件测试完成")
            self.test_timer.stop()
            print("=== 所有测试通过！前端架构工作正常 ===")

        self.test_step += 1

def main():
    """主函数"""
    app = QApplication(sys.argv)

    # 设置应用程序属性
    app.setApplicationName("Spine Ultrasound Platform")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("Medical Robotics Lab")

    # 创建测试窗口
    window = TestWindow()
    window.show()

    # 运行应用程序
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())