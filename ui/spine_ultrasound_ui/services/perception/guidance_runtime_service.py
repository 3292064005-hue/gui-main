from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any

from spine_ultrasound_ui.models import ProcessingStepRecord, RuntimeConfig
from spine_ultrasound_ui.services.algorithms.plugin_plane import PluginPlane
from spine_ultrasound_ui.services.calibration import CalibrationBundleService
from spine_ultrasound_ui.services.patient_registration import build_registration_facts
from spine_ultrasound_ui.services.perception.camera_provider import CameraProvider, CapturedFrame
from spine_ultrasound_ui.services.perception.guidance_gate_service import GuidanceGateService
from spine_ultrasound_ui.services.perception.guidance_perception_service import GuidancePerceptionService
from spine_ultrasound_ui.services.perception.guidance_registration_builder import GuidanceRegistrationBuilder
from spine_ultrasound_ui.services.perception.guidance_replay_service import GuidanceReplayService
from spine_ultrasound_ui.services.perception.manual_adjustment_service import ManualAdjustmentService
from spine_ultrasound_ui.utils import now_text


@dataclass
class GuidanceRuntimeResult:
    """Structured result returned by the camera guidance runtime.

    Attributes:
        patient_registration: Canonical guidance registration contract.
        localization_readiness: Freeze verdict for the guidance subsystem.
        calibration_bundle: Calibration bundle bound to the guidance result.
        registration_candidate: Pre-freeze registration candidate.
        manual_adjustment: Manual adjustment artifact.
        source_frame_set: Frozen frame-set index.
        localization_replay_index: Replay contract for guidance evidence.
        guidance_algorithm_registry: Guidance-stage plugin registry summary.
        guidance_processing_steps: Guidance-stage processing-step records.
    """

    patient_registration: dict[str, Any]
    localization_readiness: dict[str, Any]
    calibration_bundle: dict[str, Any]
    registration_candidate: dict[str, Any]
    manual_adjustment: dict[str, Any]
    source_frame_set: dict[str, Any]
    localization_replay_index: dict[str, Any]
    guidance_algorithm_registry: dict[str, Any]
    guidance_processing_steps: list[dict[str, Any]] = field(default_factory=list)


class GuidanceRuntimeService:
    """Orchestrate guidance-only camera registration for pre-scan freeze.

    This runtime explicitly stops at the session-freeze boundary. It produces a
    frozen guidance contract, calibration lineage, and readiness verdict, but it
    never acts as an execution authority.
    """

    def __init__(
        self,
        *,
        calibration_bundle_service: CalibrationBundleService | None = None,
        registration_builder: GuidanceRegistrationBuilder | None = None,
        gate_service: GuidanceGateService | None = None,
        manual_adjustment_service: ManualAdjustmentService | None = None,
        replay_service: GuidanceReplayService | None = None,
        plugin_plane: PluginPlane | None = None,
        camera_provider: CameraProvider | None = None,
        perception_service: GuidancePerceptionService | None = None,
    ) -> None:
        self.calibration_bundle_service = calibration_bundle_service or CalibrationBundleService()
        self.registration_builder = registration_builder or GuidanceRegistrationBuilder()
        self.gate_service = gate_service or GuidanceGateService()
        self.manual_adjustment_service = manual_adjustment_service or ManualAdjustmentService()
        self.replay_service = replay_service or GuidanceReplayService()
        self.plugin_plane = plugin_plane or PluginPlane()
        self.camera_provider = camera_provider or CameraProvider()
        self.perception_service = perception_service or GuidancePerceptionService()

    def build(
        self,
        *,
        experiment_id: str,
        config: RuntimeConfig,
        device_roster: dict[str, Any] | None,
        source_type: str,
        source_label: str,
        roi_center_y: float | None = None,
        segment_count: int | None = None,
        confidence: float | None = None,
        manual_adjustments: list[dict[str, Any]] | None = None,
        review_context: dict[str, Any] | None = None,
    ) -> GuidanceRuntimeResult:
        """Build the guidance-only localization bundle.

        Args:
            experiment_id: Experiment identifier.
            config: Active runtime configuration.
            device_roster: Device health facts available before session lock.
            source_type: Guidance source mode.
            source_label: Backward-compatible source label.
            roi_center_y: Optional guidance override. When omitted, the runtime
                derives the corridor from camera frames.
            segment_count: Optional usable segment override.
            confidence: Optional confidence override.
            manual_adjustments: Optional pre-freeze operator edits.
            review_context: Optional review approval context.

        Returns:
            Fully normalized guidance bundle.

        Raises:
            ValueError: Propagated when calibration or adjustment inputs are
                malformed.
            RuntimeError: Propagated when the configured camera provider cannot
                produce usable frames.
        """
        guidance_registry = {
            plugin.stage: {"plugin_id": plugin.plugin_id, "plugin_version": plugin.plugin_version}
            for plugin in self.plugin_plane.guidance_plugins()
        }
        algorithm_bundle_hash = self._stable_hash(guidance_registry)
        calibration_bundle = self.calibration_bundle_service.build_bundle(
            config=config,
            camera_device_id=str(getattr(config, 'camera_device_id', '') or 'rgbd_back_camera'),
        )
        frames = self.camera_provider.collect_frames(
            experiment_id=experiment_id,
            config=config,
            calibration_bundle=calibration_bundle,
            source_type=source_type,
        )
        provider_status = self.camera_provider.provider_status(
            frames=frames,
            requested_mode=str(getattr(config, 'camera_guidance_input_mode', 'synthetic') or 'synthetic').lower(),
        )
        effective_device_roster = dict(device_roster or {})
        effective_device_roster['camera'] = {
            **dict(effective_device_roster.get('camera', {})),
            'online': bool(provider_status.get('available', False)),
            'fresh': bool(provider_status.get('fresh', False)),
        }
        source_frame_set = self._build_source_frame_set(
            experiment_id=experiment_id,
            calibration_bundle=calibration_bundle,
            frames=frames,
            provider_status=provider_status,
        )
        observation = self.perception_service.analyze(
            frames=frames,
            config=config,
            calibration_bundle=calibration_bundle,
            source_type=source_type,
        )
        if roi_center_y is not None:
            observation.roi_center_y_mm = round(float(roi_center_y), 2)
            observation.back_roi['center_y_mm'] = observation.roi_center_y_mm
        if segment_count is not None:
            observation.segment_count = int(segment_count)
            observation.usable_segments = list(range(1, observation.segment_count + 1))
        if confidence is not None:
            observation.confidence = round(float(confidence), 3)
            observation.registration_quality['overall_confidence'] = observation.confidence
            observation.registration_quality['quality_metrics']['overall_confidence'] = observation.confidence
            observation.registration_quality['quality_metrics']['roi_confidence'] = min(observation.confidence, float(observation.registration_quality['quality_metrics'].get('roi_confidence', observation.confidence)))
            observation.registration_quality['quality_metrics']['midline_confidence'] = min(observation.confidence, float(observation.registration_quality['quality_metrics'].get('midline_confidence', observation.confidence)))
        manual_adjustment = self.manual_adjustment_service.normalize(manual_adjustments)
        facts = build_registration_facts(
            experiment_id=experiment_id,
            roi_center_y=observation.roi_center_y_mm,
            segment_count=observation.segment_count,
            config=config,
            source_label=source_label,
            source_type=source_type,
            confidence=observation.confidence,
            observation={
                'roi_center_y_mm': observation.roi_center_y_mm,
                'segment_count': observation.segment_count,
                'confidence': observation.confidence,
                'back_roi': observation.back_roi,
                'midline_polyline': observation.midline_polyline,
                'landmarks': observation.landmarks,
                'body_surface': observation.body_surface,
                'guidance_targets': observation.guidance_targets,
                'usable_segments': observation.usable_segments,
                'notes': observation.notes,
                'registration_quality': observation.registration_quality,
                'quality_metrics': observation.registration_quality.get('quality_metrics', {}),
                'provider_mode': observation.provider_mode,
                'surface_yaw_deg': observation.body_surface.get('surface_yaw_deg', 0.0),
            },
            camera_device_id=str(calibration_bundle.get('camera_device_id', 'rgbd_back_camera')),
        )
        registration_candidate = self._build_registration_candidate(
            facts=facts,
            source_type=source_type,
            algorithm_bundle_hash=algorithm_bundle_hash,
        )
        readiness = self.gate_service.evaluate(
            device_roster=effective_device_roster,
            calibration_bundle=calibration_bundle,
            registration_candidate=registration_candidate,
            source_frame_set=source_frame_set,
            source_type=source_type,
            manual_adjustment=manual_adjustment,
            review_context=review_context,
        )
        processing_steps = self._build_processing_steps(
            experiment_id=experiment_id,
            source_type=source_type,
            source_frame_set=source_frame_set,
            provider_mode=provider_status['provider_mode'],
        )
        registration = self.registration_builder.build(
            experiment_id=experiment_id,
            source_type=source_type,
            source_label=source_label,
            patient_frame=facts['patient_frame'],
            scan_corridor=facts['scan_corridor'],
            landmarks=facts['landmarks'],
            body_surface=facts['body_surface'],
            camera_observations=facts['camera_observations'],
            registration_quality=facts['registration_quality'],
            guidance_targets=facts['guidance_targets'],
            usable_segments=facts['usable_segments'],
            notes=facts['notes'],
            calibration_bundle=calibration_bundle,
            localization_readiness=readiness,
            source_frame_set=source_frame_set,
            algorithm_bundle_hash=algorithm_bundle_hash,
            manual_adjustment=manual_adjustment,
            processing_step_refs=[step['step_id'] for step in processing_steps],
        )
        replay_index = self.replay_service.build(
            session_or_experiment_id=experiment_id,
            source_frame_set=source_frame_set,
            processing_step_refs=[step['step_id'] for step in processing_steps],
            candidate_hash=str(registration_candidate.get('candidate_hash', '')),
            registration_hash=str(registration.get('registration_hash', '')),
            readiness_hash=str(readiness.get('readiness_hash', '')),
            calibration_bundle_hash=str(calibration_bundle.get('bundle_hash', '')),
        )
        return GuidanceRuntimeResult(
            patient_registration=registration,
            localization_readiness=readiness,
            calibration_bundle=calibration_bundle,
            registration_candidate=registration_candidate,
            manual_adjustment=manual_adjustment,
            source_frame_set=source_frame_set,
            localization_replay_index=replay_index,
            guidance_algorithm_registry=guidance_registry,
            guidance_processing_steps=processing_steps,
        )

    def _build_source_frame_set(
        self,
        *,
        experiment_id: str,
        calibration_bundle: dict[str, Any],
        frames: list[CapturedFrame],
        provider_status: dict[str, Any],
    ) -> dict[str, Any]:
        payload = {
            'schema_version': '1.0',
            'generated_at': now_text(),
            'camera_device_id': str(calibration_bundle.get('camera_device_id', 'rgbd_back_camera')),
            'frame_refs': [frame.storage_ref for frame in frames],
            'frame_envelopes': [frame.envelope() for frame in frames],
            'frame_count': len(frames),
            'fresh': all(bool(frame.fresh) for frame in frames),
            'provider_mode': provider_status.get('provider_mode', 'unknown'),
            'requested_mode': provider_status.get('requested_mode', 'unknown'),
        }
        payload['source_frame_set_hash'] = self._stable_hash(payload)
        return payload

    def _build_registration_candidate(self, *, facts: dict[str, Any], source_type: str, algorithm_bundle_hash: str) -> dict[str, Any]:
        quality_metrics = dict(facts['registration_quality'].get('quality_metrics', {}))
        payload = {
            'schema_version': '1.0',
            'candidate_id': f"candidate::{facts['experiment_id']}::{source_type}",
            'source_type': source_type,
            'patient_frame': dict(facts['patient_frame']),
            'scan_corridor': dict(facts['scan_corridor']),
            'landmarks': [dict(item) for item in facts['landmarks']],
            'registration_covariance': dict(facts['registration_quality'].get('registration_covariance', {})),
            'quality_metrics': quality_metrics,
            'confidence': float(facts['registration_quality'].get('overall_confidence', 0.0) or 0.0),
            'usable_segment_count': len(list(facts.get('usable_segments', []))),
            'algorithm_bundle_hash': algorithm_bundle_hash,
        }
        payload['candidate_hash'] = self._stable_hash(payload)
        return payload

    def _build_processing_steps(
        self,
        *,
        experiment_id: str,
        source_type: str,
        source_frame_set: dict[str, Any],
        provider_mode: str,
    ) -> list[dict[str, Any]]:
        step_specs = [
            (self.plugin_plane.camera_preprocess, ['derived/sync/source_frame_set.json'], ['derived/guidance/back_roi.json'], f'Guidance frames captured from {provider_mode} provider and prepared for ROI isolation.'),
            (self.plugin_plane.spine_midline_estimation, ['derived/guidance/back_roi.json'], ['derived/guidance/midline_polyline.json', 'derived/guidance/landmarks.json', 'derived/guidance/body_surface.json'], f'Image-derived midline, landmarks and surface model computed for {source_type}.'),
            (self.plugin_plane.registration_build, ['derived/guidance/midline_polyline.json', 'derived/guidance/landmarks.json', 'derived/guidance/body_surface.json'], ['derived/guidance/registration_candidate.json', 'derived/guidance/guidance_targets.json'], 'Guidance registration candidate composed from perception facts and calibration lineage.'),
            (self.plugin_plane.registration_validate, ['derived/guidance/registration_candidate.json'], ['meta/localization_readiness.json'], 'Guidance freeze gate evaluated with device, calibration and perception checks.'),
        ]
        steps: list[dict[str, Any]] = []
        for index, (plugin, inputs, outputs, detail) in enumerate(step_specs, start=1):
            record = ProcessingStepRecord(
                step_id=f'{plugin.stage}::{experiment_id}::{index:02d}',
                plugin_id=plugin.plugin_id,
                plugin_version=plugin.plugin_version,
                input_artifacts=list(inputs),
                output_artifacts=list(outputs),
                status='completed',
                detail=detail,
                metrics={
                    'source_type': source_type,
                    'frame_count': int(source_frame_set.get('frame_count', 0) or 0),
                    'provider_mode': provider_mode,
                },
            )
            steps.append(record.to_dict())
        return steps

    @staticmethod
    def _stable_hash(payload: dict[str, Any]) -> str:
        blob = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode('utf-8')
        return hashlib.sha256(blob).hexdigest()
