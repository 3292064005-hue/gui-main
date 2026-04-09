from __future__ import annotations

import json
from math import atan2, pi
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.services.reconstruction.closure_profile import load_reconstruction_profile, profile_name
from spine_ultrasound_ui.utils import now_text


class ReconstructionInputBuilder:
    """Build the authoritative reconstruction input index for a session.

    This builder now freezes the full reconstruction readiness contract rather
    than synthesizing probe poses from scan progress. Each synchronized row is
    normalized with measured robot pose facts, patient-frame transforms,
    calibration lineage, and explicit manual-review reasons.
    """

    def __init__(
        self,
        *,
        usable_quality_threshold: float = 0.7,
        usable_contact_threshold: float = 0.5,
        max_evidence_refs: int = 24,
        method_version: str = 'reconstruction_input_index_v3',
    ) -> None:
        self.usable_quality_threshold = float(usable_quality_threshold)
        self.usable_contact_threshold = float(usable_contact_threshold)
        self.max_evidence_refs = int(max_evidence_refs)
        self.method_version = method_version
        self.profile = load_reconstruction_profile()

    def build(self, session_dir: Path) -> dict[str, Any]:
        """Build a normalized reconstruction input payload.

        Args:
            session_dir: Locked session directory containing raw and derived
                evidence products.

        Returns:
            Canonical reconstruction payload containing normalized rows,
            patient-frame probe poses, reconstruction gates, and evidence
            references for downstream services.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` does not exist.
            ValueError: Raised when threshold configuration is invalid.

        Boundary behaviour:
            Missing optional evidence files do not fail the build. Instead, rows
            are marked with explicit manual-review reasons and the output gates
            disclose whether the session is reconstructable from measured data.
        """
        if not session_dir.exists():
            raise FileNotFoundError(session_dir)
        if self.max_evidence_refs <= 0:
            raise ValueError('max_evidence_refs must be positive')

        manifest = self._read_json(session_dir / 'meta' / 'manifest.json')
        patient_registration = self._read_json(session_dir / 'meta' / 'patient_registration.json')
        calibration_bundle = self._read_json(session_dir / 'meta' / 'calibration_bundle.json')
        sync_index = self._read_json(session_dir / 'derived' / 'sync' / 'frame_sync_index.json')
        quality_timeline = self._read_json(session_dir / 'derived' / 'quality' / 'quality_timeline.json')
        ultrasound_entries = self._read_jsonl(session_dir / 'raw' / 'ultrasound' / 'index.jsonl')
        camera_entries = self._read_jsonl(session_dir / 'raw' / 'camera' / 'index.jsonl')
        pressure_entries = self._read_jsonl(session_dir / 'raw' / 'pressure' / 'samples.jsonl')

        rows = [
            self._normalize_row(index, row, patient_registration=patient_registration, calibration_bundle=calibration_bundle)
            for index, row in enumerate(sync_index.get('rows', []), start=1)
        ]
        quality_candidate_rows = [row for row in rows if self._is_quality_usable(row)]
        authoritative_rows = [row for row in quality_candidate_rows if self._is_reconstructable(row)]
        selection_policy = dict(self.profile.get('selection_policy', {}) or {})
        if authoritative_rows:
            selected_rows = authoritative_rows
            selection_mode = 'authoritative_measured_rows'
        elif bool(selection_policy.get('authoritative_only', False)):
            selected_rows = []
            selection_mode = 'blocked_no_authoritative_rows'
        elif quality_candidate_rows and bool(selection_policy.get('allow_quality_only', True)):
            selected_rows = quality_candidate_rows
            selection_mode = 'quality_only_rows'
        elif rows and bool(selection_policy.get('allow_all_rows_fallback', True)):
            selected_rows = list(rows)
            selection_mode = 'all_rows_fallback'
        else:
            selected_rows = []
            selection_mode = 'selection_empty'
        segment_groups = self._segment_groups(selected_rows)
        quality_summary = dict(quality_timeline.get('summary', {}))
        sync_summary = dict(sync_index.get('summary', {}))
        evidence_refs = self._evidence_refs(selected_rows or rows)
        pose_series = self._probe_pose_series(selected_rows or rows)
        frame_visibility_scores = self._frame_visibility_scores(selected_rows or rows)
        aligned_us_frames = self._aligned_frames(selected_rows or rows, ultrasound_entries)
        quality_mask = self._quality_mask(selected_rows or rows)
        gates = self._build_gates(rows=rows, selected_rows=selected_rows, authoritative_rows=authoritative_rows)
        manual_review_reasons = self._manual_review_reasons(rows=rows, selected_rows=selected_rows, gates=gates)
        hard_blockers, soft_review_reasons = self._closure_reasons(gates=gates, manual_review_reasons=manual_review_reasons)
        scan_geometry = self._scan_geometry(patient_registration, calibration_bundle)

        coronal_vpi_ref = str(session_dir / 'derived' / 'reconstruction' / 'coronal_vpi.npz')
        reconstruction_volume_bundle_ref = str(session_dir / 'derived' / 'reconstruction' / 'reconstruction_volume_bundle.npz')
        output = {
            'generated_at': now_text(),
            'session_id': manifest.get('session_id', session_dir.name),
            'experiment_id': manifest.get('experiment_id', ''),
            'method_version': self.method_version,
            'usable_thresholds': {
                'quality_score': self.usable_quality_threshold,
                'contact_confidence': self.usable_contact_threshold,
            },
            'runtime_profile': profile_name(self.profile),
            'profile_release_state': str(self.profile.get('profile_release_state', 'research_validated') or 'research_validated'),
            'closure_mode': str(self.profile.get('closure_mode', 'runtime_optional') or 'runtime_optional'),
            'profile_config_path': str(self.profile.get('profile_config_path', '') or ''),
            'profile_load_error': str(self.profile.get('profile_load_error', '') or ''),
            'selection_mode': selection_mode,
            'patient_registration': patient_registration,
            'calibration_bundle': calibration_bundle,
            'scan_geometry': scan_geometry,
            'sync_summary': sync_summary,
            'quality_summary': quality_summary,
            'source_counts': {
                'sync_rows': len(rows),
                'selected_rows': len(selected_rows),
                'authoritative_rows': len(authoritative_rows),
                'ultrasound_frames': len(ultrasound_entries),
                'camera_frames': len(camera_entries),
                'pressure_samples': len(pressure_entries),
                'segment_groups': len(segment_groups),
            },
            'rows': rows,
            'selected_rows': selected_rows,
            'segment_groups': segment_groups,
            'evidence_refs': evidence_refs,
            'aligned_us_frames': aligned_us_frames,
            'probe_pose_series': pose_series,
            'frame_visibility_scores': frame_visibility_scores,
            'quality_mask': quality_mask,
            'gates': gates,
            'manual_review_reasons': manual_review_reasons,
            'hard_blockers': hard_blockers,
            'soft_review_reasons': soft_review_reasons,
            'closure_ready': not hard_blockers,
            'coronal_vpi_ref': coronal_vpi_ref,
            'reconstruction_volume_bundle_ref': reconstruction_volume_bundle_ref,
            'volume_reconstruction_ref': reconstruction_volume_bundle_ref,
            'artifacts': dict(manifest.get('artifacts', {})),
        }
        output['model_ready_input_index'] = {
            'coronal_vpi_ref': coronal_vpi_ref,
            'reconstruction_volume_bundle_ref': reconstruction_volume_bundle_ref,
            'volume_reconstruction_ref': reconstruction_volume_bundle_ref,
            'aligned_us_frame_count': len(aligned_us_frames),
            'pose_count': len([item for item in pose_series if item.get('pose_valid', False)]),
            'visible_frame_count': sum(1 for item in frame_visibility_scores if item.get('visible', False)),
            'reconstructable_frame_count': int(gates['reconstructable_frame_count']),
            'selection_mode': selection_mode,
            'ready_for_runtime': not hard_blockers,
            'runtime_profile': profile_name(self.profile),
            'profile_config_path': str(self.profile.get('profile_config_path', '') or ''),
            'profile_load_error': str(self.profile.get('profile_load_error', '') or ''),
            'model_not_ready_reason': '' if not hard_blockers else hard_blockers[0],
        }
        return output

    def _normalize_row(
        self,
        index: int,
        row: dict[str, Any],
        *,
        patient_registration: dict[str, Any],
        calibration_bundle: dict[str, Any],
    ) -> dict[str, Any]:
        annotation_refs = [dict(item) for item in row.get('annotation_refs', []) if isinstance(item, dict)]
        frame_id = str(row.get('frame_id', f'frame_{index:04d}') or f'frame_{index:04d}')
        robot_pose = self._pose_mm_rad(dict(row.get('robot_pose', {})))
        patient_pose = self._transform_pose_to_patient_frame(robot_pose, patient_registration)
        manual_review_reasons = [str(item) for item in list(row.get('manual_review_reasons', [])) if str(item)]
        if not robot_pose:
            manual_review_reasons.append('missing_robot_pose')
        if not patient_pose:
            manual_review_reasons.append('patient_frame_transform_unavailable')
        if not str(row.get('ultrasound_frame_path', '') or ''):
            manual_review_reasons.append('missing_ultrasound_frame')
        calibrated = bool(row.get('calibration_valid', False) and calibration_bundle.get('bundle_hash'))
        if not calibrated:
            manual_review_reasons.append('calibration_chain_incomplete')
        pose_source = str(row.get('robot_pose_source', 'missing') or 'missing')
        return {
            'row_index': index,
            'frame_id': frame_id,
            'segment_id': int(row.get('segment_id', 0) or 0),
            'ts_ns': int(row.get('ts_ns', 0) or 0),
            'quality_score': float(row.get('quality_score', 0.0) or 0.0),
            'contact_confidence': float(row.get('contact_confidence', 0.0) or 0.0),
            'pressure_current': float(row.get('pressure_current', 0.0) or 0.0),
            'progress_pct': float(row.get('progress_pct', 0.0) or 0.0),
            'recommended_action': str(row.get('recommended_action', '') or ''),
            'ultrasound_frame_path': str(row.get('ultrasound_frame_path', '') or ''),
            'ultrasound_frame_meta': dict(row.get('ultrasound_frame_meta', {})),
            'camera_frame_path': str(row.get('camera_frame_path', '') or ''),
            'annotation_refs': annotation_refs,
            'wrench_n': [float(value) for value in row.get('wrench_n', [])],
            'robot_state_ts_ns': int(row.get('robot_state_ts_ns', 0) or 0),
            'temporal_alignment_ms': float(row.get('temporal_alignment_ms', 0.0) or 0.0),
            'pose_valid': bool(row.get('pose_valid', False) and bool(robot_pose)),
            'sync_valid': bool(row.get('sync_valid', False)),
            'calibration_valid': calibrated,
            'patient_frame_valid': bool(row.get('patient_frame_valid', False)),
            'robot_pose_source': pose_source,
            'robot_pose_mm_rad': robot_pose,
            'patient_pose_mm_rad': patient_pose,
            'robot_joint_pos': [float(value) for value in list(row.get('robot_joint_pos', []))],
            'robot_joint_torque': [float(value) for value in list(row.get('robot_joint_torque', []))],
            'manual_review_reasons': self._unique_reasons(manual_review_reasons),
            'reconstructable': bool(
                self._is_quality_usable(row)
                and row.get('pose_valid', False)
                and row.get('sync_valid', False)
                and calibrated
                and bool(patient_pose)
                and str(row.get('ultrasound_frame_path', '') or '')
            ),
        }

    def _is_quality_usable(self, row: dict[str, Any]) -> bool:
        return (
            float(row.get('quality_score', 0.0)) >= self.usable_quality_threshold
            and float(row.get('contact_confidence', 0.0)) >= self.usable_contact_threshold
        )

    @staticmethod
    def _is_reconstructable(row: dict[str, Any]) -> bool:
        return bool(row.get('reconstructable', False))

    def _segment_groups(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[int, list[dict[str, Any]]] = {}
        for row in rows:
            grouped.setdefault(int(row.get('segment_id', 0)), []).append(row)
        groups: list[dict[str, Any]] = []
        for segment_id in sorted(grouped):
            segment_rows = grouped[segment_id]
            progress_values = [float(item.get('progress_pct', 0.0)) for item in segment_rows]
            quality_values = [float(item.get('quality_score', 0.0)) for item in segment_rows]
            reconstructable_values = [1 if self._is_reconstructable(item) else 0 for item in segment_rows]
            groups.append({
                'segment_id': segment_id,
                'frame_ids': [str(item.get('frame_id', '')) for item in segment_rows],
                'frame_count': len(segment_rows),
                'reconstructable_count': int(sum(reconstructable_values)),
                'progress_range_pct': [round(min(progress_values, default=0.0), 3), round(max(progress_values, default=0.0), 3)],
                'avg_quality_score': round(sum(quality_values) / len(quality_values), 4) if quality_values else 0.0,
            })
        return groups

    def _evidence_refs(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        refs: list[dict[str, Any]] = []
        for row in rows[: self.max_evidence_refs]:
            refs.append({
                'frame_id': str(row.get('frame_id', '')),
                'segment_id': int(row.get('segment_id', 0) or 0),
                'ultrasound_frame_path': str(row.get('ultrasound_frame_path', '') or ''),
                'camera_frame_path': str(row.get('camera_frame_path', '') or ''),
                'ts_ns': int(row.get('ts_ns', 0) or 0),
                'pose_valid': bool(row.get('pose_valid', False)),
                'sync_valid': bool(row.get('sync_valid', False)),
                'reconstructable': bool(row.get('reconstructable', False)),
            })
        return refs

    def _probe_pose_series(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        poses = []
        for row in rows:
            pose = dict(row.get('patient_pose_mm_rad', {}))
            poses.append({
                'frame_id': str(row.get('frame_id', '')),
                'segment_id': int(row.get('segment_id', 0) or 0),
                'coordinate_frame': 'patient_surface',
                'pose_source': str(row.get('robot_pose_source', 'missing') or 'missing'),
                'pose_valid': bool(row.get('pose_valid', False) and pose),
                'sync_valid': bool(row.get('sync_valid', False)),
                'pose_mm_rad': pose,
                'base_pose_mm_rad': dict(row.get('robot_pose_mm_rad', {})),
                'temporal_alignment_ms': float(row.get('temporal_alignment_ms', 0.0) or 0.0),
                'manual_review_reasons': list(row.get('manual_review_reasons', [])),
            })
        return poses

    def _frame_visibility_scores(self, rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
        values = []
        for row in rows:
            score = 0.5 * float(row.get('quality_score', 0.0) or 0.0) + 0.25 * float(row.get('contact_confidence', 0.0) or 0.0)
            score += 0.15 if bool(row.get('pose_valid', False)) else 0.0
            score += 0.10 if bool(row.get('sync_valid', False)) else 0.0
            score = round(min(1.0, max(0.0, score)), 4)
            values.append({
                'frame_id': str(row.get('frame_id', '')),
                'segment_id': int(row.get('segment_id', 0) or 0),
                'visibility_score': score,
                'visible': score >= 0.55,
                'reconstructable': bool(row.get('reconstructable', False)),
            })
        return values

    def _aligned_frames(self, rows: list[dict[str, Any]], ultrasound_entries: list[dict[str, Any]]) -> list[dict[str, Any]]:
        indexed = {
            str(entry.get('data', {}).get('frame_id') or f"frame_{int(entry.get('seq', 0) or 0):06d}"): dict(entry)
            for entry in ultrasound_entries if isinstance(entry, dict)
        }
        aligned = []
        for row in rows:
            frame_id = str(row.get('frame_id', ''))
            envelope = indexed.get(frame_id, {})
            frame_path = str(row.get('ultrasound_frame_path', envelope.get('data', {}).get('frame_path', '')) or '')
            aligned.append({
                'frame_id': frame_id,
                'segment_id': int(row.get('segment_id', 0) or 0),
                'frame_path': frame_path,
                'ts_ns': int(row.get('ts_ns', envelope.get('source_ts_ns', 0)) or 0),
                'pose_valid': bool(row.get('pose_valid', False)),
                'sync_valid': bool(row.get('sync_valid', False)),
                'reconstructable': bool(row.get('reconstructable', False)),
                'patient_pose_mm_rad': dict(row.get('patient_pose_mm_rad', {})),
            })
        return aligned

    def _quality_mask(self, rows: list[dict[str, Any]]) -> list[int]:
        return [1 if self._is_quality_usable(row) else 0 for row in rows]

    def _build_gates(self, *, rows: list[dict[str, Any]], selected_rows: list[dict[str, Any]], authoritative_rows: list[dict[str, Any]]) -> dict[str, Any]:
        return {
            'row_count': len(rows),
            'selected_row_count': len(selected_rows),
            'reconstructable_frame_count': len(authoritative_rows),
            'authoritative_pose_available': bool(authoritative_rows),
            'quality_rows_available': bool(any(self._is_quality_usable(row) for row in rows)),
            'patient_frame_available': bool(any(dict(row.get('patient_pose_mm_rad', {})) for row in rows)),
            'synchronized_pose_available': bool(any(bool(row.get('sync_valid', False)) for row in rows)),
        }

    def _manual_review_reasons(self, *, rows: list[dict[str, Any]], selected_rows: list[dict[str, Any]], gates: dict[str, Any]) -> list[str]:
        reasons: list[str] = []
        if not gates['quality_rows_available']:
            reasons.append('no_quality_usable_rows')
        if not gates['patient_frame_available']:
            reasons.append('patient_frame_transform_unavailable')
        if not gates['synchronized_pose_available']:
            reasons.append('no_synchronized_pose_rows')
        if not gates['authoritative_pose_available']:
            reasons.append('no_reconstructable_rows')
        if not selected_rows and rows:
            reasons.append('selection_empty')
        for row in selected_rows[: self.max_evidence_refs]:
            reasons.extend(list(row.get('manual_review_reasons', [])))
        return self._unique_reasons(reasons)


    def _closure_reasons(self, *, gates: dict[str, Any], manual_review_reasons: list[str]) -> tuple[list[str], list[str]]:
        """Partition closure blockers from soft review reasons for the active profile.

        Args:
            gates: Gate summary produced for the normalized reconstruction rows.
            manual_review_reasons: Deduplicated review reasons accumulated during normalization.

        Returns:
            Two lists containing hard blockers and soft review reasons.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Unknown review reasons remain soft reasons unless the active profile explicitly
            promotes them into hard blockers.
        """
        closure_policy = dict(self.profile.get('closure_policy', {}) or {})
        configured_blockers = {str(item) for item in list(closure_policy.get('hard_blockers', [])) if str(item)}
        reasons = self._unique_reasons(list(manual_review_reasons))
        hard_blockers = [reason for reason in reasons if reason in configured_blockers]
        soft_review_reasons = [reason for reason in reasons if reason not in configured_blockers]
        if int(gates.get('reconstructable_frame_count', 0) or 0) <= 0 and 'no_reconstructable_rows' in configured_blockers and 'no_reconstructable_rows' not in hard_blockers:
            hard_blockers.append('no_reconstructable_rows')
        if int(gates.get('selected_row_count', 0) or 0) <= 0 and 'selection_empty' in configured_blockers and 'selection_empty' not in hard_blockers:
            hard_blockers.append('selection_empty')
        return self._unique_reasons(hard_blockers), self._unique_reasons(soft_review_reasons)

    @staticmethod
    def _scan_geometry(patient_registration: dict[str, Any], calibration_bundle: dict[str, Any]) -> dict[str, Any]:
        corridor = dict(patient_registration.get('scan_corridor', {}))
        return {
            'coordinate_frame': 'patient_surface',
            'corridor_length_mm': float(corridor.get('length_mm', 0.0) or 0.0),
            'corridor_width_mm': float(corridor.get('width_mm', 240.0) or 240.0),
            'mm_per_pixel_x': float(calibration_bundle.get('camera_intrinsics', {}).get('mm_per_pixel_x', 0.15) or 0.15),
            'mm_per_pixel_y': float(calibration_bundle.get('camera_intrinsics', {}).get('mm_per_pixel_y', 0.15) or 0.15),
            'patient_origin_mm': dict(patient_registration.get('patient_frame', {}).get('origin_mm', {})),
        }

    @staticmethod
    def _pose_mm_rad(raw_pose: dict[str, Any]) -> dict[str, float]:
        if not raw_pose:
            return {}
        pose = {key: float(raw_pose.get(key, 0.0) or 0.0) for key in ['x', 'y', 'z', 'rx', 'ry', 'rz']}
        pose['rx'] = ReconstructionInputBuilder._angle_to_rad(pose['rx'])
        pose['ry'] = ReconstructionInputBuilder._angle_to_rad(pose['ry'])
        pose['rz'] = ReconstructionInputBuilder._angle_to_rad(pose['rz'])
        return pose

    @staticmethod
    def _transform_pose_to_patient_frame(raw_pose: dict[str, float], patient_registration: dict[str, Any]) -> dict[str, float]:
        if not raw_pose:
            return {}
        patient_frame = dict(patient_registration.get('patient_frame', {}))
        origin = dict(patient_frame.get('origin_mm', {}))
        axes = dict(patient_frame.get('axes', {}))
        scan_axis = [float(value) for value in list(axes.get('scan_longitudinal', [1.0, 0.0, 0.0]))]
        lr_axis = [float(value) for value in list(axes.get('left_right', [0.0, 1.0, 0.0]))]
        normal_axis = [float(value) for value in list(axes.get('surface_normal', [0.0, 0.0, -1.0]))]
        if len(scan_axis) != 3 or len(lr_axis) != 3 or len(normal_axis) != 3 or len(origin) < 3:
            return {}
        dx = float(raw_pose.get('x', 0.0) or 0.0) - float(origin.get('x', 0.0) or 0.0)
        dy = float(raw_pose.get('y', 0.0) or 0.0) - float(origin.get('y', 0.0) or 0.0)
        dz = float(raw_pose.get('z', 0.0) or 0.0) - float(origin.get('z', 0.0) or 0.0)
        yaw = atan2(scan_axis[1], scan_axis[0]) if abs(scan_axis[0]) + abs(scan_axis[1]) > 1e-9 else 0.0
        return {
            'x': round(dx * scan_axis[0] + dy * scan_axis[1] + dz * scan_axis[2], 6),
            'y': round(dx * lr_axis[0] + dy * lr_axis[1] + dz * lr_axis[2], 6),
            'z': round(dx * normal_axis[0] + dy * normal_axis[1] + dz * normal_axis[2], 6),
            'rx': round(float(raw_pose.get('rx', 0.0) or 0.0), 6),
            'ry': round(float(raw_pose.get('ry', 0.0) or 0.0), 6),
            'rz': round(float(raw_pose.get('rz', 0.0) or 0.0) - yaw, 6),
        }

    @staticmethod
    def _angle_to_rad(value: float) -> float:
        angle = float(value or 0.0)
        if abs(angle) > (2.0 * pi + 1e-6):
            return angle / 180.0 * pi
        return angle

    @staticmethod
    def _unique_reasons(values: list[str]) -> list[str]:
        ordered: list[str] = []
        for value in values:
            item = str(value or '').strip()
            if item and item not in ordered:
                ordered.append(item)
        return ordered

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        """Read an optional JSON artifact without aborting reconstruction.

        Args:
            path: Artifact path to read.

        Returns:
            Parsed JSON object, or an empty dictionary when the file is missing
            or malformed.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Reconstruction is expected to degrade explicitly when upstream side
            artifacts are absent or partially written. Returning an empty
            payload lets the builder emit hard-blockers instead of failing with
            JSON parsing exceptions.
        """
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding='utf-8'))
        except (OSError, json.JSONDecodeError):
            return {}

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        """Read a JSONL artifact while tolerating malformed rows.

        Args:
            path: JSONL artifact path.

        Returns:
            List of parsed JSON objects. Malformed rows are skipped.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Command journals and frame-level capture indexes may contain partial
            trailing writes when a session terminates abruptly. The builder
            ignores malformed lines so the remaining valid evidence can still be
            evaluated.
        """
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding='utf-8').splitlines()
        except OSError:
            return []
        rows: list[dict[str, Any]] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                rows.append(payload)
        return rows
