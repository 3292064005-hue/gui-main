from __future__ import annotations

from pathlib import Path

from spine_ultrasound_ui.models import CapabilityStatus, ImplementationState


class PreprocessStage:
    """Build preprocess artifacts without changing the public façade."""

    def run(self, service, session_dir: Path | None) -> CapabilityStatus:
        """Execute the preprocess stage.

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
            return service._blocked("图像预处理")
        quality_target = service._build_quality_timeline(session_dir)
        alarms_target = service._build_alarm_timeline(session_dir)
        service.exp_manager.append_artifact(session_dir, "quality_timeline", quality_target)
        service.exp_manager.append_artifact(session_dir, "alarm_timeline", alarms_target)
        service.exp_manager.append_processing_step(
            session_dir,
            service.plugin_executor.run(
                service.plugin_registry.get("preprocess"),
                session_dir,
                {
                    "input_artifacts": ["raw/ui/quality_feedback.jsonl", "raw/core/alarm_event.jsonl", "raw/ui/annotations.jsonl"],
                    "output_artifacts": ["derived/quality/quality_timeline.json", "derived/alarms/alarm_timeline.json"],
                },
            ),
        )
        return service.job_manager.run_stage(
            stage="preprocess",
            session_dir=session_dir,
            metadata={"artifacts": [str(quality_target), str(alarms_target)]},
            build_status=lambda: CapabilityStatus(
                ready=True,
                state="AVAILABLE",
                implementation=ImplementationState.IMPLEMENTED.value,
                detail=f"质量时间线与告警时间线已生成：{quality_target.name} / {alarms_target.name}",
            ),
        )
