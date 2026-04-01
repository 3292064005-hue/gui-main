# Bridge Observability Mainline

## Goal

前后端互联不再只验证“能连上”。正式主线还必须验证前端**真的观测到了**后端 runtime 的关键 topic、关键执行态与关键命令结果。

## Scope

`BridgeObservabilityService` 负责三类检查：

1. **Telemetry freshness**
   - `core_state`
   - `robot_state`
   - `safety_status`
   - `contact_state`
   - `scan_progress`
   - `quality_feedback`（推荐项）

2. **State consistency**
   - 执行态进入正式路径后，会话必须已锁定
   - 执行态进入正式路径后，机器人必须已上电
   - 扫查相关执行态必须处于自动模式
   - `SCANNING / CONTACT_STABLE / PAUSED_HOLD` 必须满足 `safe_to_scan`

3. **Command observability**
   - 不是只看命令 reply `ok=true`
   - 还要检查最近关键命令是否在前端观测面上得到状态确认
   - 例如：
     - `power_on -> powered=true`
     - `set_auto_mode -> operate_mode=automatic`
     - `start_scan -> execution_state in {SCANNING, PAUSED_HOLD, SCAN_COMPLETE}`

## Launch gate

`AppController.start_scan()` 现在除了已有的：

- config baseline
- model precheck
- SDK alignment
- backend link

还会额外阻塞：

- **bridge observability blocked**

也就是：

- topic 太旧
- 执行态与锁定态不一致
- 最近关键命令没有被前端观测确认

这三类问题都会阻止正式启动扫查。

## UI surfacing

以下页面统一展示桥接观测摘要：

- 系统总览
- 系统准备
- 机器人监控
- 实验回放
- 系统设置

## Contract rule

**Declared capability is not enough. Observed runtime evidence is required.**
