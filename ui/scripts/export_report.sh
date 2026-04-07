#!/usr/bin/env bash
set -euo pipefail

if [[ $# -lt 1 ]]; then
  echo "Usage: $0 <session_dir> [output_txt]" >&2
  exit 1
fi

SESSION_DIR="$1"
OUTPUT="${2:-$SESSION_DIR/export/summary.txt}"

python - "$SESSION_DIR" "$OUTPUT" <<'PY'
import json
import sys
from pathlib import Path

session_dir = Path(sys.argv[1])
output = Path(sys.argv[2])
manifest_path = session_dir / 'meta' / 'manifest.json'
summary_path = session_dir / 'export' / 'summary.json'
report_path = session_dir / 'export' / 'session_report.json'

if not manifest_path.exists():
    raise SystemExit(f"manifest not found: {manifest_path}")
manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
summary = json.loads(summary_path.read_text(encoding='utf-8')) if summary_path.exists() else {}
report = json.loads(report_path.read_text(encoding='utf-8')) if report_path.exists() else {}

lines = [
    'Spine Ultrasound Session Summary',
    '=' * 32,
    f"Experiment: {manifest.get('experiment_id', '-')}",
    f"Session: {manifest.get('session_id', '-')}",
    f"Software: {manifest.get('software_version', '-')} ({manifest.get('build_id', '-')})",
    f"Planner: {manifest.get('planner_version', '-')}",
    f"Registration: {manifest.get('registration_version', '-')}",
    f"Protocol: {manifest.get('protocol_version', '-')}",
    f"Plan hash: {manifest.get('scan_plan_hash', '-')}",
]
metrics = summary.get('metrics', {})
if metrics:
    lines.extend([
        '',
        'Metrics',
        '-' * 7,
        f"Pressure: {metrics.get('pressure_current', 0.0)} / {metrics.get('pressure_target', 0.0)} N",
        f"Contact: {metrics.get('contact_mode', '-')} ({metrics.get('contact_confidence', 0.0)})",
        f"Progress: {metrics.get('scan_progress', 0.0)}%",
        f"Quality: {metrics.get('quality_score', 0.0)}",
    ])
quality = report.get('quality_summary', {})
if quality:
    lines.extend([
        '',
        'Quality Summary',
        '-' * 15,
        f"Average quality: {quality.get('avg_quality_score', 0.0)}",
        f"Coverage ratio: {quality.get('coverage_ratio', 0.0)}",
        f"Usable sync ratio: {quality.get('usable_sync_ratio', 0.0)}",
    ])
output.parent.mkdir(parents=True, exist_ok=True)
output.write_text('\n'.join(lines) + '\n', encoding='utf-8')
print(output)
PY
