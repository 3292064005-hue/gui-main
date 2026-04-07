from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.contracts import schema_catalog


class QAPackService:
    """Assemble an operator-facing QA package from authoritative session artifacts."""

    def build(self, session_dir: Path) -> dict[str, Any]:
        """Build the QA package payload for a locked session.

        Args:
            session_dir: Locked session directory.

        Returns:
            QA package payload containing canonical report, replay, reconstruction,
            assessment, and auxiliary-UCA evidence products.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` does not exist.

        Boundary behaviour:
            Missing optional artifacts are represented by empty dictionaries or
            lists. This preserves the QA package contract for historical sessions
            while allowing newer authoritative artifacts to be included when
            present.
        """
        if not session_dir.exists():
            raise FileNotFoundError(session_dir)
        return {
            'session_dir': str(session_dir),
            'manifest': self._read_json(session_dir / 'meta' / 'manifest.json'),
            'report': self._read_json(session_dir / 'export' / 'session_report.json'),
            'replay': self._read_json(session_dir / 'replay' / 'replay_index.json'),
            'quality': self._read_json(session_dir / 'derived' / 'quality' / 'quality_timeline.json'),
            'alarms': self._read_json(session_dir / 'derived' / 'alarms' / 'alarm_timeline.json'),
            'frame_sync': self._read_json(session_dir / 'derived' / 'sync' / 'frame_sync_index.json'),
            'pressure_timeline': self._read_json(session_dir / 'derived' / 'pressure' / 'pressure_sensor_timeline.json'),
            'ultrasound_frame_metrics': self._read_json(session_dir / 'derived' / 'ultrasound' / 'ultrasound_frame_metrics.json'),
            'pressure_analysis': self._read_json(session_dir / 'export' / 'pressure_analysis.json'),
            'ultrasound_analysis': self._read_json(session_dir / 'export' / 'ultrasound_analysis.json'),
            'reconstruction_input_index': self._read_json(session_dir / 'derived' / 'reconstruction' / 'reconstruction_input_index.json'),
            'training_bridge_model_ready_input_index': self._read_json(session_dir / 'derived' / 'training_bridge' / 'model_ready_input_index.json'),
            'coronal_vpi_stats': self._read_npz_summary(session_dir / 'derived' / 'reconstruction' / 'coronal_vpi.npz'),
            'vpi_ranked_slices': self._read_json(session_dir / 'derived' / 'reconstruction' / 'vpi_ranked_slices.json'),
            'bone_mask_summary': self._read_npz_summary(session_dir / 'derived' / 'reconstruction' / 'bone_mask.npz'),
            'vpi_bone_feature_mask_summary': self._read_npz_summary(session_dir / 'derived' / 'reconstruction' / 'vpi_bone_feature_mask.npz'),
            'lamina_candidates': self._read_json(session_dir / 'derived' / 'reconstruction' / 'lamina_candidates.json'),
            'spine_curve': self._read_json(session_dir / 'derived' / 'reconstruction' / 'spine_curve.json'),
            'prior_assisted_curve': self._read_json(session_dir / 'derived' / 'reconstruction' / 'prior_assisted_curve.json'),
            'landmark_track': self._read_json(session_dir / 'derived' / 'reconstruction' / 'landmark_track.json'),
            'reconstruction_summary': self._read_json(session_dir / 'derived' / 'reconstruction' / 'reconstruction_summary.json'),
            'reconstruction_evidence': self._read_json(session_dir / 'derived' / 'reconstruction' / 'reconstruction_evidence.json'),
            'assessment': self._read_json(session_dir / 'derived' / 'assessment' / 'cobb_measurement.json'),
            'prior_assisted_cobb': self._read_json(session_dir / 'derived' / 'assessment' / 'prior_assisted_cobb.json'),
            'vertebra_pairs': self._read_json(session_dir / 'derived' / 'assessment' / 'vertebra_pairs.json'),
            'tilt_candidates': self._read_json(session_dir / 'derived' / 'assessment' / 'tilt_candidates.json'),
            'uca_measurement': self._read_json(session_dir / 'derived' / 'assessment' / 'uca_measurement.json'),
            'assessment_agreement': self._read_json(session_dir / 'derived' / 'assessment' / 'assessment_agreement.json'),
            'assessment_summary': self._read_json(session_dir / 'derived' / 'assessment' / 'assessment_summary.json'),
            'assessment_overlay_available': (session_dir / 'derived' / 'assessment' / 'assessment_overlay.png').exists(),
            'compare': self._read_json(session_dir / 'export' / 'session_compare.json'),
            'trends': self._read_json(session_dir / 'export' / 'session_trends.json'),
            'diagnostics': self._read_json(session_dir / 'export' / 'diagnostics_pack.json'),
            'annotations': self._read_jsonl(session_dir / 'raw' / 'ui' / 'annotations.jsonl'),
            'robot_profile': self._read_json(session_dir / 'meta' / 'xmate_profile.json'),
            'patient_registration': self._read_json(session_dir / 'meta' / 'patient_registration.json'),
            'scan_protocol': self._read_json(session_dir / 'derived' / 'preview' / 'scan_protocol.json'),
            'schemas': schema_catalog(),
        }

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        if not path.exists():
            return []
        try:
            return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
        except (OSError, json.JSONDecodeError):
            return []

    @staticmethod
    def _read_npz_summary(path: Path) -> dict[str, Any]:
        if not path.exists():
            return {}
        import numpy as np
        try:
            with np.load(path, allow_pickle=True) as bundle:
                payload: dict[str, Any] = {'keys': list(bundle.keys())}
                if 'summary' in bundle:
                    try:
                        payload['summary'] = json.loads(str(bundle['summary']))
                    except Exception:
                        payload['summary'] = {'raw': str(bundle['summary'])}
                if 'stats' in bundle:
                    try:
                        payload['stats'] = json.loads(str(bundle['stats']))
                    except Exception:
                        payload['stats'] = {'raw': str(bundle['stats'])}
                if 'image' in bundle:
                    payload['shape'] = list(bundle['image'].shape)
                return payload
        except Exception:
            return {}
