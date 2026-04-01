# IPC Protocol

正式支持环境固定为 Ubuntu 22.04。

本工程采用本机双通道 IPC，正式协议统一为 TLS 1.3 + length-prefixed Protobuf：

- Command Channel: request/reply, default `127.0.0.1:5656`
- Telemetry Channel: fanout stream, default `127.0.0.1:5657`
- All envelopes include `protocol_version = 1`
- Python `RobotCoreClientBackend`、C++ `CommandServer`、`scripts/mock_robot_core_server.py` 必须共用同一协议定义
- Headless/Web 公开面通过 `GET /api/v1/schema` 暴露同一份命令与遥测合同

## 1. Protobuf Messages

### Command
- `protocol_version: int32`
- `command: string`
- `payload_json: string`
- `request_id: string`

### Reply
- `protocol_version: int32`
- `ok: bool`
- `message: string`
- `request_id: string`
- `data_json: string`

### TelemetryEnvelope
- `protocol_version: int32`
- `topic: string`
- `ts_ns: int64`
- `data_json: string`

说明：
- 传输层不再使用 JSON 行协议。
- `payload_json` / `data_json` 作为 protobuf 内部承载的对象型 JSON 字符串，用于保持 UI 与 runtime 的 payload 形状稳定。

## 2. Commands

- `connect_robot`
- `disconnect_robot`
- `power_on`
- `power_off`
- `set_auto_mode`
- `set_manual_mode`
- `validate_setup`
- `lock_session`
- `load_scan_plan`
- `approach_prescan`
- `seek_contact`
- `start_scan`
- `pause_scan`
- `resume_scan`
- `safe_retreat`
- `go_home`
- `clear_fault`
- `emergency_stop`

`lock_session` payload 至少包含：
- `experiment_id`
- `session_id`
- `session_dir`
- `config_snapshot`
- `device_roster`
- `software_version`
- `build_id`
- `scan_plan_hash`

`load_scan_plan` payload 包含完整 `scan_plan` 对象。

`GET /api/v1/schema` 会把命令必填字段、状态前置条件、telemetry topic 核心字段和 `configs/force_control.json` 中的正式力控阈值一起公开出来，供 `ui_frontend`、文档和回归测试复用。

## 3. Topics

### `core_state`
- `execution_state`
- `armed`
- `fault_code`
- `active_segment`
- `progress_pct`
- `session_id`

### `robot_state`
- `powered`
- `operate_mode`
- `joint_pos`
- `joint_vel`
- `joint_torque`
- `cart_force`
- `tcp_pose`
- `last_event`
- `last_controller_log`

### `contact_state`
- `mode`
- `confidence`
- `pressure_current`
- `recommended_action`

### `scan_progress`
- `active_segment`
- `path_index`
- `overall_progress`
- `frame_id`

### `device_health`
- `devices`

### `safety_status`
- `safe_to_arm`
- `safe_to_scan`
- `active_interlocks`

### `recording_status`
- `session_id`
- `recording`
- `dropped_samples`
- `last_flush_ns`

### `quality_feedback`
- `image_quality`
- `feature_confidence`
- `quality_score`
- `need_resample`

### `alarm_event`
- `severity`
- `source`
- `message`
- `session_id`
- `segment_id`
- `event_ts_ns`
