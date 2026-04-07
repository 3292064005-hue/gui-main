from __future__ import annotations

import json
from pathlib import Path
from statistics import mean, pstdev
from typing import Any

from spine_ultrasound_ui.utils import now_text


class PressureAnalysisService:
    """Build pressure-sensor storage views and derived analytics for a session."""

    def build_timeline(self, session_dir: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        pressure_entries = self._read_jsonl(session_dir / 'raw' / 'pressure' / 'samples.jsonl')
        contact_entries = self._read_jsonl(session_dir / 'raw' / 'core' / 'contact_state.jsonl')
        rows: list[dict[str, Any]] = []
        source_entries = pressure_entries or contact_entries
        pressure_upper = float(manifest.get('config_snapshot', {}).get('pressure_upper', 0.0) or 0.0)
        pressure_lower = float(manifest.get('config_snapshot', {}).get('pressure_lower', 0.0) or 0.0)
        pressure_target = float(manifest.get('config_snapshot', {}).get('pressure_target', 0.0) or 0.0)
        stale_threshold_ms = int(manifest.get('safety_thresholds', {}).get('stale_telemetry_ms', 250) or 250)
        last_ts = 0
        for entry in source_entries:
            payload = dict(entry.get('data', {}))
            ts_ns = int(entry.get('source_ts_ns', 0) or entry.get('monotonic_ns', 0))
            current = float(payload.get('pressure_current', payload.get('pressure_n', 0.0)) or 0.0)
            desired = float(payload.get('desired_force_n', pressure_target) or pressure_target)
            confidence = float(payload.get('contact_confidence', payload.get('confidence', 0.0)) or 0.0)
            status = str(payload.get('force_status', payload.get('status', 'unknown')))
            source = str(payload.get('force_source', payload.get('source', '')))
            stable = bool(payload.get('contact_stable', False))
            wrench_n = list(payload.get('wrench_n', payload.get('wrench', [])))
            delta_ms = 0 if last_ts == 0 else max(0, int((ts_ns - last_ts) / 1_000_000))
            last_ts = ts_ns
            rows.append({
                'seq': int(entry.get('seq', 0)),
                'ts_ns': ts_ns,
                'pressure_current': current,
                'desired_force_n': desired,
                'pressure_error': round(current - desired, 4),
                'contact_confidence': confidence,
                'contact_mode': str(payload.get('contact_mode', payload.get('mode', ''))),
                'recommended_action': str(payload.get('recommended_action', '')),
                'contact_stable': stable,
                'force_status': status,
                'force_source': source,
                'wrench_n': wrench_n,
                'estimated_normal_force_n': float(payload.get('estimated_normal_force_n', current) or current),
                'normal_force_confidence': float(payload.get('normal_force_confidence', confidence) or confidence),
                'admittance_displacement_mm': float(payload.get('admittance_displacement_mm', 0.0) or 0.0),
                'admittance_velocity_mm_s': float(payload.get('admittance_velocity_mm_s', 0.0) or 0.0),
                'admittance_saturated': bool(payload.get('admittance_saturated', False)),
                'orientation_trim_deg': float(payload.get('orientation_trim_deg', 0.0) or 0.0),
                'orientation_trim_saturated': bool(payload.get('orientation_trim_saturated', False)),
                'contact_control_mode': str(payload.get('contact_control_mode', 'normal_axis_admittance')),
                'overpressure': bool(pressure_upper > 0.0 and current > pressure_upper),
                'underpressure': bool(pressure_lower > 0.0 and current < pressure_lower),
                'stale': delta_ms > stale_threshold_ms,
                'delta_ms': delta_ms,
            })
        values = [float(row['pressure_current']) for row in rows]
        errors = [abs(float(row['pressure_error'])) for row in rows]
        est_errors = [abs(float(row['estimated_normal_force_n']) - float(row['desired_force_n'])) for row in rows]
        payload = {
            'generated_at': now_text(),
            'session_id': manifest.get('session_id', session_dir.name),
            'thresholds': {
                'pressure_target': pressure_target,
                'pressure_lower': pressure_lower,
                'pressure_upper': pressure_upper,
                'stale_threshold_ms': stale_threshold_ms,
            },
            'samples': rows,
            'summary': {
                'sample_count': len(rows),
                'avg_pressure': round(mean(values), 4) if values else 0.0,
                'std_pressure': round(pstdev(values), 4) if len(values) > 1 else 0.0,
                'max_pressure': max(values) if values else 0.0,
                'min_pressure': min(values) if values else 0.0,
                'avg_abs_error': round(mean(errors), 4) if errors else 0.0,
                'max_abs_error': max(errors) if errors else 0.0,
                'stable_ratio': round(sum(1 for row in rows if row['contact_stable']) / max(1, len(rows)), 4),
                'overpressure_count': sum(1 for row in rows if row['overpressure']),
                'underpressure_count': sum(1 for row in rows if row['underpressure']),
                'stale_count': sum(1 for row in rows if row['stale']),
                'unavailable_count': sum(1 for row in rows if row['force_status'] != 'ok'),
                'sources': sorted({row['force_source'] for row in rows if row['force_source']}),
                'force_tracking_rmse': round((sum(v * v for v in est_errors) / max(1, len(est_errors))) ** 0.5, 4) if est_errors else 0.0,
                'saturation_ratio': round(sum(1 for row in rows if row['admittance_saturated']) / max(1, len(rows)), 4),
                'orientation_trim_saturation_ratio': round(sum(1 for row in rows if row['orientation_trim_saturated']) / max(1, len(rows)), 4),
                'source_switch_count': sum(1 for idx in range(1, len(rows)) if rows[idx]['force_source'] != rows[idx - 1]['force_source']),
            },
        }
        return payload

    def build_report(self, session_dir: Path, timeline: dict[str, Any] | None = None) -> dict[str, Any]:
        timeline = timeline or self.build_timeline(session_dir)
        rows = list(timeline.get('samples', []))
        summary = dict(timeline.get('summary', {}))
        notable = [row for row in rows if row.get('overpressure') or row.get('underpressure') or row.get('force_status') != 'ok'][:20]
        return {
            'generated_at': now_text(),
            'session_id': timeline.get('session_id', session_dir.name),
            'thresholds': dict(timeline.get('thresholds', {})),
            'summary': summary,
            'notable_events': notable,
            'recommendations': self._recommendations(summary),
        }

    @staticmethod
    def _recommendations(summary: dict[str, Any]) -> list[str]:
        recs: list[str] = []
        if int(summary.get('overpressure_count', 0)) > 0:
            recs.append('接触压力存在超上限样本，需复核力控阈值与扫查路径。')
        if int(summary.get('underpressure_count', 0)) > 0:
            recs.append('接触压力存在低于下限样本，需复核耦合与贴合稳定性。')
        if int(summary.get('unavailable_count', 0)) > 0:
            recs.append('存在压力传感器不可用样本，需检查传感器链路与超时设置。')
        if int(summary.get('stale_count', 0)) > 0:
            recs.append('存在压力数据陈旧样本，需检查采样频率与同步链路。')
        if float(summary.get('saturation_ratio', 0.0)) > 0.1:
            recs.append('导纳外环出现较高比例饱和，需下调法向步长或阻尼配置。')
        if int(summary.get('source_switch_count', 0)) > 0:
            recs.append('法向力估计源发生切换，需复核压力与外力传感器一致性。')
        if not recs:
            recs.append('压力数据整体稳定，可作为接触分析证据。')
        return recs

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        return json.loads(path.read_text(encoding='utf-8'))

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
