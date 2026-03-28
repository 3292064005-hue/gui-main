#pragma once

#include <iostream>
#include <array>
#include <atomic>
#include <cmath>
#include <functional>
#include <memory>
#include <chrono>
#include <thread>

// Assuming ROKAE SDK headers are available when compiling against third_party.
// #include "rokae/robot.h"
// #include "rokae/exceptions.h"

// Forward declarations for IDE syntax checking
namespace rokae {
    struct CartesianPosition {
        std::array<double, 16> pos;
        void setFinished() {}
    };
    enum RtSupportedFields { tcpPose_m, tau_ext_m };
    enum RtControllerMode { cartesianImpedance };
    struct Load {
        double mass;
        std::array<double, 3> cog;
        std::array<double, 3> inertia;
    };
    class RtMotionControlCobot {
    public:
        template<typename T> void setEndEffectorFrame(const T&, std::error_code&) {}
        void setLoad(const Load&, std::error_code&) {}
        void setCartesianImpedance(const std::array<double, 6>&, std::error_code&) {}
        void setCartesianImpedanceDesiredTorque(const std::array<double, 6>&, std::error_code&) {}
        void setTorqueFilterCutOffFrequency(double, std::error_code&) {}
        void startReceiveRobotState(std::chrono::milliseconds, const std::vector<RtSupportedFields>&) {}
        void updateRobotState(std::chrono::milliseconds) {}
        template<typename T> void getStateData(RtSupportedFields, T&) {}
        void startMove(RtControllerMode) {}
        void setControlLoop(std::function<CartesianPosition()>, int, bool) {}
        void startLoop(bool) {}
        void stopMove() {}
        void stopReceiveRobotState() {}
    };
    class RealtimeMotionException : public std::exception {
    public:
        const char* what() const noexcept override { return "Realtime motion error"; }
    };
    using error_code = std::error_code;
}

using namespace rokae;

class ImpedanceScanController {
private:
    std::shared_ptr<RtMotionControlCobot> rt_con_;
    std::atomic<bool> is_scanning_{false};

    // 医疗级安全红线 (绝对禁止修改为过大数值)
    const double MAX_Z_FORCE_N = 35.0; // 探头向下压的最大容忍力 35N

public:
    ImpedanceScanController(std::shared_ptr<RtMotionControlCobot> rt_con)
        : rt_con_(rt_con) {}

    /**
     * @brief 阶段一：进入阻抗控制模式前的"最优参数整定"
     * @param desired_force_n 探头贴合患者背部的期望保持力 (如 10N)
     */
    void prepare_impedance_mode(double desired_force_n, error_code& ec) {
        // 1. 【核心细节：物理对齐】设定探头 TCP (必须包含探头长度和耦合剂厚度预估)
        std::array<double, 16> tcp_trans = {
            1, 0, 0, 0,
            0, 1, 0, 0,
            0, 0, 1, 0.18, // 假设探头长 180mm，Z 轴向外延伸
            0, 0, 0, 1
        };
        rt_con_->setEndEffectorFrame(tcp_trans, ec);
        if (ec) return;

        // 2. 【核心细节：真实负载补偿】必须补偿探头重量，否则力控会发生零点漂移
        Load probe_load;
        probe_load.mass = 0.85; // 探头重量 0.85kg
        probe_load.cog = {0.0, 0.0, 0.08}; // 质心偏移
        probe_load.inertia = {0.01, 0.01, 0.01};
        rt_con_->setLoad(probe_load, ec);
        if (ec) return;

        // 3. 【力位混合控制核心】阻抗系数矩阵 (刚度)
        // X/Y 轴刚度极高 (2000)，保证扫查路径不跑偏
        // Z 轴刚度极低 (50)，使其具备弹簧特性，自适应背部起伏
        // Rx/Ry/Rz 刚度适中 (200)，保持探头姿态垂直
        std::array<double, 6> stiffness = {2000.0, 2000.0, 50.0, 200.0, 200.0, 200.0};
        rt_con_->setCartesianImpedance(stiffness, ec);
        if (ec) return;

        // 4. 设置期望恒力 (注意方向：Z 轴正方向是向外，所以压入背部是负值)
        std::array<double, 6> desired_wrench = {0.0, 0.0, -std::abs(desired_force_n), 0.0, 0.0, 0.0};
        rt_con_->setCartesianImpedanceDesiredTorque(desired_wrench, ec);

        // 5. 设置力矩滤波频率 (医疗场景最优解：30Hz，兼顾平滑与响应延迟)
        rt_con_->setTorqueFilterCutOffFrequency(30.0, ec);
    }

    /**
     * @brief 阶段二：执行 1ms 力位混合实时控制与安全熔断
     */
    void start_contact_scan() {
        error_code ec;

        // 1. 订阅必要的高频数据：包含 TCP 位姿和末端受力
        rt_con_->startReceiveRobotState(std::chrono::milliseconds(1), {
            RtSupportedFields::tcpPose_m,
            RtSupportedFields::tau_ext_m // 外部力矩/力反馈
        });

        // 2. 状态对齐：获取起始绝对位姿，防止 startMove 瞬间跳变引发 kInstabilityDetection
        rt_con_->updateRobotState(std::chrono::milliseconds(5));
        std::array<double, 16> initial_pose;
        rt_con_->getStateData(RtSupportedFields::tcpPose_m, initial_pose);

        // 3. 准备启动阻抗控制模式
        rt_con_->startMove(RtControllerMode::cartesianImpedance);

        is_scanning_ = true;
        double time_t = 0.0;
        CartesianPosition target_cmd;
        target_cmd.pos = initial_pose; // 初始指令必须等于当前真实位置

        // 4. 定义 1ms 实时调度回调函数
        std::function<CartesianPosition()> control_loop = [&]() {
            time_t += 0.001;

            // --- [极速力觉熔断器 (Force Circuit Breaker)] ---
            // 实时读取当前受力 (假设 tau_ext_m 包含了转换到笛卡尔的受力)
            // 注：此处需根据实机反馈的字段提取 Z 轴力分量
            std::array<double, 7> ext_tau;
            rt_con_->getStateData(RtSupportedFields::tau_ext_m, ext_tau);

            // 简化的力映射逻辑 (实际中可用 SDK 接口 getEndTorque 或雅可比矩阵解算)
            double current_z_force = calculate_z_force(ext_tau);

            if (std::abs(current_z_force) > MAX_Z_FORCE_N) {
                is_scanning_ = false;
                // 瞬间切断：通过返回 setFinished() 优雅但极速地终止控制流
                target_cmd.setFinished();
                std::cerr << "[EMERGENCY] Force Circuit Breaker Triggered! Z-Force: "
                          << current_z_force << " N" << std::endl;
                return target_cmd;
            }
            // ----------------------------------------------

            // --- [位置规划 (仅干预 X/Y 轴)] ---
            if (is_scanning_) {
                // 示例：沿 Y 轴以 5mm/s 的速度进行匀速直线扫查
                // 注意：由于 Z 轴刚度极低且施加了期望力，Z 轴位置指令即使不变，
                // 探头也会自动紧贴起伏的背部。

                // 仅根据齐次变换矩阵的平移分量进行累加更新 (Y轴为索引 7)
                target_cmd.pos[7] = initial_pose[7] + (0.005 * time_t);

                // 扫查长度限制 (如 200mm)
                if ((0.005 * time_t) >= 0.200) {
                    target_cmd.setFinished();
                    is_scanning_ = false;
                }
            }

            return target_cmd;
        };

        // 5. 将回调函数挂载到 SDK，开启非阻塞实时循环
        rt_con_->setControlLoop(control_loop, 99, true); // priority=99, useStateDataInLoop=true

        try {
            rt_con_->startLoop(true); // 阻塞主线程，直到 target_cmd.setFinished() 被触发
        } catch (const RealtimeMotionException& e) {
            std::cerr << "[FATAL] Realtime Control Interrupted: " << e.what() << std::endl;
        }

        // 清理工作
        rt_con_->stopMove();
        rt_con_->stopReceiveRobotState();
    }

    /**
     * @brief 检查扫描是否正在进行
     */
    bool is_scanning() const { return is_scanning_.load(); }

    /**
     * @brief 停止扫描
     */
    void stop_scan() {
        is_scanning_ = false;
    }

private:
    double calculate_z_force(const std::array<double, 7>& tau) {
        // 在实机中，如果没有直接的 cartesianForce 字段，
        // 需要通过 model_->jacobian() 和外力矩 tau 逆解出笛卡尔力 F = (J^T)^-1 * tau
        // 为保证代码跑通，此处假设 tau[2] 为近似受力（实际联调时替换为真实的笛卡尔 Z 轴力获取函数）
        return tau[2];
    }
};