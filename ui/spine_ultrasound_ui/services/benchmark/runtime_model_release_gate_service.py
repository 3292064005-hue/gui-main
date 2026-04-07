from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text


class RuntimeModelReleaseGateService:
    """Validate exported runtime packages against benchmark thresholds."""

    def evaluate(self, *, runtime_meta: dict[str, Any], benchmark_manifest_path: str | Path, thresholds: dict[str, Any], required_release_state: str = '') -> dict[str, Any]:
        benchmark_path = Path(benchmark_manifest_path)
        if not benchmark_path.exists():
            raise FileNotFoundError(benchmark_path)
        manifest = json.loads(benchmark_path.read_text(encoding='utf-8'))
        summary = dict(manifest.get('summary', {}) or {})
        mean_error = float(summary.get('mean_error_px', float('inf')))
        max_error = float(summary.get('max_error_px', float('inf')))
        detection_rate = float(summary.get('detection_rate', 0.0))
        stable_detection_rate = float(summary.get('stable_detection_rate', 0.0))
        checks = {
            'mean_error_px': mean_error <= float(thresholds.get('max_mean_error_px', float('inf'))),
            'max_error_px': max_error <= float(thresholds.get('max_max_error_px', float('inf'))),
            'detection_rate': detection_rate >= float(thresholds.get('min_detection_rate', 0.0)),
            'stable_detection_rate': stable_detection_rate >= float(thresholds.get('min_stable_detection_rate', 0.0)),
        }
        release_ok = True
        if required_release_state:
            release_ok = str(runtime_meta.get('release_state', '') or '') == str(required_release_state)
            checks['release_state'] = release_ok
        failures = [name for name, passed in checks.items() if not bool(passed)]
        return {
            'generated_at': now_text(),
            'passed': not failures,
            'failures': failures,
            'benchmark_manifest_path': str(benchmark_path),
            'thresholds': dict(thresholds),
            'summary': summary,
        }
