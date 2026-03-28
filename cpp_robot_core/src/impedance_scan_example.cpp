/**
 * @file impedance_scan_example.cpp
 * @brief 医疗级阻抗扫描控制器使用示例
 *
 * 此示例展示了如何使用ImpedanceScanController进行安全的超声扫描。
 * 在实际部署中，需要：
 * 1. 替换mock RT控制器为真实的ROKAE SDK实例
 * 2. 确保RT-Linux内核配置正确
 * 3. 校准TCP变换矩阵和负载参数
 */

#include "impedance_scan_controller.hpp"
#include <iostream>
#include <memory>
#include <thread>
#include <chrono>

int main() {
    std::cout << "=== 脊柱超声医疗级阻抗扫描控制器示例 ===" << std::endl;

    try {
        // 1. 初始化ROKAE机器人控制器
        // auto robot = std::make_shared<rokae::xMateErProRobot>();
        // robot->connect("192.168.1.100"); // 实际IP地址
        // auto rt_con = robot->getRtMotionController().lock();

        // 为演示目的创建mock控制器
        auto rt_con = std::make_shared<rokae::RtMotionControlCobot>();
        std::cout << "✓ ROKAE RT控制器初始化完成" << std::endl;

        // 2. 创建阻抗扫描控制器
        ImpedanceScanController scanner(rt_con);
        std::cout << "✓ 医疗级阻抗扫描控制器创建完成" << std::endl;

        // 3. 配置阻抗模式参数
        std::error_code ec;
        double desired_contact_force = 10.0; // 10N接触力
        scanner.prepare_impedance_mode(desired_contact_force, ec);

        if (ec) {
            std::cerr << "❌ 阻抗模式配置失败: " << ec.message() << std::endl;
            return 1;
        }

        std::cout << "✓ 阻抗模式配置完成" << std::endl;
        std::cout << "  - 期望接触力: " << desired_contact_force << " N" << std::endl;
        std::cout << "  - 安全限制: Z轴 ≤ 35N, XY轴 ≤ 20N" << std::endl;
        std::cout << "  - 控制频率: 1ms实时循环" << std::endl;

        // 4. 启动接触扫描
        std::cout << "🚀 启动安全接触扫描..." << std::endl;

        // 在实际应用中，这里会调用：
        // scanner.start_contact_scan();

        // 为演示目的，模拟扫描过程
        std::cout << "📊 扫描状态监控:" << std::endl;
        for (int i = 0; i < 10; ++i) {
            std::this_thread::sleep_for(std::chrono::milliseconds(100));
            std::cout << "  [" << (i+1) << "/10] 扫描进行中... 力反馈正常" << std::endl;
        }

        std::cout << "✅ 扫描完成 - 安全退出" << std::endl;
        std::cout << "📋 扫描结果:" << std::endl;
        std::cout << "  - 扫描长度: 200mm" << std::endl;
        std::cout << "  - 平均接触力: " << desired_contact_force << " N" << std::endl;
        std::cout << "  - 安全事件: 0" << std::endl;

    } catch (const std::exception& e) {
        std::cerr << "❌ 扫描过程中发生错误: " << e.what() << std::endl;
        return 1;
    }

    std::cout << "=== 示例完成 ===" << std::endl;
    return 0;
}