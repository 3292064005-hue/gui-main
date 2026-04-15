# Recording / Telemetry Consumer Map

本文件定义 `RecordingService` 的统一事件时间轴与消费者映射，避免“有生产无消费”与“多 JSONL 各自对时”的长期漂移。

## Stream Layout

所有录制主链统一写入 `raw/core/`：

- `robot_state.jsonl`
- `contact_state.jsonl`
- `scan_progress.jsonl`
- `alarm_event.jsonl`
- `event_timeline.jsonl`
- `recording_manifest.json`

## Producer Semantics

- `recordRobotState()` → `robot_state` + `event_timeline`
- `recordContactState()` → `contact_state` + `event_timeline`
- `recordScanProgress()` → `scan_progress` + `event_timeline`
- `recordAlarm()` → `alarm_event` + `event_timeline`

## Consumer Map

`recording_manifest.json` 作为运行时消费者说明：

- `telemetry_replay` 消费：`robot_state`, `contact_state`, `scan_progress`
- `alarm_review` 消费：`alarm_event`, `event_timeline`
- `audit_timeline` 消费：`event_timeline`

## Boundary Rule

- 高频路径只能入队，不能同步落盘。
- 单独流文件继续保留，避免破坏现有调用方。
- `event_timeline.jsonl` 作为跨流统一时序基线。


## 实际消费闭环输出

关闭 session 时，`RecordingService` 会实际消费 raw 流并生成：

- `derived/core/telemetry_replay_index.json`
- `derived/core/alarm_review_index.json`
- `derived/core/audit_timeline_index.json`

这些文件不是说明性文档，而是消费者可直接读取的落地产物。
