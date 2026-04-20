from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.utils import now_text
from spine_ultrasound_ui.core.postprocess.io_helpers import read_npz_bundle


def build_reconstruction_artifacts(service, session_dir: Path) -> dict[str, Path]:
    input_index = service.reconstruction_input_builder.build(session_dir)
    reconstruction = service.reconstruction_service.reconstruct(input_index)
    return service.reconstruction_writer.write(
        session_dir,
        input_index=input_index,
        coronal_vpi=reconstruction["coronal_vpi"],
        frame_anatomy_points=reconstruction["frame_anatomy_points"],
        bone_mask=reconstruction["bone_mask"],
        lamina_candidates=reconstruction["lamina_candidates"],
        pose_series=reconstruction["pose_series"],
        reconstruction_evidence=reconstruction["reconstruction_evidence"],
        spine_curve=reconstruction["spine_curve"],
        landmark_track=reconstruction["landmark_track"],
        summary=reconstruction["reconstruction_summary"],
        prior_assisted_curve=reconstruction.get("prior_assisted_curve"),
    )


def should_write_prior_assisted_cobb_sidecar(measurement: dict[str, Any]) -> bool:
    measurement_source = str(measurement.get('measurement_source', '') or '')
    closure_verdict = str(measurement.get('closure_verdict', '') or '')
    contamination_flags = {str(item) for item in list(measurement.get('source_contamination_flags', [])) if str(item)}
    return (
        measurement_source == 'curve_window_fallback'
        or closure_verdict == 'prior_assisted'
        or 'registration_prior_curve_used' in contamination_flags
        or 'curve_window_fallback_used' in contamination_flags
    )


def build_assessment_agreement_payload(measurement: dict[str, Any], uca_measurement: dict[str, Any]) -> dict[str, Any]:
    primary = float(measurement.get('angle_deg', 0.0) or 0.0)
    auxiliary = float(uca_measurement.get('angle_deg', 0.0) or 0.0)
    delta = round(abs(primary - auxiliary), 4)
    status = 'aligned' if delta <= 6.0 else 'divergent'
    manual_review_reasons: list[str] = []
    if status != 'aligned':
        manual_review_reasons.append('primary_auxiliary_divergence')
    manual_review_reasons.extend(list(measurement.get('manual_review_reasons', [])))
    manual_review_reasons.extend(list(uca_measurement.get('manual_review_reasons', [])))
    ordered: list[str] = []
    for reason in manual_review_reasons:
        item = str(reason or '').strip()
        if item and item not in ordered:
            ordered.append(item)
    return {
        'generated_at': now_text(),
        'primary_measurement_source': str(measurement.get('measurement_source', 'curve_window_fallback') or 'curve_window_fallback'),
        'auxiliary_measurement_source': str(uca_measurement.get('measurement_source', 'uca_auxiliary') or 'uca_auxiliary'),
        'primary_angle_deg': primary,
        'auxiliary_angle_deg': auxiliary,
        'delta_deg': delta,
        'agreement_status': status,
        'requires_manual_review': bool(ordered),
        'manual_review_reason': '' if not ordered else ordered[0],
        'manual_review_reasons': ordered,
    }


def build_assessment_summary_payload(assessment_input: dict[str, Any], measurement: dict[str, Any], uca_measurement: dict[str, Any], agreement: dict[str, Any]) -> dict[str, Any]:
    reconstruction_summary = dict(assessment_input.get("reconstruction_summary", {}))
    manual_review_reasons: list[str] = []
    manual_review_reasons.extend(list(reconstruction_summary.get('manual_review_reasons', [])))
    manual_review_reasons.extend(list(measurement.get('manual_review_reasons', [])))
    manual_review_reasons.extend(list(uca_measurement.get('manual_review_reasons', [])))
    manual_review_reasons.extend(list(agreement.get('manual_review_reasons', [])))
    ordered_reasons: list[str] = []
    for reason in manual_review_reasons:
        item = str(reason or '').strip()
        if item and item not in ordered_reasons:
            ordered_reasons.append(item)
    return {
        "generated_at": now_text(),
        "session_id": str(assessment_input.get("session_id", "") or ""),
        "experiment_id": str(assessment_input.get("experiment_id", "") or ""),
        "method_version": str(measurement.get("method_version", "") or ""),
        "runtime_profile": str(measurement.get('runtime_profile', reconstruction_summary.get('runtime_profile', 'weighted_runtime')) or 'weighted_runtime'),
        "profile_release_state": str(measurement.get('profile_release_state', reconstruction_summary.get('profile_release_state', 'research_validated')) or 'research_validated'),
        "closure_mode": str(measurement.get('closure_mode', reconstruction_summary.get('closure_mode', 'runtime_optional')) or 'runtime_optional'),
        "profile_config_path": str(measurement.get('profile_config_path', reconstruction_summary.get('profile_config_path', '')) or ''),
        "profile_load_error": str(measurement.get('profile_load_error', reconstruction_summary.get('profile_load_error', '')) or ''),
        "measurement_source": str(measurement.get("measurement_source", "curve_window_fallback") or "curve_window_fallback"),
        "measurement_status": str(measurement.get('measurement_status', 'degraded') or 'degraded'),
        "closure_verdict": str(measurement.get('closure_verdict', reconstruction_summary.get('closure_verdict', 'blocked')) or 'blocked'),
        "provenance_purity": str(measurement.get('provenance_purity', reconstruction_summary.get('provenance_purity', 'blocked')) or 'blocked'),
        "source_contamination_flags": list(measurement.get('source_contamination_flags', reconstruction_summary.get('source_contamination_flags', []))),
        "hard_blockers": list(measurement.get('hard_blockers', reconstruction_summary.get('hard_blockers', []))),
        "soft_review_reasons": list(measurement.get('soft_review_reasons', reconstruction_summary.get('soft_review_reasons', []))),
        "cobb_angle_deg": float(measurement.get("angle_deg", 0.0) or 0.0),
        "confidence": float(measurement.get("confidence", 0.0) or 0.0),
        "requires_manual_review": bool(ordered_reasons or measurement.get("requires_manual_review", False) or uca_measurement.get('requires_manual_review', False) or agreement.get('requires_manual_review', False)),
        "manual_review_reasons": ordered_reasons,
        "coordinate_frame": str(measurement.get("coordinate_frame", "patient_surface") or "patient_surface"),
        "point_count": int(reconstruction_summary.get("point_count", 0) or 0),
        "segment_count": int(reconstruction_summary.get("segment_count", 0) or 0),
        "reconstruction_status": str(reconstruction_summary.get('reconstruction_status', 'unknown') or 'unknown'),
        "uca_angle_deg": float(uca_measurement.get('angle_deg', 0.0) or 0.0),
        "uca_confidence": float(uca_measurement.get('confidence', 0.0) or 0.0),
        "agreement": agreement,
        "upper_end_vertebra_candidate": dict(measurement.get("upper_end_vertebra_candidate", {})),
        "lower_end_vertebra_candidate": dict(measurement.get("lower_end_vertebra_candidate", {})),
        "evidence_refs": list(measurement.get("evidence_refs", [])),
        "overlay_ref": "derived/assessment/assessment_overlay.png",
        "manual_review_reason": str(agreement.get('manual_review_reason', '') or (ordered_reasons[0] if ordered_reasons else '')),
    }


def build_assessment_artifacts(service, session_dir: Path) -> dict[str, Path]:
    assessment_input = service.assessment_input_builder.build(session_dir)
    measurement = service.cobb_measurement_service.measure(assessment_input)
    vertebra_pairs = {'generated_at': now_text(), 'pairs': list(measurement.get('vertebra_pairs', [])), 'summary': {'pair_count': len(measurement.get('vertebra_pairs', []))}}
    tilt_candidates = {'generated_at': now_text(), 'candidates': list(measurement.get('tilt_candidates', [])), 'summary': {'candidate_count': len(measurement.get('tilt_candidates', []))}}
    vpi_bundle = read_npz_bundle(session_dir / 'derived' / 'reconstruction' / 'coronal_vpi.npz')
    ranked_slices = service.vpi_slice_selector_service.rank(vpi_bundle)
    bone_feature_mask = service.bone_feature_segmentation_service.infer(vpi_bundle, ranked_slices)
    uca_measurement = service.uca_measurement_service.measure(assessment_input, ranked_slices, bone_feature_mask)
    agreement = build_assessment_agreement_payload(measurement, uca_measurement)
    summary = build_assessment_summary_payload(assessment_input, measurement, uca_measurement, agreement)
    overlay_tmp = session_dir / 'derived' / 'assessment' / '.assessment_overlay_tmp.png'
    overlay_path = service.assessment_evidence_renderer.render(assessment_input, measurement, overlay_tmp)
    service.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/vpi_ranked_slices.json', ranked_slices)
    feature_mask_target = session_dir / 'derived' / 'reconstruction' / 'vpi_bone_feature_mask.npz'
    import numpy as _np
    _np.savez_compressed(feature_mask_target, mask=_np.asarray(bone_feature_mask.get('mask', _np.zeros((1, 1), dtype=_np.uint8))), summary=json.dumps(bone_feature_mask.get('summary', {}), ensure_ascii=False))
    return service.assessment_writer.write(
        session_dir,
        cobb_measurement=measurement,
        assessment_summary=summary,
        vertebra_pairs=vertebra_pairs,
        tilt_candidates=tilt_candidates,
        uca_measurement=uca_measurement,
        assessment_agreement=agreement,
        overlay_path=overlay_path,
        prior_assisted_cobb=(dict(measurement) if should_write_prior_assisted_cobb_sidecar(measurement) else None),
    )
