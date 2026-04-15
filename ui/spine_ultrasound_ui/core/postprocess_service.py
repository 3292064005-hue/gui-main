from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from spine_ultrasound_ui.core.experiment_manager import ExperimentManager
from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState
from spine_ultrasound_ui.core.postprocess_job_manager import PostprocessJobManager
from spine_ultrasound_ui.services.algorithms import PluginExecutor, PluginPlane, PluginRegistry
from spine_ultrasound_ui.services.session_products_authority_surface import SessionProductsAuthoritySurface
from spine_ultrasound_ui.services.assessment import (
    AssessmentArtifactWriter,
    AssessmentEvidenceRenderer,
    AssessmentInputBuilder,
    CobbMeasurementService,
    LaminaPairingService,
    UCAMeasurementService,
    VertebraTiltService,
    VPISliceSelectorService,
)
from spine_ultrasound_ui.services.diagnostics_pack_service import DiagnosticsPackService
from spine_ultrasound_ui.services.frame_sync_indexer import FrameSyncIndexer
from spine_ultrasound_ui.services.qa_pack_service import QAPackService
from spine_ultrasound_ui.services.reconstruction import (
    BoneFeatureSegmentationService,
    ReconstructionArtifactWriter,
    ReconstructionInputBuilder,
    SpineCurveReconstructionService,
)
from spine_ultrasound_ui.services.datasets import AnnotationManifestBuilder, SessionExportService
from spine_ultrasound_ui.services.session_integrity_service import SessionIntegrityService
from spine_ultrasound_ui.services.session_analytics import SessionAnalyticsService
from spine_ultrasound_ui.services.pressure_analysis_service import PressureAnalysisService
from spine_ultrasound_ui.services.ultrasound_analysis_service import UltrasoundAnalysisService
from spine_ultrasound_ui.utils import now_text
from spine_ultrasound_ui.core.postprocess.preprocess_stage import PreprocessStage
from spine_ultrasound_ui.core.postprocess.reconstruct_stage import ReconstructStage
from spine_ultrasound_ui.core.postprocess.report_stage import ReportStage
from spine_ultrasound_ui.core.postprocess.export_stage import ExportStage
from spine_ultrasound_ui.core.postprocess.stage_registry import iter_stage_specs


class PostprocessService:
    def __init__(self, exp_manager: ExperimentManager):
        self.exp_manager = exp_manager
        self.plugins = PluginPlane()
        self.plugin_registry = PluginRegistry(self.plugins.all_plugins())
        self.plugin_executor = PluginExecutor()
        self.qa_pack_service = QAPackService()
        self.diagnostics_service = DiagnosticsPackService()
        self.analytics = SessionAnalyticsService(exp_manager.root)
        self.sync_indexer = FrameSyncIndexer()
        self.pressure_analysis_service = PressureAnalysisService()
        self.ultrasound_analysis_service = UltrasoundAnalysisService()
        self.integrity_service = SessionIntegrityService()
        self.reconstruction_input_builder = ReconstructionInputBuilder()
        self.reconstruction_service = SpineCurveReconstructionService()
        self.reconstruction_writer = ReconstructionArtifactWriter(exp_manager)
        self.assessment_input_builder = AssessmentInputBuilder()
        self.lamina_pairing_service = LaminaPairingService()
        self.vertebra_tilt_service = VertebraTiltService()
        self.cobb_measurement_service = CobbMeasurementService(
            lamina_pairing_service=self.lamina_pairing_service,
            vertebra_tilt_service=self.vertebra_tilt_service,
        )
        self.vpi_slice_selector_service = VPISliceSelectorService()
        self.bone_feature_segmentation_service = BoneFeatureSegmentationService()
        self.uca_measurement_service = UCAMeasurementService()
        self.assessment_evidence_renderer = AssessmentEvidenceRenderer()
        self.assessment_writer = AssessmentArtifactWriter(exp_manager)
        self.authoritative_artifact_reader = SessionProductsAuthoritySurface()
        self.dataset_export_service = SessionExportService()
        self.annotation_manifest_builder = AnnotationManifestBuilder()
        self.job_manager = PostprocessJobManager()
        self.preprocess_stage = PreprocessStage()
        self.reconstruct_stage = ReconstructStage()
        self.report_stage = ReportStage()
        self.export_stage = ExportStage()
        self.stage_specs = iter_stage_specs()

    def preprocess(self, session_dir: Path | None) -> CapabilityStatus:
        return self.preprocess_stage.run(self, session_dir)

    def reconstruct(self, session_dir: Path | None) -> CapabilityStatus:
        return self.reconstruct_stage.run(self, session_dir)

    def assess(self, session_dir: Path | None) -> CapabilityStatus:
        return self.report_stage.run(self, session_dir)

    def export_lamina_center_case(self, session_dir: Path | None, output_root: Path) -> dict[str, Any]:
        """Export a locked session into the lamina-center dataset tree.

        Args:
            session_dir: Locked session directory.
            output_root: Dataset root receiving the exported case.

        Returns:
            Export manifest payload for the written case.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` is ``None`` or missing.

        Boundary behaviour:
            The method first materializes reconstruction artifacts so exported
            cases always contain authoritative reconstruction evidence.
        """
        if session_dir is None:
            raise FileNotFoundError('no active session')
        self._build_reconstruction_artifacts(session_dir)
        return self.dataset_export_service.export_lamina_center_case(session_dir, output_root)

    def export_uca_case(self, session_dir: Path | None, output_root: Path) -> dict[str, Any]:
        """Export a locked session into the UCA dataset tree.

        Args:
            session_dir: Locked session directory.
            output_root: Dataset root receiving the exported case.

        Returns:
            Export manifest payload for the written case.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` is ``None`` or missing.

        Boundary behaviour:
            Reconstruction and assessment artifacts are materialized before the
            export so UCA annotation tooling receives the latest authoritative
            VPI and auxiliary measurement payloads.
        """
        if session_dir is None:
            raise FileNotFoundError('no active session')
        self._build_reconstruction_artifacts(session_dir)
        self._build_assessment_artifacts(session_dir)
        return self.dataset_export_service.export_uca_case(session_dir, output_root)

    def build_annotation_manifest(self, dataset_root: Path) -> dict[str, Any]:
        """Build a patient-level annotation manifest for exported datasets.

        Args:
            dataset_root: Dataset root to scan.

        Returns:
            Annotation manifest payload.

        Raises:
            FileNotFoundError: Raised when the dataset root does not exist.
        """
        return self.annotation_manifest_builder.build(dataset_root)

    def refresh_all(self, session_dir: Path | None) -> dict[str, CapabilityStatus]:
        statuses = self.export_stage.run(self, session_dir)
        if session_dir is not None:
            target = self._build_stage_manifest(session_dir, statuses)
            self.exp_manager.append_artifact(session_dir, "postprocess_stage_manifest", target)
        return statuses

    def describe_pipeline(self) -> list[dict[str, Any]]:
        """Return the declarative postprocess pipeline specification.

        Returns:
            Ordered list of postprocess stage descriptors.

        Raises:
            No exceptions are raised.
        """
        return [spec.to_dict() for spec in self.stage_specs]

    def _build_stage_manifest(self, session_dir: Path, statuses: dict[str, CapabilityStatus]) -> Path:
        payload = {
            "generated_at": now_text(),
            "session_id": self.exp_manager.load_manifest(session_dir)["session_id"],
            "schema": "session/postprocess_stage_manifest_v1.schema.json",
            "stages": [
                {
                    **spec.to_dict(),
                    "ready": bool(statuses.get(spec.stage).ready) if spec.stage in statuses else False,
                    "status": str(statuses.get(spec.stage).state) if spec.stage in statuses else "NOT_RUN",
                }
                for spec in self.stage_specs
            ],
        }
        return self.exp_manager.save_json_artifact(session_dir, "derived/postprocess/postprocess_stage_manifest.json", payload)

    def _build_session_integrity(self, session_dir: Path) -> Path:
        payload = self.integrity_service.build(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/session_integrity.json", payload)

    @staticmethod
    def _blocked(label: str) -> CapabilityStatus:
        return CapabilityStatus(
            ready=False,
            state="BLOCKED",
            implementation=ImplementationState.IMPLEMENTED.value,
            detail=f"{label}需要先完成一次有效会话。",
        )

    def _ensure_artifact(self, session_dir: Path, relative_path: str, builder) -> Path:
        target = session_dir / relative_path
        if target.exists():
            return target
        return builder(session_dir)


    def _build_pressure_sensor_timeline(self, session_dir: Path) -> Path:
        payload = self.pressure_analysis_service.build_timeline(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "derived/pressure/pressure_sensor_timeline.json", payload)

    def _build_pressure_analysis(self, session_dir: Path) -> Path:
        timeline = self._read_json(session_dir / "derived" / "pressure" / "pressure_sensor_timeline.json")
        payload = self.pressure_analysis_service.build_report(session_dir, timeline)
        return self.exp_manager.save_json_artifact(session_dir, "export/pressure_analysis.json", payload)

    def _build_ultrasound_frame_metrics(self, session_dir: Path) -> Path:
        payload = self.ultrasound_analysis_service.build_frame_metrics(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "derived/ultrasound/ultrasound_frame_metrics.json", payload)

    def _build_ultrasound_analysis(self, session_dir: Path) -> Path:
        frame_metrics = self._read_json(session_dir / "derived" / "ultrasound" / "ultrasound_frame_metrics.json")
        payload = self.ultrasound_analysis_service.build_report(session_dir, frame_metrics)
        return self.exp_manager.save_json_artifact(session_dir, "export/ultrasound_analysis.json", payload)

    def _build_quality_timeline(self, session_dir: Path) -> Path:
        manifest = self.exp_manager.load_manifest(session_dir)
        quality_entries = self._read_jsonl(session_dir / "raw" / "ui" / "quality_feedback.jsonl")
        contact_entries = self._read_jsonl(session_dir / "raw" / "core" / "contact_state.jsonl")
        progress_entries = self._read_jsonl(session_dir / "raw" / "core" / "scan_progress.jsonl")
        stale_threshold_ms = int(manifest.get("safety_thresholds", {}).get("stale_telemetry_ms", 250))
        last_ts = 0
        points = []
        for index, entry in enumerate(quality_entries):
            ts_ns = int(entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0))
            payload = dict(entry.get("data", {}))
            contact = contact_entries[min(index, len(contact_entries) - 1)]["data"] if contact_entries else {}
            progress = progress_entries[min(index, len(progress_entries) - 1)]["data"] if progress_entries else {}
            delta_ms = 0 if last_ts == 0 else max(0, int((ts_ns - last_ts) / 1_000_000))
            last_ts = ts_ns
            points.append(
                {
                    "seq": int(entry.get("seq", 0)),
                    "ts_ns": ts_ns,
                    "image_quality": float(payload.get("image_quality", 0.0)),
                    "feature_confidence": float(payload.get("feature_confidence", 0.0)),
                    "quality_score": float(payload.get("quality_score", 0.0)),
                    "coverage_score": round(min(1.0, float(progress.get("progress_pct", progress.get("overall_progress", 0.0))) / 100.0), 4),
                    "contact_confidence": float(contact.get("confidence", 0.0)),
                    "pressure_current": float(contact.get("pressure_current", 0.0)),
                    "need_resample": bool(payload.get("need_resample", False)),
                    "stale_telemetry": delta_ms > stale_threshold_ms,
                    "delta_ms": delta_ms,
                    "stale_threshold_ms": stale_threshold_ms,
                    "force_status": str(contact.get("recommended_action", "IDLE")),
                    "segment_id": int(progress.get("active_segment", 0)),
                }
            )
        quality_scores = [point["quality_score"] for point in points]
        payload = {
            "generated_at": now_text(),
            "session_id": manifest["session_id"],
            "sample_count": len(points),
            "points": points,
            "summary": {
                "min_quality_score": min(quality_scores) if quality_scores else 0.0,
                "max_quality_score": max(quality_scores) if quality_scores else 0.0,
                "avg_quality_score": round(sum(quality_scores) / len(quality_scores), 4) if quality_scores else 0.0,
                "resample_events": sum(1 for point in points if point["need_resample"]),
                "coverage_ratio": round(max((point["coverage_score"] for point in points), default=0.0), 4),
                "stale_samples": sum(1 for point in points if point["stale_telemetry"]),
                "stale_threshold_ms": stale_threshold_ms,
            },
        }
        return self.exp_manager.save_json_artifact(session_dir, "derived/quality/quality_timeline.json", payload)

    def _build_alarm_timeline(self, session_dir: Path) -> Path:
        manifest = self.exp_manager.load_manifest(session_dir)
        core_alarm_entries = self._read_jsonl(session_dir / "raw" / "core" / "alarm_event.jsonl")
        journal_entries = self._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl")
        events: list[dict[str, Any]] = []
        for entry in core_alarm_entries:
            data = dict(entry.get("data", {}))
            events.append(
                {
                    "severity": str(data.get("severity", "WARN")),
                    "source": str(data.get("source", "robot_core")),
                    "message": str(data.get("message", "")),
                    "workflow_step": str(data.get("workflow_step", "")),
                    "request_id": str(data.get("request_id", "")),
                    "auto_action": str(data.get("auto_action", "")),
                    "ts_ns": int(data.get("event_ts_ns", entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0))),
                }
            )
        for entry in journal_entries:
            data = dict(entry.get("data", {}))
            reply = dict(data.get("reply", {}))
            if bool(reply.get("ok", True)):
                continue
            events.append(
                {
                    "severity": "ERROR",
                    "source": str(data.get("source", "desktop")),
                    "message": str(reply.get("message", "command failure")),
                    "workflow_step": str(data.get("workflow_step", data.get("command", ""))),
                    "request_id": str(reply.get("request_id", "")),
                    "auto_action": str(data.get("auto_action", "")),
                    "ts_ns": int(data.get("ts_ns", entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0))),
                }
            )
        events.sort(key=lambda item: int(item.get("ts_ns", 0)))
        payload = {
            "generated_at": now_text(),
            "session_id": manifest["session_id"],
            "events": events,
            "summary": {
                "count": len(events),
                "fatal_count": sum(1 for event in events if event["severity"].upper().startswith("FATAL")),
                "hold_count": sum(1 for event in events if event.get("auto_action") == "hold"),
                "retreat_count": sum(1 for event in events if "retreat" in event.get("auto_action", "")),
            },
        }
        target = self.exp_manager.save_json_artifact(session_dir, "derived/alarms/alarm_timeline.json", payload)
        self.exp_manager.update_manifest(session_dir, alarms_summary=payload["summary"])
        return target

    def _build_frame_sync_index(self, session_dir: Path) -> Path:
        payload = self.sync_indexer.build(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "derived/sync/frame_sync_index.json", payload)

    def _build_replay_index(self, session_dir: Path) -> Path:
        manifest = self.exp_manager.load_manifest(session_dir)
        camera_entries = self._read_jsonl(session_dir / "raw" / "camera" / "index.jsonl")
        ultrasound_entries = self._read_jsonl(session_dir / "raw" / "ultrasound" / "index.jsonl")
        alarm_timeline = self._read_json(session_dir / "derived/alarms/alarm_timeline.json")
        quality_timeline = self._read_json(session_dir / "derived/quality/quality_timeline.json")
        sync_index = self._read_json(session_dir / "derived/sync/frame_sync_index.json")
        annotations = self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
        timeline = []
        for event in alarm_timeline.get("events", []):
            timeline.append(
                {
                    "type": "alarm",
                    "ts_ns": int(event.get("ts_ns", 0)),
                    "label": f"{event.get('severity', 'WARN')} / {event.get('workflow_step', '-')}",
                    "anchor": event.get("auto_action", ""),
                }
            )
        for point in quality_timeline.get("points", []):
            if float(point.get("quality_score", 1.0)) < 0.75:
                timeline.append(
                    {
                        "type": "quality_valley",
                        "ts_ns": int(point.get("ts_ns", 0)),
                        "label": f"quality={float(point.get('quality_score', 0.0)):.2f}",
                        "anchor": f"segment-{point.get('segment_id', 0)}",
                    }
                )
        for row in sync_index.get("rows", []):
            if row.get("annotation_refs"):
                timeline.append(
                    {
                        "type": "sync_annotation",
                        "ts_ns": int(row.get("ts_ns", 0)),
                        "label": f"frame_sync annotations={len(row.get('annotation_refs', []))}",
                        "anchor": f"frame-{row.get('frame_id', 0)}",
                    }
                )
        for entry in annotations:
            data = dict(entry.get("data", {}))
            timeline.append(
                {
                    "type": "annotation",
                    "ts_ns": int(data.get("ts_ns", entry.get("source_ts_ns", 0) or entry.get("monotonic_ns", 0))),
                    "label": str(data.get("message", data.get("kind", "annotation"))),
                    "anchor": str(data.get("kind", "annotation")),
                }
            )
        timeline.sort(key=lambda item: int(item.get("ts_ns", 0)))
        payload = {
            "generated_at": now_text(),
            "session_id": manifest["session_id"],
            "channels": ["camera", "ultrasound", "robot_state", "contact_state", "pressure_sensor", "scan_progress", "alarm_event", "quality_feedback", "annotations", "frame_sync_index"],
            "streams": {
                "camera": {
                    "index_path": "raw/camera/index.jsonl",
                    "frame_count": len(camera_entries),
                    "latest_frame": camera_entries[-1]["data"].get("frame_path", "") if camera_entries else "",
                },
                "ultrasound": {
                    "index_path": "raw/ultrasound/index.jsonl",
                    "frame_count": len(ultrasound_entries),
                    "latest_frame": ultrasound_entries[-1]["data"].get("frame_path", "") if ultrasound_entries else "",
                },
                "frame_sync": {
                    "index_path": "derived/sync/frame_sync_index.json",
                    "frame_count": int(sync_index.get("summary", {}).get("frame_count", 0)),
                    "usable_ratio": float(sync_index.get("summary", {}).get("usable_ratio", 0.0)),
                },
                "core_topics": [
                    topic
                    for topic in ["robot_state", "contact_state", "scan_progress", "alarm_event"]
                    if (session_dir / "raw" / "core" / f"{topic}.jsonl").exists()
                ],
            },
            "timeline": timeline,
            "alarm_segments": alarm_timeline.get("events", []),
            "quality_segments": [
                {
                    "ts_ns": int(point.get("ts_ns", 0)),
                    "segment_id": int(point.get("segment_id", 0)),
                    "quality_score": float(point.get("quality_score", 0.0)),
                }
                for point in quality_timeline.get("points", [])
            ],
            "annotation_segments": [dict(entry.get("data", {})) for entry in annotations],
            "frame_sync_summary": sync_index.get("summary", {}),
            "notable_events": timeline[:50],
            "artifacts": dict(manifest.get("artifacts", {})),
        }
        return self.exp_manager.save_json_artifact(session_dir, "replay/replay_index.json", payload)

    def _build_reconstruction_artifacts(self, session_dir: Path) -> dict[str, Path]:
        """Build authoritative reconstruction artifacts for a locked session.

        Args:
            session_dir: Locked session directory containing raw capture and
                prerequisite derived artifacts.

        Returns:
            Mapping of canonical reconstruction artifact names to written paths.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` does not exist.
            ValueError: Raised when reconstruction inputs are structurally
                invalid.

        Boundary behaviour:
            The method is deterministic and idempotent. It overwrites the
            authoritative reconstruction artifacts on every invocation so the
            downstream assessment path always sees a coherent snapshot.
        """
        input_index = self.reconstruction_input_builder.build(session_dir)
        reconstruction = self.reconstruction_service.reconstruct(input_index)
        return self.reconstruction_writer.write(
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

    def _build_assessment_artifacts(self, session_dir: Path) -> dict[str, Path]:
        """Build authoritative scoliosis-assessment artifacts for a locked session.

        Args:
            session_dir: Locked session directory containing reconstruction
                artifacts.

        Returns:
            Mapping of canonical assessment artifact names to written paths.

        Raises:
            FileNotFoundError: Raised when ``session_dir`` does not exist.
            ValueError: Raised when the assessment input payload is invalid.

        Boundary behaviour:
            Missing assessment prerequisites should have been materialized by the
            caller. The writer still overwrites the authoritative artifacts on
            each invocation, enabling deterministic retries.
        """
        assessment_input = self.assessment_input_builder.build(session_dir)
        measurement = self.cobb_measurement_service.measure(assessment_input)
        vertebra_pairs = {'generated_at': now_text(), 'pairs': list(measurement.get('vertebra_pairs', [])), 'summary': {'pair_count': len(measurement.get('vertebra_pairs', []))}}
        tilt_candidates = {'generated_at': now_text(), 'candidates': list(measurement.get('tilt_candidates', [])), 'summary': {'candidate_count': len(measurement.get('tilt_candidates', []))}}
        vpi_bundle = self._read_npz_bundle(session_dir / 'derived' / 'reconstruction' / 'coronal_vpi.npz')
        ranked_slices = self.vpi_slice_selector_service.rank(vpi_bundle)
        bone_feature_mask = self.bone_feature_segmentation_service.infer(vpi_bundle, ranked_slices)
        uca_measurement = self.uca_measurement_service.measure(assessment_input, ranked_slices, bone_feature_mask)
        agreement = self._build_assessment_agreement_payload(measurement, uca_measurement)
        summary = self._build_assessment_summary_payload(assessment_input, measurement, uca_measurement, agreement)
        overlay_tmp = session_dir / 'derived' / 'assessment' / '.assessment_overlay_tmp.png'
        overlay_path = self.assessment_evidence_renderer.render(assessment_input, measurement, overlay_tmp)
        # persist auxiliary reconstruction artifacts as assessment inputs for QA
        self.exp_manager.save_json_artifact(session_dir, 'derived/reconstruction/vpi_ranked_slices.json', ranked_slices)
        feature_mask_target = session_dir / 'derived' / 'reconstruction' / 'vpi_bone_feature_mask.npz'
        import numpy as _np
        _np.savez_compressed(feature_mask_target, mask=_np.asarray(bone_feature_mask.get('mask', _np.zeros((1, 1), dtype=_np.uint8))), summary=json.dumps(bone_feature_mask.get('summary', {}), ensure_ascii=False))
        written = self.assessment_writer.write(
            session_dir,
            cobb_measurement=measurement,
            assessment_summary=summary,
            vertebra_pairs=vertebra_pairs,
            tilt_candidates=tilt_candidates,
            uca_measurement=uca_measurement,
            assessment_agreement=agreement,
            overlay_path=overlay_path,
            prior_assisted_cobb=(dict(measurement) if self._should_write_prior_assisted_cobb_sidecar(measurement) else None),
        )
        return written

    @staticmethod
    def _should_write_prior_assisted_cobb_sidecar(measurement: dict[str, Any]) -> bool:
        """Return whether the measurement must be mirrored to a prior-assisted sidecar.

        Args:
            measurement: Primary Cobb measurement payload.

        Returns:
            ``True`` when the measurement lineage is contaminated by prior-only
            reconstruction or curve-window fallback semantics.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Empty or partially populated measurements simply return ``False`` so
            legacy sessions without closure metadata remain compatible.
        """
        measurement_source = str(measurement.get('measurement_source', '') or '')
        closure_verdict = str(measurement.get('closure_verdict', '') or '')
        contamination_flags = {str(item) for item in list(measurement.get('source_contamination_flags', [])) if str(item)}
        return (
            measurement_source == 'curve_window_fallback'
            or closure_verdict == 'prior_assisted'
            or 'registration_prior_curve_used' in contamination_flags
            or 'curve_window_fallback_used' in contamination_flags
        )

    @staticmethod
    def _build_assessment_summary_payload(assessment_input: dict[str, Any], measurement: dict[str, Any], uca_measurement: dict[str, Any], agreement: dict[str, Any]) -> dict[str, Any]:
        """Condense detailed Cobb measurement output into a session summary.

        Args:
            assessment_input: Normalized assessment input payload.
            measurement: Detailed measurement payload returned by the Cobb
                measurement service.

        Returns:
            Compact assessment summary suitable for reports, QA packaging, and
            runtime writeback.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Optional reconstruction inputs degrade to empty metadata fields so
            the assessment summary remains serializable even for sparse sessions.
        """
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

    @staticmethod
    def _build_assessment_agreement_payload(measurement: dict[str, Any], uca_measurement: dict[str, Any]) -> dict[str, Any]:
        """Build agreement metadata between primary Cobb and auxiliary-UCA heads.

        Args:
            measurement: Primary Cobb measurement payload.
            uca_measurement: Auxiliary-UCA payload.

        Returns:
            Agreement payload exposing delta and manual-review status.

        Raises:
            No exceptions are raised.
        """
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

    def _read_npz_bundle(self, path: Path) -> dict[str, Any]:
        """Read a compressed NPZ artifact bundle into a JSON-like payload.

        Args:
            path: NPZ artifact path.

        Returns:
            Dictionary with at least ``image`` and metadata fields.

        Raises:
            No exceptions are raised.

        Boundary behaviour:
            Missing files produce a zero-valued VPI bundle so auxiliary heads can
            degrade gracefully.
        """
        import numpy as _np

        fallback = {
            'session_id': '',
            'image': _np.zeros((1, 1), dtype=_np.float32),
            'slices': [],
            'stats': {},
            'row_geometry': [],
            'contributing_frames': [],
            'contribution_map': _np.zeros((1, 1), dtype=_np.float32),
        }
        if not path.exists():
            return fallback

        def _bundle_json(bundle: Any, key: str, default: Any) -> Any:
            if key not in bundle:
                return default
            try:
                return json.loads(str(bundle[key]))
            except Exception:
                return default

        try:
            with _np.load(path, allow_pickle=True) as bundle:
                image = bundle['image'] if 'image' in bundle else fallback['image']
                return {
                    'session_id': '',
                    'image': image,
                    'slices': _bundle_json(bundle, 'slices', []),
                    'stats': _bundle_json(bundle, 'stats', {}),
                    'row_geometry': _bundle_json(bundle, 'row_geometry', []),
                    'contributing_frames': _bundle_json(bundle, 'contributing_frames', []),
                    'contribution_map': bundle['contribution_map'] if 'contribution_map' in bundle else _np.zeros_like(image, dtype=_np.float32),
                }
        except Exception:
            return fallback

    def _build_session_report(self, session_dir: Path) -> Path:
        manifest = self.exp_manager.load_manifest(session_dir)
        summary = self._read_json(session_dir / "export" / "summary.json")
        quality_timeline = self._read_json(session_dir / "derived/quality/quality_timeline.json")
        replay_index = self._read_json(session_dir / "replay/replay_index.json")
        alarms = self._read_json(session_dir / "derived/alarms/alarm_timeline.json")
        sync_index = self._read_json(session_dir / "derived/sync/frame_sync_index.json")
        pressure_timeline = self._read_json(session_dir / "derived/pressure/pressure_sensor_timeline.json")
        ultrasound_metrics = self._read_json(session_dir / "derived/ultrasound/ultrasound_frame_metrics.json")
        pressure_analysis = self._read_json(session_dir / "export/pressure_analysis.json")
        ultrasound_analysis = self._read_json(session_dir / "export/ultrasound_analysis.json")
        reconstruction_summary = self._read_json(session_dir / "derived" / "reconstruction" / "reconstruction_summary.json")
        assessment_summary = self._read_json(session_dir / "derived" / "assessment" / "assessment_summary.json")
        cobb_resolution = self.authoritative_artifact_reader.read_cobb_measurement(session_dir)
        cobb_measurement = dict(cobb_resolution.get("effective_payload", {}))
        uca_measurement = self._read_json(session_dir / "derived" / "assessment" / "uca_measurement.json")
        assessment_agreement = self._read_json(session_dir / "derived" / "assessment" / "assessment_agreement.json")
        journal_entries = self._read_jsonl(session_dir / "raw" / "ui" / "command_journal.jsonl")
        annotations = self._read_jsonl(session_dir / "raw" / "ui" / "annotations.jsonl")
        payload = {
            "generated_at": now_text(),
            "experiment_id": manifest["experiment_id"],
            "session_id": manifest["session_id"],
            "session_overview": {
                "core_state": summary.get("core_state", "UNKNOWN"),
                "software_version": manifest.get("software_version", ""),
                "build_id": manifest.get("build_id", ""),
                "force_sensor_provider": manifest.get("force_sensor_provider", ""),
                "robot_model": manifest.get("robot_profile", {}).get("robot_model", ""),
                "sdk_robot_class": manifest.get("robot_profile", {}).get("sdk_robot_class", ""),
                "axis_count": manifest.get("robot_profile", {}).get("axis_count", 0),
            },
            "workflow_trace": {
                **summary.get("workflow", {}),
                "patient_registration": manifest.get("patient_registration", {}),
                "scan_protocol": manifest.get("scan_protocol", {}),
            },
            "safety_summary": {
                **summary.get("safety", {}),
                "alarms": alarms.get("summary", {}),
                "safety_thresholds": manifest.get("safety_thresholds", {}),
                "contact_force_policy": manifest.get("robot_profile", {}).get("clinical_scan_contract", {}).get("contact_force_policy", {}),
            },
            "recording": summary.get("recording", {}),
            "quality_summary": {
                **quality_timeline.get("summary", {}),
                "annotation_count": len(annotations),
                "usable_sync_ratio": sync_index.get("summary", {}).get("usable_ratio", 0.0),
            },
            "ultrasound_summary": {
                **ultrasound_metrics.get("summary", {}),
                "analysis": ultrasound_analysis.get("summary", {}),
            },
            "pressure_summary": {
                **pressure_timeline.get("summary", {}),
                "analysis": pressure_analysis.get("summary", {}),
            },
            "operator_actions": {
                "command_count": len(journal_entries),
                "latest_command": journal_entries[-1].get("data", {}).get("command", "") if journal_entries else "",
                "annotation_count": len(annotations),
            },
            "closure": {
                "runtime_profile": reconstruction_summary.get("runtime_profile", assessment_summary.get("runtime_profile", "weighted_runtime")),
                "profile_release_state": reconstruction_summary.get("profile_release_state", assessment_summary.get("profile_release_state", "research_validated")),
                "closure_mode": reconstruction_summary.get("closure_mode", assessment_summary.get("closure_mode", "runtime_optional")),
                "profile_config_path": reconstruction_summary.get("profile_config_path", assessment_summary.get("profile_config_path", "")),
                "profile_load_error": reconstruction_summary.get("profile_load_error", assessment_summary.get("profile_load_error", "")),
                "closure_verdict": assessment_summary.get("closure_verdict", reconstruction_summary.get("closure_verdict", "blocked")),
                "provenance_purity": assessment_summary.get("provenance_purity", reconstruction_summary.get("provenance_purity", "blocked")),
                "source_contamination_flags": assessment_summary.get("source_contamination_flags", reconstruction_summary.get("source_contamination_flags", [])),
                "hard_blockers": assessment_summary.get("hard_blockers", reconstruction_summary.get("hard_blockers", [])),
                "soft_review_reasons": assessment_summary.get("soft_review_reasons", reconstruction_summary.get("soft_review_reasons", [])),
            },
            "reconstruction_summary": reconstruction_summary,
            "assessment_summary": assessment_summary,
            "cobb_measurement": cobb_measurement,
            "uca_measurement": uca_measurement,
            "assessment_agreement": assessment_agreement,
            "devices": {
                **manifest.get("device_health_snapshot", {}),
                "device_readiness": manifest.get("device_readiness", {}),
                "robot_profile": manifest.get("robot_profile", {}),
            },
            "outputs": manifest.get("artifact_registry", {}),
            "replay": {
                "camera_frames": replay_index.get("streams", {}).get("camera", {}).get("frame_count", 0),
                "ultrasound_frames": replay_index.get("streams", {}).get("ultrasound", {}).get("frame_count", 0),
                "synced_frames": sync_index.get("summary", {}).get("frame_count", 0),
                "timeline_points": len(replay_index.get("timeline", [])),
                "pressure_samples": pressure_timeline.get("summary", {}).get("sample_count", 0),
                "ultrasound_metric_frames": ultrasound_metrics.get("summary", {}).get("frame_count", 0),
            },
            "algorithm_versions": {plugin.stage: plugin.plugin_version for plugin in self.plugins.all_plugins()},
            "open_issues": [],
        }
        return self.exp_manager.save_json_artifact(session_dir, "export/session_report.json", payload)

    def _build_session_compare(self, session_dir: Path) -> Path:
        payload = self.analytics.compare_session(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/session_compare.json", payload)

    def _build_session_trends(self, session_dir: Path) -> Path:
        payload = self.analytics.trend_summary(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/session_trends.json", payload)

    def _build_diagnostics_pack(self, session_dir: Path) -> Path:
        payload = self.diagnostics_service.build(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/diagnostics_pack.json", payload)

    def _build_qa_pack(self, session_dir: Path) -> Path:
        payload = self.qa_pack_service.build(session_dir)
        return self.exp_manager.save_json_artifact(session_dir, "export/qa_pack.json", payload)

    @staticmethod
    def _read_jsonl(path: Path) -> list[dict[str, Any]]:
        """Read a JSONL artifact while tolerating malformed trailing rows.

        Args:
            path: JSONL artifact path.

        Returns:
            Parsed JSON rows. Malformed lines are skipped.

        Raises:
            No exceptions are raised.
        """
        if not path.exists():
            return []
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            return []
        entries: list[dict[str, Any]] = []
        for line in lines:
            if not line.strip():
                continue
            try:
                payload = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(payload, dict):
                entries.append(payload)
        return entries

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        """Read an optional JSON artifact without aborting report generation.

        Args:
            path: JSON artifact path.

        Returns:
            Parsed payload, or an empty dictionary when the file is missing or
            malformed.

        Raises:
            No exceptions are raised.
        """
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {}
