from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState


class ReconstructStage:
    """Build authoritative lamina-aware reconstruction artifacts for a session."""

    def run(self, service, session_dir: Path | None) -> CapabilityStatus:
        """Execute the reconstruction stage.

        Args:
            service: ``PostprocessService`` façade instance.
            session_dir: Session directory or ``None`` when unavailable.

        Returns:
            ``CapabilityStatus`` describing stage availability.

        Raises:
            RuntimeError: Propagated from the façade when artifact generation
                fails.

        Boundary behaviour:
            The stage remains idempotent. Existing prerequisite artifacts are
            reused, while authoritative reconstruction artifacts are rebuilt so
            downstream assessment consumes a fresh, deterministic snapshot.
        """
        if session_dir is None:
            return service._blocked('局部重建')
        service._ensure_artifact(session_dir, 'derived/quality/quality_timeline.json', service._build_quality_timeline)
        service._ensure_artifact(session_dir, 'derived/alarms/alarm_timeline.json', service._build_alarm_timeline)
        sync_target = service._build_frame_sync_index(session_dir)
        replay_target = service._build_replay_index(session_dir)
        reconstruction_targets = service._build_reconstruction_artifacts(session_dir)
        for name, target in {
            'frame_sync_index': sync_target,
            'replay_index': replay_target,
            **reconstruction_targets,
        }.items():
            service.exp_manager.append_artifact(session_dir, name, target)
        service.exp_manager.append_processing_step(
            session_dir,
            service.plugin_executor.run(
                service.plugin_registry.get('reconstruction'),
                session_dir,
                {
                    'input_artifacts': [
                        'raw/camera/index.jsonl',
                        'raw/ultrasound/index.jsonl',
                        'raw/core/contact_state.jsonl',
                        'raw/core/scan_progress.jsonl',
                        'derived/quality/quality_timeline.json',
                        'derived/alarms/alarm_timeline.json',
                        'raw/ui/annotations.jsonl',
                        'meta/patient_registration.json',
                    ],
                    'output_artifacts': [
                        'derived/sync/frame_sync_index.json',
                        'replay/replay_index.json',
                        'derived/reconstruction/reconstruction_input_index.json',
                        'derived/reconstruction/coronal_vpi.npz',
                        'derived/reconstruction/vpi_preview.png',
                        'derived/reconstruction/bone_mask.npz',
                        'derived/reconstruction/frame_anatomy_points.json',
                        'derived/reconstruction/lamina_candidates.json',
                        'derived/reconstruction/pose_series.json',
                        'derived/reconstruction/reconstruction_evidence.json',
                        'derived/reconstruction/spine_curve.json',
                        'derived/reconstruction/landmark_track.json',
                        'derived/reconstruction/reconstruction_summary.json',
                    ],
                },
            ),
        )
        produced = [sync_target, replay_target, *reconstruction_targets.values()]
        return service.job_manager.run_stage(
            stage='reconstruction',
            session_dir=session_dir,
            metadata={'artifacts': [str(target) for target in produced]},
            build_status=lambda: CapabilityStatus(
                ready=True,
                state='AVAILABLE',
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=(
                    '重建输入索引、VPI、lamina candidates、脊柱曲线、landmark track 与回放/同步索引已生成：'
                    f"{reconstruction_targets['spine_curve'].name}"
                ),
            ),
        )
