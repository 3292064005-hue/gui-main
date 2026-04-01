# xCore SDK 对齐优化框架

## 目标
把当前项目从“可演示 UI + 自定义后端”收口为“以 xCore SDK(C++) 为唯一机器人控制主线的临床研究工作站”。

## 设计原则
- Python / UI 不进入 1 kHz 回调
- C++ 持有唯一实时控制权
- 单控制源，不与 RobotAssist 并行抢控制
- 扫查主线固定为：NRT 接近 -> RT 笛卡尔阻抗接触 -> RT 笛卡尔阻抗扫查 -> 安全退让
- directTorque 仅保留给研究模式，不进入临床主线

## 模块分层

### 1. SDK 适配层（C++）
职责：
- `connectToRobot`, `setPowerState`, `setOperateMode`
- `setMotionControlMode`, `moveAppend`, `moveStart`, `stop`
- `startReceiveRobotState`, `setControlLoop`, `startLoop`, `startMove`, `stopMove`
- `setCartesianImpedance`, `setLoad`, `setEndEffectorFrame`, `setNetworkTolerance`
- `queryControllerLog`, `enableCollisionDetection`, `setSoftLimit`
- `getDI/DO/AI/AO`, `readRegister/writeRegister`
- `projectInfo/loadProject/runProject`
- `enableDrag/replayPath/queryPathLists`

### 2. 运行时治理层（C++ core_runtime）
职责：
- 状态机
- 安全联锁
- 会话锁定
- 路径加载与执行监督
- 告警上报
- 恢复策略

### 3. 协议层（TLS/Protobuf）
职责：
- UI 与 core 之间的命令/状态解耦
- 避免 UI 直接依赖 SDK 细节
- 为 headless / kiosk / web 提供统一入口

### 4. 桌面治理层（Python UI）
职责：
- 配置编辑
- 主线对齐检查
- 会话与数据治理
- 医疗流程引导
- 结果可视化

## SDK 主线
1. `connectToRobot(remoteIP, localIP)`
2. `setPowerState(on)`
3. `setOperateMode(auto)`
4. `setMotionControlMode(NRT)`
5. `MoveAbsJ/MoveJ/MoveL` 执行接近
6. `setMotionControlMode(RT)`
7. `startReceiveRobotState(1ms, fields)`
8. `setLoad + setEndEffectorFrame + setCartesianImpedance + setNetworkTolerance`
9. `startMove(cartesianImpedance)`
10. `setControlLoop(...) + startLoop(...)`

## 当前已落地
- SDK 能力矩阵与主线对齐检查
- UI 配置页补齐 Robot class / axis / IP / link / RT mode / filter / tolerance / tool / TCP / load
- 将碰撞检测、软限位、奇异规避、RL project/task、xPanel 输出模式纳入正式配置项
- 启动扫查前强制执行 SDK blocker 检查与 model precheck 阻塞检查
- 设置页与系统准备页展示 SDK 对齐状态、命令映射和主线顺序
- 新增 `SdkRuntimeAssetService` 聚合 controller log、RL 工程、路径库、I/O、安全配置和 motion contract
- 新增 `XMateModelService` 输出路径包络、连续性、执行 profile 选择与近似 DH 前检报告
- 机器人监控页与实验回放页已可显示 RL/drag/path/I/O 等 SDK 资产摘要

## 下一阶段建议
- 将 `SdkRobotFacade` 从 mock 过渡到真实 `rokae::xMateRobot`
- 将 `queryControllerLog` / `projectInfo` / `queryPathLists` / `readRegister` 等命令接入真实 core-side facade
- 将真实 `xMateModel` 的 FK/IK/Jacobian/动力学结果替换近似前检服务
- 把 `Planner` 的 S 曲线结果与扫描预览统一到同一 execution candidate 选择链
- 将碰撞检测、软限位、奇异规避参数写入 session manifest 作为冻结安全合同
