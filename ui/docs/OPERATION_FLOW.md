# Operation Flow

## Operator mainline
1. Connect robot
2. Power on
3. Enter auto mode
4. Create experiment
5. Run localization
6. Generate preview path
7. Lock session
8. Load scan plan
9. Approach / seek contact / start scan
10. Pause / resume / retreat if required
11. Save results
12. Export summary
13. Refresh session products
14. Review report / replay / quality / alarms / qa-pack

## Data products generated on the mainline
- `export/summary.json`
- `export/summary.txt`
- `export/session_report.json`
- `export/session_compare.json`
- `export/qa_pack.json`
- `derived/quality/quality_timeline.json`
- `derived/alarms/alarm_timeline.json`
- `replay/replay_index.json`
- `raw/ui/command_journal.jsonl`
- `derived/training_bridge/model_ready_input_index.json`
- `derived/reconstruction/prior_assisted_curve.json` (optional sidecar)
- `derived/assessment/prior_assisted_cobb.json` (optional sidecar)

## Failure semantics
- pre-lock failure: reject without session mutation
- lock failure: rollback pending local session
- scan-step failure: raise alarm and request safe retreat
- fatal runtime failure: converge to fault/estop semantics

## Closure semantics
- `weighted_runtime` may emit degraded or prior-assisted outputs. Prior-assisted payloads are written to dedicated sidecars, while canonical `spine_curve.json` and `cobb_measurement.json` become authoritative placeholders rather than contaminated data carriers.
- `preweight_deterministic` accepts only measured authoritative rows and fail-closes when measured evidence is insufficient.
- `export/session_report.json`, `derived/reconstruction/reconstruction_summary.json`, and `derived/assessment/assessment_summary.json` expose `closure_verdict`, `provenance_purity`, `hard_blockers`, `soft_review_reasons`, `profile_config_path`, and `profile_load_error`.
