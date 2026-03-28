# Headless API v1

正式支持环境固定为 Ubuntu 22.04。

正式 headless 适配层固定入口为 `spine_ultrasound_ui.api_server:app`。

## Stability Rules

- `v1` 只允许增量加字段，不允许重命名或删除字段。
- `POST /api/v1/commands/{command}` 对已知命令且请求已送达 runtime 时，始终返回 `ReplyEnvelope` 形状的 HTTP 200。
- 未知命令、payload 缺字段或 payload 不是对象时返回 HTTP 400。
- runtime 连接失败、TLS 失败、协议版本失败时返回 HTTP 502。

## Endpoints

### `GET /api/v1/status`
- 适配层当前 backend mode、命令/遥测 endpoint、execution state、topics 列表。

### `GET /api/v1/telemetry/snapshot`
- 返回主线 telemetry topic 的最近快照列表。
- 每项形状：
  - `topic`
  - `ts_ns`
  - `data`

### `GET /api/v1/schema`
- 自描述合同入口。
- 输出：
  - `api_version`
  - `protocol_version`
  - `transport`
  - `compatibility_policy`
  - `reply_envelope`
  - `commands`
  - `telemetry_topics`
  - `force_control`

### `POST /api/v1/commands/{command}`
- 请求体必须是 JSON object。
- 典型命令：
  - `start_scan`
  - `pause_scan`
  - `resume_scan`
  - `safe_retreat`
  - `emergency_stop`
  - `clear_fault`
  - `lock_session`
  - `load_scan_plan`

`lock_session` 最少字段：
- `session_id`
- `session_dir`
- `config_snapshot`
- `device_roster`
- `scan_plan_hash`

`load_scan_plan` 最少字段：
- `scan_plan.plan_id`
- `scan_plan.segments`

## WebSockets

### `/ws/telemetry`
- 推送单条 JSON telemetry item。
- 形状与 `GET /api/v1/telemetry/snapshot` 中单条记录一致。

### `/ws/camera`
### `/ws/ultrasound`
- 推送 base64 PNG 帧。
- Web 前端应使用统一 `WS_BASE_URL` 配置生成连接地址。

## Force-Control Source of Truth

- 仓库唯一正式阈值源是 `configs/force_control.json`。
- Python schema、mock runtime、C++ safety tests、阻抗默认值都从这份配置读取。
