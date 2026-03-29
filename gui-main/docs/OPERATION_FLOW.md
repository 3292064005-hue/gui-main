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

## Failure semantics
- pre-lock failure: reject without session mutation
- lock failure: rollback pending local session
- scan-step failure: raise alarm and request safe retreat
- fatal runtime failure: converge to fault/estop semantics
