from __future__ import annotations

import json
from pathlib import Path
from statistics import mean
from typing import Any

import cv2
import numpy as np

from spine_ultrasound_ui.services.ultrasound_service import UltrasoundCouplingMonitor
from spine_ultrasound_ui.utils import now_text


class UltrasoundAnalysisService:
    """Build stored ultrasound-frame metrics and derived session analysis."""

    def __init__(self) -> None:
        self.coupling_monitor = UltrasoundCouplingMonitor()

    def build_frame_metrics(self, session_dir: Path) -> dict[str, Any]:
        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        ultrasound_entries = self._read_jsonl(session_dir / 'raw' / 'ultrasound' / 'index.jsonl')
        quality_entries = self._read_jsonl(session_dir / 'raw' / 'ui' / 'quality_feedback.jsonl')
        pressure_entries = self._read_jsonl(session_dir / 'raw' / 'pressure' / 'samples.jsonl')
        rows: list[dict[str, Any]] = []
        for index, entry in enumerate(ultrasound_entries):
            payload = dict(entry.get('data', {}))
            ts_ns = int(entry.get('source_ts_ns', 0) or entry.get('monotonic_ns', 0))
            frame_path = Path(str(payload.get('frame_path', '')))
            row = {
                'frame_id': int(payload.get('frame_id', index + 1) or (index + 1)),
                'seq': int(entry.get('seq', 0)),
                'ts_ns': ts_ns,
                'frame_path': str(frame_path),
                'segment_id': int(payload.get('segment_id', 0) or 0),
                'quality_score': float(payload.get('quality_score', 0.0) or 0.0),
                'pressure_current': float(payload.get('pressure_current', 0.0) or 0.0),
                'contact_mode': str(payload.get('contact_mode', '')),
                'mean_intensity': 0.0,
                'std_intensity': 0.0,
                'dark_ratio': 0.0,
                'edge_energy': 0.0,
                'coupled': False,
                'warning': '',
                'missing_frame': True,
            }
            if frame_path.exists():
                frame_gray = cv2.imread(str(frame_path), cv2.IMREAD_GRAYSCALE)
                if frame_gray is not None and frame_gray.size > 0:
                    assessment = self.coupling_monitor.assess(frame_gray)
                    gx, gy = np.gradient(frame_gray.astype(np.float32))
                    edge_energy = float(np.sqrt(gx ** 2 + gy ** 2).mean())
                    row.update({
                        'mean_intensity': round(float(frame_gray.mean()), 4),
                        'std_intensity': round(float(frame_gray.std()), 4),
                        'dark_ratio': round(float(assessment.dark_ratio), 4),
                        'edge_energy': round(edge_energy, 4),
                        'coupled': bool(assessment.coupled),
                        'warning': assessment.warning or '',
                        'missing_frame': False,
                    })
            if not payload.get('quality_score') and quality_entries:
                nearest_quality = self._nearest(quality_entries, ts_ns)
                if nearest_quality:
                    row['quality_score'] = float(nearest_quality.get('data', {}).get('quality_score', 0.0) or 0.0)
            if not payload.get('pressure_current') and pressure_entries:
                nearest_pressure = self._nearest(pressure_entries, ts_ns)
                if nearest_pressure:
                    row['pressure_current'] = float(nearest_pressure.get('data', {}).get('pressure_current', 0.0) or 0.0)
            rows.append(row)
        edge_values = [float(row['edge_energy']) for row in rows if not row['missing_frame']]
        payload = {
            'generated_at': now_text(),
            'session_id': manifest.get('session_id', session_dir.name),
            'frames': rows,
            'summary': {
                'frame_count': len(rows),
                'available_frame_count': sum(1 for row in rows if not row['missing_frame']),
                'coupled_ratio': round(sum(1 for row in rows if row['coupled']) / max(1, len(rows)), 4),
                'avg_edge_energy': round(mean(edge_values), 4) if edge_values else 0.0,
                'max_edge_energy': max(edge_values) if edge_values else 0.0,
                'missing_frame_count': sum(1 for row in rows if row['missing_frame']),
                'quality_backed_frame_count': sum(1 for row in rows if float(row['quality_score']) > 0.0),
            },
        }
        return payload

    def build_report(self, session_dir: Path, frame_metrics: dict[str, Any] | None = None) -> dict[str, Any]:
        frame_metrics = frame_metrics or self.build_frame_metrics(session_dir)
        rows = list(frame_metrics.get('frames', []))
        coupled = [row for row in rows if row.get('coupled')]
        highest_edge = max(rows, key=lambda row: float(row.get('edge_energy', 0.0)), default={})
        lowest_quality = min(rows, key=lambda row: float(row.get('quality_score', 1.0)), default={})
        return {
            'generated_at': now_text(),
            'session_id': frame_metrics.get('session_id', session_dir.name),
            'summary': dict(frame_metrics.get('summary', {})),
            'best_detail_frame': {
                'frame_id': highest_edge.get('frame_id', 0),
                'frame_path': highest_edge.get('frame_path', ''),
                'edge_energy': highest_edge.get('edge_energy', 0.0),
            },
            'lowest_quality_frame': {
                'frame_id': lowest_quality.get('frame_id', 0),
                'frame_path': lowest_quality.get('frame_path', ''),
                'quality_score': lowest_quality.get('quality_score', 0.0),
            },
            'coupling_issues': [row for row in rows if not row.get('coupled')][:20],
            'recommendations': self._recommendations(frame_metrics.get('summary', {}), coupled_count=len(coupled)),
        }

    @staticmethod
    def _recommendations(summary: dict[str, Any], *, coupled_count: int) -> list[str]:
        recs: list[str] = []
        if int(summary.get('missing_frame_count', 0)) > 0:
            recs.append('存在缺失超声帧，需复核采集链路与存储完整性。')
        if float(summary.get('coupled_ratio', 0.0)) < 0.7:
            recs.append('探头耦合比例偏低，需复核耦合剂、接触压力与扫查动作。')
        if coupled_count == 0:
            recs.append('没有检测到有效耦合帧，当前超声数据不适合进入评估链。')
        if not recs:
            recs.append('超声帧存储完整且耦合状态总体可接受。')
        return recs

    @staticmethod
    def _nearest(entries: list[dict[str, Any]], ts_ns: int) -> dict[str, Any] | None:
        if not entries:
            return None
        return min(entries, key=lambda item: abs(int(item.get('source_ts_ns', 0) or item.get('monotonic_ns', 0)) - ts_ns))

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
