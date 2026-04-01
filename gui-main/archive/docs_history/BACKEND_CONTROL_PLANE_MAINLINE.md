# Backend Control Plane Mainline

## Goal

把“前后端能连通”升级成“前后端控制面一致”。

正式主线不只检查：

- REST / TLS / WebSocket 是否在线
- telemetry 是否持续更新

还要同时检查：

- 前端运行配置与后端运行配置是否一致
- 控制面协议版本是否一致
- 必需 telemetry topic 是否覆盖完整
- 最近命令窗口是否存在失败和退化

## Control Plane Contract

Headless adapter 统一提供：

- `/api/v1/control-plane`
- `/api/v1/commands/recent`

其中 `control-plane` 聚合：

- `status`
- `health`
- `schema`
- `runtime_config`
- `topics`
- `recent_commands`

## Desktop-side Governance

桌面端使用 `BackendControlPlaneService` 生成正式摘要：

- `protocol_status`
- `config_sync`
- `topic_coverage`
- `command_window`
- `blockers / warnings`

这些结果进入：

- `BackendLinkService`
- readiness
- 启动前检查
- 机器人监控页
- 系统设置页
- 治理快照导出

## Release Gates

正式启动扫查前，前后端互联必须同时满足：

1. 链路在线
2. 协议一致
3. 前后端运行配置一致
4. 必需 topic 覆盖完整或可接受降级
5. 最近命令窗口无阻塞性失败

## Why this matters

仅靠 link alive 不足以证明系统可用。真正导致误启动和返工的问题通常是：

- UI 参数已经改了，但 headless / robot_core 仍在跑旧配置
- command/reply 协议版本漂移
- topic catalog 缺关键状态，导致 readiness 误判
- 最近命令窗口已经退化，但界面仍显示“在线”

这一层补上之后，前后端互联从“连接成功”提升为“控制面一致”。
