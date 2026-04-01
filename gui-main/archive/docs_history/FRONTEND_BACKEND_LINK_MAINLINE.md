# Frontend-backend link mainline

## Goal

把桌面前端与 backend 的互联固定为正式工程主线，而不是继续依赖“桌面直接内嵌 mock”这一种开发形态。

## Supported link modes

1. `mock`
   - 桌面内嵌 `MockCoreRuntime`
   - 用于 UI 验证和产品流程演示

2. `core`
   - 桌面直接连 `robot_core`
   - 传输协议：TLS 1.3 + length-prefixed Protobuf
   - 适合本机集成调试

3. `api`
   - 桌面通过 `FastAPI` + `WebSocket` 连接 `HeadlessAdapter`
   - 命令：`/api/v1/commands/{command}`
   - 遥测：`/ws/telemetry`
   - 图像流：`/ws/camera`、`/ws/ultrasound`
   - 运行配置：`/api/v1/runtime-config`

## Mainline components

- `ApiBridgeBackend`
  - UI 侧 bridge backend
  - 负责 HTTP 命令、WebSocket 遥测和媒体流接收、链路状态缓存

- `HeadlessAdapter`
  - backend 统一接入面
  - 负责 mock/core 两类 runtime 的统一协议包装

- `BackendLinkService`
  - 聚合 REST reachability、telemetry freshness、camera/ultrasound 连接状态、命令成功率、reconnect 统计
  - 输出 blocker / warning / summary_label

## Release criteria

前后端互联进入正式可启动状态时，至少满足：

- REST 网关可达
- adapter 处于运行态
- telemetry 已连通
- telemetry 未 stale
- 命令成功率无持续下降
- UI readiness 中的“前后端链路在线”检查通过

## UI surfaces

- `系统总览`：展示链路 summary、命令成功率、telemetry 状态
- `系统准备`：把链路状态纳入启动前检查摘要
- `机器人监控`：展示 endpoint、media stream、reconnect 和链路说明
- `系统设置`：展示链路状态、流状态和当前 backend 入口
