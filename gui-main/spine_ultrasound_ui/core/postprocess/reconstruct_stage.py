from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState


class ReconstructStage:
    """Build replay and synchronization artifacts for a session."""

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
        """
        if session_dir is None:
            return service._blocked("局部重建")
        service._ensure_artifact(session_dir, "derived/quality/quality_timeline.json", service._build_quality_timeline)
        service._ensure_artifact(session_dir, "derived/alarms/alarm_timeline.json", service._build_alarm_timeline)
        sync_target = service._build_frame_sync_index(session_dir)
        replay_target = service._build_replay_index(session_dir)
        service.exp_manager.append_artifact(session_dir, "frame_sync_index", sync_target)
        service.exp_manager.append_artifact(session_dir, "replay_index", replay_target)
        service.exp_manager.append_processing_step(
            session_dir,
            service.plugin_executor.run(
                service.plugin_registry.get("reconstruction"),
                session_dir,
                {
                    "input_artifacts": [
                        "raw/camera/index.jsonl",
                        "raw/ultrasound/index.jsonl",
                        "raw/core/contact_state.jsonl",
                        "raw/core/scan_progress.jsonl",
                        "derived/quality/quality_timeline.json",
                        "derived/alarms/alarm_timeline.json",
                        "raw/ui/annotations.jsonl",
                    ],
                    "output_artifacts": ["derived/sync/frame_sync_index.json", "replay/replay_index.json"],
                },
            ),
        )
        return service.job_manager.run_stage(
            stage="reconstruction",
            session_dir=session_dir,
            metadata={"artifacts": [str(sync_target), str(replay_target)]},
            build_status=lambda: CapabilityStatus(
                ready=True,
                state="AVAILABLE",
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=f"帧同步索引与回放索引已生成：{sync_target.name} / {replay_target.name}",
            ),
        )
