# Headless API v1

## Scope
- Web/Product shell 只消费同一 adapter 暴露的 REST/WS 视图
- 不引入第二执行状态机
- 不改变既有 v1 字段语义，只做增量扩展

## Read-only endpoints
- `GET /api/v1/status`
- `GET /api/v1/health`
- `GET /api/v1/telemetry/snapshot?topics=`
- `GET /api/v1/schema`
- `GET /api/v1/schema/artifacts`
- `GET /api/v1/sessions/current`
- `GET /api/v1/sessions/current/report`
- `GET /api/v1/sessions/current/replay`
- `GET /api/v1/sessions/current/quality`
- `GET /api/v1/sessions/current/alarms`
- `GET /api/v1/sessions/current/artifacts`
- `GET /api/v1/sessions/current/compare`
- `GET /api/v1/sessions/current/trends`
- `GET /api/v1/sessions/current/diagnostics`
- `GET /api/v1/sessions/current/annotations`
- `GET /api/v1/sessions/current/qa-pack`

## Write endpoint
- `POST /api/v1/commands/{command}`
  - 在 `SPINE_READ_ONLY_MODE=1` 时统一拒绝

## WebSocket
- `GET /ws/telemetry?topics=`
  - 不传 `topics` 时默认全量 topics
- `GET /ws/camera`
- `GET /ws/ultrasound`

## Session product contracts
固定主线资产：
- `meta/manifest.json`
- `export/summary.json`
- `export/summary.txt`
- `export/session_report.json`
- `export/session_compare.json`
- `export/session_trends.json`
- `export/diagnostics_pack.json`
- `export/qa_pack.json`
- `derived/quality/quality_timeline.json`
- `derived/alarms/alarm_timeline.json`
- `replay/replay_index.json`
- `raw/ui/command_journal.jsonl`
- `raw/ui/annotations.jsonl`

## Notes
- 前端不得自行生成正式 `session_id`
- 前端状态只能来自 `health/current-session/telemetry`
- artifact registry 现在带 `artifact_id / checksum / schema / created_at`


## Additional Read-only Endpoints

- `GET /api/v1/sessions/current/readiness` — returns the frozen device readiness snapshot written at session lock.
- `GET /api/v1/sessions/current/diagnostics` — returns the structured diagnostics pack with recovery, artifact, alarm, and version digests.
- `GET /api/v1/sessions/current/trends` — returns fleet/session trend deltas for the active session.
