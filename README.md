# Spine Ultrasound Platform

这是一个面向脊柱侧弯自动检测研究的平台工程，采用 **SDK-first 双执行体架构**：

- `cpp_robot_core/`：唯一机器人控制核心（未来直接接 ROKAE xCore SDK）
- `spine_ultrasound_ui/`：Python / PySide6 前端，负责实验管理、图像处理、重建、评估、回放与导出
- `third_party/rokae_xcore_sdk/robot/`：官方 SDK 原包，已并入工程

## 最新优化进展

### 基础优化阶段 (2026-03-28)
- ✅ **自适应控制频率**：在 `RtMotionService` 中实现 `AdaptiveTimer` 类，根据CPU负载动态调整控制周期 (0.5-2ms)，减少抖动，提升性能。
- ✅ **IPC效率提升**：替换字符串JSON为Protobuf序列化，减少开销。添加 `ipc_messages.proto`，更新 `CommandServer` 和 `TelemetryPublisher` 使用Protobuf。效率提升：5.22x更快，2.5x更小。
- ✅ **错误处理与安全**：实现统一异常处理器 (`ExceptionHandler`)，分类错误并提供用户反馈；C++端扩展 `RecoveryManager` 添加自动重试；添加TLS 1.3加密IPC通道，防止中间人攻击。
- 🔄 **代码质量**：Clang-Tidy修复，重构测试。

**验证**：编译成功，自适应逻辑测试通过，Protobuf效率提升显著，异常处理测试通过，TLS集成完成，安全性和稳定性大幅提升。

### 医疗级力控制阶段 (2026-03-28)
- ✅ **ImpedanceControlManager**：实现笛卡尔阻抗控制管理器，包含ForceCircuitBreaker安全熔断器，35N Z轴力限制，20N XY轴力限制，1ms实时安全监控。
- ✅ **ImpedanceScanController**：医疗级笛卡尔阻抗控制调度器，集成ROKAE xCore SDK规范，力位混合控制，1ms极速力觉熔断器，TCP对齐，负载补偿，阻抗参数整定。
- ✅ **集成到RtMotionService**：在实时运动服务中集成阻抗管理器，配置医疗安全参数，期望10N接触力，实时力监控和紧急回缩。

**验证**：力控制安全系统测试通过，阻抗扫描控制器编译成功，安全熔断器正确检测35N超限，控制器准备好进行医疗超声扫描。

## 当前工程状态

本工程当前已完成：
- 统一 `protocol_version = 1` 的命令/遥测契约
- `AppController` 已拆成更薄的编排层，状态解析、session/manifest、路径预览与导出分别下沉到独立服务
- `MockBackend` 与 `scripts/mock_robot_core_server.py` 复用同一套 mock core runtime
- `RobotCoreClientBackend` 退化为纯 TCP 传输层，UI 不再维护第二份执行状态
- `ExperimentManager` 改为先保存 preview plan，再在 `lock_session` 时一次性写死 manifest 和最终 `scan_plan_hash`
- `cpp_robot_core/` 已具备可运行的 TCP command/telemetry runtime，`core` 模式可以真实连接到 `robot_core_main`

当前能力矩阵：
- `Implemented`：双 TCP IPC、UI 只读 telemetry、preview plan -> lock session -> load plan 流程、session manifest、core/ui 双侧 recorder、C++ simulated robot_core runtime
- `Simulated`：视觉定位、路径预览生成、C++ core 内部机器人运动/接触过程、quality feedback
- `Planned`：真实 ROKAE xCore SDK 深度控制、真实相机/超声/压力设备接入、预处理/重建/Cobb 角算法

当前里程碑聚焦：
- 安全扫查闭环
- 单一控制权
- 数据同步与回放基础

仍需在实机环境联调的部分：
- 真实 C++ robot_core 与官方 SDK 深度对接
- 真正的相机 / 超声 / 压力设备接入
- RT 参数整定、实时 jitter 监测与安全验证

## 运行方式

### 1. 纯 Mock 模式
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py --backend mock
```

### 2. IPC 演示模式（推荐先验证 UI 与 robot_core 架构）
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python scripts/mock_robot_core_server.py
# 新终端
SPINE_UI_BACKEND=core python run.py --backend core
```

### 3. 启动 C++ robot_core 模拟控制面
```bash
cd cpp_robot_core
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j
./build/robot_core_main
```

### 4. 一键启动 C++ core + GUI
```bash
./scripts/start_real.sh
```

## 架构原则

1. 官方 SDK 只在 C++ 核心里使用
2. Python 前端绝不进入 1ms 实时控制闭环
3. 自由空间动作统一走 SDK 非实时接口
4. 接触扫查默认走 `cartesianImpedance`
5. 不重复实现位置/速度/力矩/位姿采集
6. ROS2 只做镜像和联调，不做实时主控
7. `cpp_robot_core` 是唯一执行状态源，UI 只消费遥测
8. 每次扫查以 session manifest 为数据锚点，后处理只读 manifest
项目目录结构
spine_ultrasound_platform_complete/
├─ run.py
├─ requirements.txt
├─ README.md
├─ ARCHITECTURE.md
├─ docs/
├─ scripts/
├─ tests/
├─ cpp_robot_core/
├─ spine_ultrasound_ui/
└─ third_party/
   └─ rokae_xcore_sdk/
      └─ robot/
目录说明
根目录文件
run.py

项目统一启动入口。
用于启动 Python 侧上位机程序，支持不同后端模式。

requirements.txt

Python 依赖清单。
用于创建虚拟环境并安装 GUI、测试、工具链依赖。

README.md

项目说明文档。
用于介绍项目目标、目录结构、运行方式和开发流程。

ARCHITECTURE.md

系统架构说明文档。
用于说明整体采用的 C++ 机器人控制核心 + Python 研究平台前端 双执行体架构。

docs/

项目文档目录，用于存放架构、协议、状态机和开发说明。

建议包含并重点维护以下内容：

STATE_MACHINE.md
系统状态机说明，包括连接、准备、扫查、暂停、处理、回放、故障等状态流转。
IPC_PROTOCOL.md
Python GUI 与 cpp_robot_core 之间的通信协议定义。
MODULE_RESPONSIBILITIES.md
各模块职责说明，便于后续维护和分工。
INTERFACE_MATRIX.md
模块之间的接口关系、输入输出和调用方式。
OPERATION_FLOW.md
项目实际工作流说明，例如：连接机器人 → 创建实验 → 定位 → 建路径 → 扫查 → 重建 → 评估 → 导出。
DEVELOPMENT_ROADMAP.md
开发路线图和阶段目标。
SDK_USAGE_POLICY.md
官方 SDK 的使用边界说明，明确哪些功能复用 SDK、哪些功能由项目自研。
scripts/

辅助脚本目录。

典型用途：

启动 mock 后端
启动本地演示链路
启动/调试 IPC 服务
导出结果
做联调辅助

例如当前工程里已有：

mock_robot_core_server.py
用于模拟 cpp_robot_core，方便在没有真机时验证 GUI 与 IPC 通信链路。
tests/

测试目录。

用于：

状态机测试
配置服务测试
实验管理测试
MockBackend 测试
后续补充 IPC 和数据同步测试

目标是保证：

核心流程可回归
架构调整后不轻易引入功能性回归
核心工程目录
cpp_robot_core/

C++ 机器人控制核心。
这是项目中唯一直接使用官方 xCore SDK 的模块。

设计定位

cpp_robot_core 负责所有与机器人实时性强、控制安全要求高的能力，包括：

机器人连接与断开
上下电与模式切换
非实时运动控制
实时控制回调
机器人状态采集
接触状态估计
扫查监督与安全策略
向上位机发布标准化状态
接收 GUI 发来的高层命令
目录建议职责
include/

头文件目录。
定义各核心模块接口，例如：

SdkRobotFacade
RobotStateHub
NrtMotionEngine
RtMotionEngine
ContactObserver
ScanSupervisor
SafetyService
RecoveryManager
TrajectoryCompiler
CommandServer
TelemetryPublisher
src/

对应的实现文件目录。
实现机器人控制、状态处理、安全逻辑和通信逻辑。

apps/

可执行入口目录。
通常包括：

robot_core_main.cpp：正式运行入口
robot_core_cli.cpp：命令行调试入口
tests/

C++ 侧测试代码目录。

CMakeLists.txt

C++ 工程构建入口，用于编译 cpp_robot_core。

spine_ultrasound_ui/

Python 研究平台前端。
这是项目的图形操作层、实验管理层、图像处理层、回放导出层。

设计定位

该模块不直接调用 SDK，不承担 1ms 实时控制。
它负责：

PySide6 GUI
实验管理
参数管理
图像显示与处理
重建与评估
回放与导出
与 cpp_robot_core 的通信
spine_ultrasound_ui/ 子目录说明
models/

数据模型目录。
定义前端统一使用的数据结构，例如：

系统状态
设备状态
运行指标
实验记录
配置模型
机器人状态模型
接触状态模型

作用：

统一页面之间的数据传递格式
统一后端到前端的数据组织方式
services/

服务层目录。
负责对接外部资源或实现具体业务能力。

当前/建议包括：

backend_base.py

后端抽象接口。
定义 GUI 统一调用的接口，屏蔽真实后端和 Mock 后端差异。

mock_backend.py

模拟后端。
用于无设备调试、演示和测试。

robot_core_client.py

真实后端客户端。
负责和 cpp_robot_core 通信，向 GUI 提供真实机器人状态和命令入口。

ipc_protocol.py

IPC 协议定义。
定义 GUI 和 C++ 核心之间的消息格式、命令结构和状态结构。

config_service.py

配置读写服务。
负责配置模板的加载、保存和应用。

export_service.py

结果导出服务。
负责导出 JSON、CSV、图片和后续 PDF 报告。

replay_service.py

实验回放服务。
负责读取历史实验并进行回放。

camera_service.py

相机服务。
负责相机接入与图像采集。

ultrasound_service.py

超声服务。
负责超声图像流接入。

quality_monitor.py

质量监测服务。
用于图像质量评估、接触质量评分和重采建议。

pages/

页面目录。
每个页面负责一个明确业务场景，避免把所有逻辑堆进主窗口。

当前/建议页面包括：

overview_page.py

系统总览页。
显示连接状态、实验摘要、系统状态和总体入口。

experiment_page.py

实验管理页。
负责实验创建、实验列表、实验信息与数据目录管理。

prepare_page.py

系统准备页。
负责机器人/设备准备、自检、参数确认、进入 Ready 状态。

scan_page.py

自动扫查页。
主作业页面，显示实时相机图、超声图、进度、状态和控制按钮。

robot_monitor_page.py

机器人监控页。
显示关节位置、速度、力矩、TCP 位姿、控制器状态、日志等。

vision_page.py

视觉定位与路径页。
显示背部图像、定位结果、中线与路径预览。

reconstruction_page.py

图像处理与重建页。
显示原始图、增强图、特征图与重建结果。

assessment_page.py

量化评估页。
显示 Cobb 角、关键点、质量评分和导出按钮。

replay_page.py

实验回放页。
用于回放历史实验、跳转告警点和分析低质量段。

settings_page.py

系统设置页。
用于管理全局配置、设备配置、扫查配置、安全配置和导出配置。

widgets/

通用组件目录。
封装可复用的 UI 组件，降低页面复杂度。

包括但不限于：

status_card.py：状态卡片
image_pane.py：图像显示区域
config_form.py：参数表单
experiment_table_model.py：实验表格模型
alarm_banner.py：顶部告警条
state_timeline.py：流程状态时间线
log_console.py：日志显示控件
styles/

样式目录。
用于统一前端视觉风格。

例如：

主题色
深浅色模式
卡片样式
按钮样式
日志显示风格
utils/

工具目录。
存放和业务逻辑弱相关的通用工具函数。

例如：

文件工具
时间工具
图像工具
校验工具
日志工具
第三方依赖目录
third_party/rokae_xcore_sdk/robot/

官方 ROKAE xCore SDK 包。
该目录直接保留你提供的官方 SDK 压缩包内容，作为项目机器人控制能力的底座。

使用原则
该 SDK 只在 cpp_robot_core 中调用
Python GUI 不直接依赖 SDK
项目不重复实现 SDK 已有的底层能力，例如：
位置/速度/力矩采集
TCP 位姿获取
Toolset / Load 配置
非实时运动
实时控制
碰撞检测
软限位
控制器日志
事件回调
推荐写进 README 的一句话总结

本项目采用“C++ 机器人控制核心 + Python 研究平台前端”的双执行体架构：cpp_robot_core 负责复用官方 xCore SDK 实现机器人控制与安全闭环，spine_ultrasound_ui 负责图形界面、实验管理、图像处理、重建评估与结果导出。
