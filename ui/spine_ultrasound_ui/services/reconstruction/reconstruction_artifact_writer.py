from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.services.reconstruction.vpi_projection_builder import VPIProjectionBuilder
from spine_ultrasound_ui.utils import ensure_dir


class ReconstructionArtifactWriter:
    """Persist authoritative reconstruction artifacts to the session tree."""

    def __init__(self, exp_manager: ExperimentManager) -> None:
        self.exp_manager = exp_manager

    def write(
        self,
        session_dir: Path,
        *,
        input_index: dict[str, Any],
        coronal_vpi: dict[str, Any],
        frame_anatomy_points: dict[str, Any],
        bone_mask: dict[str, Any],
        lamina_candidates: dict[str, Any],
        pose_series: dict[str, Any],
        reconstruction_evidence: dict[str, Any],
        spine_curve: dict[str, Any],
        landmark_track: dict[str, Any],
        summary: dict[str, Any],
        prior_assisted_curve: dict[str, Any] | None = None,
    ) -> dict[str, Path]:
        """Write reconstruction artifacts to deterministic session locations.

        Args:
            session_dir: Locked session directory.
            input_index: Reconstruction input payload.
            coronal_vpi: Coronal VPI bundle.
            frame_anatomy_points: Frame-level anatomical point payload.
            bone_mask: Bone segmentation bundle.
            lamina_candidates: Lamina-candidate payload.
            pose_series: Patient-frame probe-pose series.
            reconstruction_evidence: Reconstruction evidence summary.
            spine_curve: Aggregated spine-curve payload.
            landmark_track: Landmark-track payload.
            summary: Reconstruction summary payload.
            prior_assisted_curve: Optional sidecar curve generated from registration priors only.

        Returns:
            Mapping of canonical reconstruction artifact names to written paths.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` does not exist.

        Boundary behaviour:
            Optional dense arrays are stored in the NPZ bundle when present, but
            missing arrays do not prevent the canonical JSON artifacts from being
            written. When a prior-assisted curve exists, the canonical
            ``spine_curve.json`` is rewritten as an authoritative placeholder so
            contaminated geometry does not occupy the authoritative file name.
        """
        if not session_dir.exists():
            raise FileNotFoundError(session_dir)
        input_index = dict(input_index)
        model_ready_input_index = dict(input_index.get('model_ready_input_index', {}))
        canonical_spine_curve = self._canonical_spine_curve_payload(
            spine_curve=spine_curve,
            summary=summary,
            prior_assisted_curve=prior_assisted_curve,
        )
        output = {
            'reconstruction_input_index': self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/reconstruction_input_index.json', input_index),
            'model_ready_input_index': self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/model_ready_input_index.json', model_ready_input_index),
            'training_bridge_model_ready_input_index': self.exp_manager.save_json_artifact(session_dir, 'derived/training_bridge/model_ready_input_index.json', model_ready_input_index),
            'frame_anatomy_points': self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/frame_anatomy_points.json', frame_anatomy_points),
            'lamina_candidates': self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/lamina_candidates.json', lamina_candidates),
            'pose_series': self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/pose_series.json', pose_series),
            'reconstruction_evidence': self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/reconstruction_evidence.json', reconstruction_evidence),
            'spine_curve': self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/spine_curve.json', canonical_spine_curve),
            'landmark_track': self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/landmark_track.json', landmark_track),
            'reconstruction_summary': self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/reconstruction_summary.json', summary),
        }
        coronal_vpi_path = session_dir / 'derived' / 'reconstruction' / 'coronal_vpi.npz'
        ensure_dir(coronal_vpi_path.parent)
        np.savez_compressed(
            coronal_vpi_path,
            image=np.asarray(coronal_vpi.get('image')),
            stats=json.dumps(coronal_vpi.get('stats', {}), ensure_ascii=False),
            slices=json.dumps(coronal_vpi.get('slices', []), ensure_ascii=False),
            row_geometry=json.dumps(coronal_vpi.get('row_geometry', []), ensure_ascii=False),
            contributing_frames=json.dumps(coronal_vpi.get('contributing_frames', []), ensure_ascii=False),
            contribution_map=np.asarray(coronal_vpi.get('contribution_map', np.zeros((1, 1), dtype=np.float32))),
        )
        output['coronal_vpi'] = coronal_vpi_path
        preview_path = session_dir / 'derived' / 'reconstruction' / 'vpi_preview.png'
        VPIProjectionBuilder.save_preview(np.asarray(coronal_vpi.get('preview_rgb')), preview_path)
        output['vpi_preview'] = preview_path
        bone_mask_path = session_dir / 'derived' / 'reconstruction' / 'bone_mask.npz'
        np.savez_compressed(
            bone_mask_path,
            mask=np.asarray(bone_mask.get('mask')),
            binary_mask=np.asarray(bone_mask.get('binary_mask')),
            summary=json.dumps(bone_mask.get('summary', {}), ensure_ascii=False),
            runtime_model=json.dumps(bone_mask.get('runtime_model', {}), ensure_ascii=False),
        )
        output['bone_mask'] = bone_mask_path
        reconstruction_volume_bundle_path = session_dir / 'derived' / 'reconstruction' / 'reconstruction_volume_bundle.npz'
        np.savez_compressed(
            reconstruction_volume_bundle_path,
            coronal_vpi_image=np.asarray(coronal_vpi.get('image')),
            coronal_contribution_map=np.asarray(coronal_vpi.get('contribution_map', np.zeros((1, 1), dtype=np.float32))),
            bone_mask=np.asarray(bone_mask.get('mask')),
            bone_binary_mask=np.asarray(bone_mask.get('binary_mask')),
            pose_series=json.dumps(pose_series, ensure_ascii=False),
            frame_anatomy_points=json.dumps(frame_anatomy_points, ensure_ascii=False),
            lamina_candidates=json.dumps(lamina_candidates, ensure_ascii=False),
            reconstruction_evidence=json.dumps(reconstruction_evidence, ensure_ascii=False),
            spine_curve=json.dumps(canonical_spine_curve, ensure_ascii=False),
            landmark_track=json.dumps(landmark_track, ensure_ascii=False),
            reconstruction_summary=json.dumps(summary, ensure_ascii=False),
        )
        output['reconstruction_volume_bundle'] = reconstruction_volume_bundle_path
        model_ready_input_index['reconstruction_volume_bundle_ref'] = str(reconstruction_volume_bundle_path)
        model_ready_input_index['volume_reconstruction_ref'] = str(reconstruction_volume_bundle_path)
        input_index['reconstruction_volume_bundle_ref'] = str(reconstruction_volume_bundle_path)
        input_index['volume_reconstruction_ref'] = str(reconstruction_volume_bundle_path)
        input_index['model_ready_input_index'] = model_ready_input_index
        output['reconstruction_input_index'] = self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/reconstruction_input_index.json', input_index)
        output['model_ready_input_index'] = self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/model_ready_input_index.json', model_ready_input_index)
        output['training_bridge_model_ready_input_index'] = self.exp_manager.save_json_artifact(session_dir, 'derived/training_bridge/model_ready_input_index.json', model_ready_input_index)
        if prior_assisted_curve is not None:
            output['prior_assisted_curve'] = self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/prior_assisted_curve.json', prior_assisted_curve)
        return output

    @staticmethod
    def _canonical_spine_curve_payload(
        *,
        spine_curve: dict[str, Any],
        summary: dict[str, Any],
        prior_assisted_curve: dict[str, Any] | None,
    ) -> dict[str, Any]:
        """Return the canonical spine-curve payload for disk persistence.

        When prior-assisted geometry exists, the authoritative canonical file is
        turned into an explicit placeholder and the contaminated geometry is
        emitted only via the dedicated sidecar.
        """
        contamination_flags = {str(item) for item in list(summary.get('source_contamination_flags', [])) if str(item)}
        is_prior_assisted = bool(prior_assisted_curve) or str(summary.get('closure_verdict', '')) == 'prior_assisted' or 'registration_prior_curve_used' in contamination_flags
        if not is_prior_assisted:
            return dict(spine_curve)
        return {
            'generated_at': str(spine_curve.get('generated_at', summary.get('generated_at', '')) or ''),
            'session_id': str(summary.get('session_id', spine_curve.get('session_id', '')) or ''),
            'experiment_id': str(summary.get('experiment_id', '') or ''),
            'method_version': str(spine_curve.get('method_version', summary.get('method_version', '')) or ''),
            'coordinate_frame': str(spine_curve.get('coordinate_frame', summary.get('coordinate_frame', 'patient_surface')) or 'patient_surface'),
            'patient_frame': dict(spine_curve.get('patient_frame', {})),
            'scan_corridor': dict(spine_curve.get('scan_corridor', {})),
            'points': [],
            'fit': {},
            'evidence_refs': [],
            'measurement_source': 'authoritative_curve_unavailable',
            'measurement_status': 'unavailable',
            'authoritative_available': False,
            'sidecar_ref': 'derived/reconstruction/prior_assisted_curve.json',
            'closure_verdict': 'prior_assisted',
            'source_contamination_flags': list(summary.get('source_contamination_flags', [])),
            'runtime_profile': str(summary.get('runtime_profile', spine_curve.get('runtime_profile', 'weighted_runtime')) or 'weighted_runtime'),
            'profile_release_state': str(summary.get('profile_release_state', 'research_validated') or 'research_validated'),
            'closure_mode': str(summary.get('closure_mode', 'runtime_optional') or 'runtime_optional'),
        }
