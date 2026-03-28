#!/usr/bin/env python3
"""
单元测试：验证前端架构核心组件
不启动GUI，直接测试逻辑功能
"""

import sys
import os
import numpy as np
from pathlib import Path

# 添加项目路径
sys.path.insert(0, os.path.dirname(__file__))

def test_event_bus():
    """测试事件总线"""
    print("测试事件总线...")

    # 清理可能存在的模块缓存
    modules_to_clear = ['core.event_bus']
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    from core.event_bus import get_event_bus
    ebus = get_event_bus()

    # 测试信号定义
    assert hasattr(ebus, 'sig_robot_state_changed')
    assert hasattr(ebus, 'sig_new_us_frame')
    assert hasattr(ebus, 'sig_new_pose')
    print("✓ 事件总线信号定义正确")

def test_state_machine():
    """测试状态机"""
    print("测试状态机...")

    # 清理可能存在的模块缓存
    modules_to_clear = ['core.state_machine', 'core.event_bus']
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    from core.state_machine import get_state_machine, SystemState
    state_machine = get_state_machine()

    # 测试初始状态
    assert state_machine.get_current_state() == SystemState.IDLE
    print("✓ 初始状态正确")

    # 测试状态转换
    assert state_machine.transition_to(SystemState.READY)
    assert state_machine.get_current_state() == SystemState.READY
    print("✓ 状态转换正常")

def test_config_manager():
    """测试配置管理器"""
    print("测试配置管理器...")

    from core.settings_store import SettingsStore
    import tempfile
    import os

    # 创建临时文件进行测试
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = f.name

    try:
        store = SettingsStore(Path(temp_path))

        # 测试保存和加载
        test_data = {'impedance': {'desired_force': 10.0}, 'test': {'value': 42}}
        store.save(test_data)
        loaded_data = store.load()

        assert loaded_data['impedance']['desired_force'] == 10.0
        assert loaded_data['test']['value'] == 42
        print("✓ 配置存储和加载正常")

    finally:
        os.unlink(temp_path)

def test_process_watchdog():
    """测试进程看门狗"""
    print("测试进程看门狗...")

    # 清理可能存在的模块缓存
    modules_to_clear = ['core.process_watchdog', 'core.event_bus']
    for mod in modules_to_clear:
        if mod in sys.modules:
            del sys.modules[mod]

    from core.process_watchdog import ProcessWatchdog

    # 创建看门狗实例
    watchdog = ProcessWatchdog(heartbeat_timeout_ms=1000)

    # 注册测试进程
    watchdog.register_process("test_process_unit")

    # 发送心跳
    watchdog.heartbeat("test_process_unit")

    # 检查状态
    status = watchdog.get_process_status("test_process_unit")
    assert status['is_healthy'] == True
    print("✓ 进程看门狗工作正常")

    # 停止看门狗
    watchdog.stop()

def test_components_import():
    """测试组件导入"""
    print("测试组件导入...")

    # 测试US图像视图导入
    try:
        from views.components.us_image_view import USImageView
        print("✓ US图像视图导入成功")
    except ImportError as e:
        print(f"⚠ US图像视图导入失败: {e}")

    # 测试3D机器人视图导入
    try:
        from views.components.gl_robot_view import GLRobotView
        print("✓ 3D机器人视图导入成功")
    except ImportError as e:
        print(f"⚠ 3D机器人视图导入失败: {e}")

def main():
    """主测试函数"""
    print("=== 医疗级前端架构单元测试 ===\n")

    try:
        test_event_bus()
        print()

        test_state_machine()
        print()

        test_config_manager()
        print()

        test_process_watchdog()
        print()

        test_components_import()
        print()

        print("=== 所有单元测试通过！前端架构核心功能正常 ===")
        return 0

    except Exception as e:
        print(f"❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())